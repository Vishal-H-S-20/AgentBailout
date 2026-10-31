import asyncio
from datetime import datetime
from decimal import Decimal
from pydantic import BaseModel
from typing import Literal
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException
from sqlalchemy import select
from backend.database import Base, engine, SessionLocal
from backend.models import Task, Stage, Event
from backend.schemas import TaskCreate, TaskView, EventView
from backend.supervisor import AGENTS, claim, execute, fail
from backend.ledger import fund, snapshot


class FailureRequest(BaseModel):
    scenario: Literal['crash', 'heartbeat_loss', 'backup_failure', 'expensive', 'no_backup']


def create_app(db_engine=engine, factory=SessionLocal) -> FastAPI:
    jobs: set[asyncio.Task] = set()

    @asynccontextmanager
    async def lifespan(app):
        Base.metadata.create_all(db_engine)
        with factory() as db:
            interrupted = list(db.scalars(select(Task.id).where(Task.status.in_(['RUNNING', 'RESCUING', 'RESCUED']))))
        for task_id in interrupted:
            fail(factory, task_id, None, 'Interrupted execution detected on startup; create a new task')
        yield
        for job in list(jobs):
            job.cancel()
        await asyncio.gather(*jobs, return_exceptions=True)

    app = FastAPI(title='AgentBailout', version='0.1.0', lifespan=lifespan)

    def get_task(task_id: str) -> TaskView:
        with factory() as db:
            task = db.get(Task, task_id)
            if task is None:
                raise HTTPException(404, 'Task not found')
            return TaskView.model_validate(task)

    @app.get('/health')
    def health():
        with factory() as db:
            db.execute(select(1))
        return {'status': 'ok', 'phase': 3}

    @app.post('/tasks', response_model=TaskView, status_code=201)
    def create_task(body: TaskCreate):
        if not body.prompt.strip():
            raise HTTPException(422, 'Prompt must contain text')
        with factory.begin() as db:
            task = Task(prompt=body.prompt.strip())
            task.stages = [Stage(name=name, position=i) for i, (name, _) in enumerate(AGENTS)]
            db.add(task)
            db.flush()
            fund(db, task.id)
            db.add(Event(task_id=task.id, type='TASK_CREATED', message='Task persisted'))
            result = TaskView.model_validate(task)
        return result

    @app.get('/tasks', response_model=list[TaskView])
    def list_tasks():
        with factory() as db:
            return [TaskView.model_validate(t) for t in db.scalars(select(Task).order_by(Task.created_at.desc()).limit(100))]

    @app.get('/tasks/{task_id}', response_model=TaskView)
    def detail(task_id: str):
        return get_task(task_id)

    @app.post('/tasks/{task_id}/start', status_code=202)
    async def start(task_id: str):
        get_task(task_id)
        if not claim(factory, task_id):
            raise HTTPException(409, 'Only a CREATED task can be started')
        job = asyncio.create_task(execute(factory, task_id))
        jobs.add(job)
        job.add_done_callback(jobs.discard)
        return {'task_id': task_id, 'status': 'RUNNING'}

    @app.get('/tasks/{task_id}/events', response_model=list[EventView])
    def events(task_id: str):
        get_task(task_id)
        with factory() as db:
            return [EventView.model_validate(e) for e in db.scalars(select(Event).where(Event.task_id == task_id).order_by(Event.id))]

    @app.post('/tasks/{task_id}/inject-failure')
    def inject(task_id: str, body: FailureRequest):
        with factory.begin() as db:
            task = db.get(Task, task_id)
            if task is None:
                raise HTTPException(404, 'Task not found')
            if task.status not in {'CREATED', 'RUNNING'} or task.stages[1].status == 'COMPLETED':
                raise HTTPException(409, 'Formatter is no longer injectable')
            if db.scalar(select(Event.id).where(Event.task_id == task_id, Event.type == 'FAILURE_INJECTED')):
                raise HTTPException(409, 'Failure already configured')
            db.add(Event(task_id=task_id, type='FAILURE_INJECTED', message=body.scenario))
        return {'scenario': body.scenario}

    @app.get('/tasks/{task_id}/ledger')
    def ledger(task_id: str):
        get_task(task_id)
        with factory() as db:
            return snapshot(db, task_id)

    @app.get('/metrics')
    def metrics():
        with factory() as db:
            tasks = list(db.scalars(select(Task)))
            events = list(db.scalars(select(Event)))
            failures = sum(e.type == 'FAILURE_DETECTED' for e in events)
            recovered = sum(t.status == 'COMPLETED' and any(s.recovery_attempts for s in t.stages) for t in tasks)
            durations = []
            for task in tasks:
                starts = [e.timestamp for e in events if e.task_id == task.id and e.type == 'FAILURE_DETECTED']
                ends = [e.timestamp for e in events if e.task_id == task.id and e.type == 'BACKUP_COMPLETED']
                if starts and ends:
                    durations.append((datetime.fromisoformat(ends[0])-datetime.fromisoformat(starts[0])).total_seconds())
            from backend.models import LedgerEntry
            expenses = list(db.scalars(select(LedgerEntry).where(LedgerEntry.account.in_(['backup_expense','recovery_overhead']))))
            return {'tasks_processed':sum(t.status in {'COMPLETED','FAILED'} for t in tasks),
                    'failures_detected':failures,'successful_recoveries':recovered,
                    'recovery_success_rate':recovered/failures if failures else 0,
                    'average_recovery_seconds':sum(durations)/len(durations) if durations else 0,
                    'total_simulated_rescue_cost':str(Decimal(sum(e.credit_cents-e.debit_cents for e in expenses))/100)}

    return app


app = create_app()
