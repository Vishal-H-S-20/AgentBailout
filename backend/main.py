import asyncio
from datetime import datetime
from decimal import Decimal
from pydantic import BaseModel
from typing import Literal
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from sqlalchemy.exc import IntegrityError
from sqlalchemy import select
from backend.database import Base, engine, SessionLocal
from backend.models import Task, Stage, Event, Agent, Workflow, Execution, Comparison
from backend.schemas import TaskCreate, TaskView, EventView, FaultDefinition, AgentCreate, WorkflowCreate
from backend.supervisor import AGENTS, claim, execute, fail
from backend.ledger import fund, snapshot


class FailureRequest(FaultDefinition):
    pass


def create_app(db_engine=engine, factory=SessionLocal) -> FastAPI:
    jobs: set[asyncio.Task] = set()

    @asynccontextmanager
    async def lifespan(app):
        from backend.migrations import migrate
        from backend.registry import seed
        migrate(db_engine)
        with factory.begin() as db:
            seed(db)
        with factory() as db:
            interrupted = list(db.scalars(select(Task.id).where(Task.status.in_(['RUNNING', 'RESCUING', 'RESCUED']))))
        for task_id in interrupted:
            fail(factory, task_id, None, 'Interrupted execution detected on startup; create a new task')
        yield
        for job in list(jobs):
            job.cancel()
        await asyncio.gather(*jobs, return_exceptions=True)

    app = FastAPI(title='AgentBailout', version='0.4.0', lifespan=lifespan)

    @app.exception_handler(IntegrityError)
    async def conflict(request, exc):
        return JSONResponse(status_code=409,content={'detail':'Conflicting write; operation was rolled back'})

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
        return {'status': 'ok', 'phase': 4}

    @app.post('/tasks', response_model=TaskView, status_code=201)
    def create_task(body: TaskCreate):
        if not body.prompt.strip():
            raise HTTPException(422, 'Prompt must contain text')
        with factory.begin() as db:
            from backend.workflows import create_execution
            try:
                task = create_execution(db,body)
            except ValueError as exc:
                raise HTTPException(422,str(exc)) from None
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
            execution = db.get(Execution,task_id)
            index = body.stage_index if body.stage_index is not None else min(1,len(task.stages)-1)
            if index >= len(task.stages):
                raise HTTPException(422,'Failure stage is outside the workflow')
            if task.status not in {'CREATED', 'RUNNING'} or task.stages[index].status != 'PENDING':
                raise HTTPException(409, 'Only pending stages accept controlled faults')
            if db.scalar(select(Event.id).where(Event.task_id == task_id, Event.type == 'FAILURE_INJECTED')):
                raise HTTPException(409, 'Failure already configured')
            if execution:
                config = dict(execution.configuration)
                config['failure'] = {'scenario':body.scenario,'stage_index':index}
                execution.configuration = config
                import json
                message = json.dumps(config['failure'])
            else:
                message = body.scenario
            db.add(Event(task_id=task_id, type='FAILURE_INJECTED', message=message))
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

    @app.get('/agents')
    @app.get('/workers')
    def agents():
        from backend.registry import public_agent
        with factory() as db:
            return [public_agent(row) for row in db.scalars(select(Agent).order_by(Agent.id,Agent.version))]

    @app.post('/agents',status_code=201)
    def register_agent(body: AgentCreate):
        from backend.registry import configuration, public_agent
        with factory.begin() as db:
            versions = list(db.scalars(select(Agent.version).where(Agent.id==body.id)))
            config = configuration(body.name,list(body.capabilities))
            config.update(body.model_dump(mode='json',exclude={'id'}))
            config['health_status'] = 'available' if body.provider=='offline' else 'configured_unverified'
            row = Agent(id=body.id,version=max(versions,default=0)+1,configuration=config)
            db.add(row)
            db.flush()
            return public_agent(row)

    @app.get('/workflows')
    def workflows():
        with factory() as db:
            return [{'id':w.id,**w.definition,'created_at':w.created_at} for w in db.scalars(select(Workflow).order_by(Workflow.id))]

    @app.post('/workflows',status_code=201)
    def create_workflow(body: WorkflowCreate):
        from backend.workflows import resolve_stages
        with factory.begin() as db:
            try:
                resolve_stages(db,[s.model_dump() for s in body.stages])
            except ValueError as exc:
                raise HTTPException(422,str(exc)) from None
            row = Workflow(definition=body.model_dump())
            db.add(row)
            db.flush()
            return {'id':row.id,**row.definition}

    @app.get('/tasks/{task_id}/execution')
    def execution_detail(task_id: str):
        from backend.workflows import execution_report
        get_task(task_id)
        with factory() as db:
            return execution_report(db,task_id)

    @app.post('/comparisons',status_code=202)
    async def compare(body: TaskCreate):
        from backend.workflows import create_execution
        with factory.begin() as db:
            try:
                protected = create_execution(db,body.model_copy(update={'agentbailout_enabled':True}))
                db.flush()
                config = dict(db.get(Execution,protected.id).configuration)
                config['agentbailout_enabled'] = False
                baseline = create_execution(db,body,config)
            except ValueError as exc:
                raise HTTPException(422,str(exc)) from None
            pair = Comparison(baseline_id=baseline.id,protected_id=protected.id)
            db.add(pair)
            db.flush()
            result = {'id':pair.id,'baseline_id':baseline.id,'protected_id':protected.id}
        # Execute sequentially to reduce local contention; configurations and fault are identical.
        claim(factory,baseline.id)
        claim(factory,protected.id)
        async def paired():
            try:
                await execute(factory,baseline.id)
                await execute(factory,protected.id)
            except asyncio.CancelledError:
                with factory() as db:
                    pending = db.get(Task,protected.id).status in {'RUNNING','RESCUING','RESCUED'}
                if pending:
                    fail(factory,protected.id,None,'Comparison interrupted by server shutdown')
                raise
        job = asyncio.create_task(paired())
        jobs.add(job)
        job.add_done_callback(jobs.discard)
        return result

    @app.get('/comparisons')
    def comparisons():
        with factory() as db:
            return [{'id':p.id,'baseline_id':p.baseline_id,'protected_id':p.protected_id} for p in db.scalars(select(Comparison).order_by(Comparison.created_at.desc()).limit(100))]

    @app.get('/comparisons/{comparison_id}')
    def comparison_detail(comparison_id: str):
        from backend.workflows import execution_report
        with factory() as db:
            pair = db.get(Comparison,comparison_id)
            if not pair:
                raise HTTPException(404,'Comparison not found')
            baseline,protected = execution_report(db,pair.baseline_id),execution_report(db,pair.protected_id)
            delta = None if baseline['execution_seconds'] is None or protected['execution_seconds'] is None else protected['execution_seconds']-baseline['execution_seconds']
            allocations = []
            for run in [baseline,protected]:
                allocations.append(Decimal('5.00')-Decimal(run['ledger']['balances'].get('client_refund','0')) if run['ledger']['settled'] else None)
            return {'id':pair.id,'baseline':baseline,'protected':protected,'time_difference_seconds':delta,
                    'simulated_allocation_difference':str(allocations[1]-allocations[0]) if all(a is not None for a in allocations) else None,
                    'api_cost_difference':str(Decimal(protected['api_cost'])-Decimal(baseline['api_cost'])) if baseline['api_cost'] is not None and protected['api_cost'] is not None else None,
                    'note':'Sequential controlled runs with frozen agent versions and identical fault; external LLM outputs can vary. Positive time difference means protection took longer.'}

    return app


app = create_app()
