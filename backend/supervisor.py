import asyncio
from time import monotonic
from sqlalchemy import update, select
from backend.models import Task, Stage, Event, LedgerEntry, now
from backend.config import STAGE_SECONDS
from backend.agents import research, formatter, synthesis

AGENTS = [('Research', research.run), ('Formatter', formatter.run), ('Synthesis', synthesis.run)]
TRANSITIONS = {'CREATED': {'RUNNING'}, 'RUNNING': {'COMPLETED', 'FAILED'}}
TRANSITIONS['RUNNING'].add('RESCUING')
TRANSITIONS['RESCUING'] = {'RESCUED', 'FAILED'}
TRANSITIONS['RESCUED'] = {'COMPLETED', 'FAILED'}


def transition(task: Task, status: str) -> None:
    if status not in TRANSITIONS.get(task.status, set()):
        raise ValueError(f'Invalid transition {task.status} -> {status}')
    task.status, task.updated_at = status, now()


def claim(factory, task_id: str) -> bool:
    with factory.begin() as db:
        changed = db.execute(update(Task).where(Task.id == task_id, Task.status == 'CREATED')
                             .values(status='RUNNING', updated_at=now())).rowcount
        if changed:
            db.add(Event(task_id=task_id, type='TASK_STARTED', message='Pipeline started'))
        return bool(changed)


async def execute(factory, task_id: str) -> None:
    active_id = None
    try:
        with factory() as db:
            task = db.get(Task, task_id)
            data = {'prompt': task.prompt}
            stages = [(s.id, fn) for s, (_, fn) in zip(task.stages, AGENTS)]
        for active_id, fn in stages:
            started = monotonic()
            with factory.begin() as db:
                stage = db.get(Stage, active_id)
                stage.status, stage.started_at = 'RUNNING', now()
                stage.heartbeat_at, stage.input = now(), data
                db.add(Event(task_id=task_id, type='AGENT_STARTED', message=stage.name))
            await asyncio.sleep(STAGE_SECONDS)
            if fn is formatter.run:
                from backend.recovery import formatter as recoverable_formatter
                data = await recoverable_formatter(factory, task_id, active_id, data)
            else:
                data = fn(data)
            with factory.begin() as db:
                stage = db.get(Stage, active_id)
                stage.result, stage.status, stage.ended_at = data, 'COMPLETED', now()
                stage.duration_seconds = monotonic() - started
                db.add(Event(task_id=task_id, type='AGENT_COMPLETED', message=stage.name))
        with factory.begin() as db:
            task = db.get(Task, task_id)
            task.result = data
            transition(task, 'COMPLETED')
            db.add(Event(task_id=task_id, type='TASK_COMPLETED', message='All three stages completed'))
            from backend.ledger import settle
            if db.scalar(select(LedgerEntry.id).where(LedgerEntry.task_id == task_id)):
                settle(db, task)
    except asyncio.CancelledError:
        fail(factory, task_id, active_id, 'Execution interrupted by server shutdown')
        raise
    except Exception as exc:
        fail(factory, task_id, active_id, str(exc))


def fail(factory, task_id: str, stage_id: str | None, message: str) -> None:
    with factory.begin() as db:
        task = db.get(Task, task_id)
        transition(task, 'FAILED')
        task.error = message
        if stage_id:
            stage = db.get(Stage, stage_id)
            stage.status, stage.error, stage.ended_at = 'FAILED', message, now()
        else:
            for stage in task.stages:
                if stage.status == 'RUNNING':
                    stage.status, stage.error, stage.ended_at = 'FAILED', message, now()
        db.add(Event(task_id=task_id, type='TASK_FAILED', message=message))
        from backend.ledger import settle
        from backend.models import LedgerEntry
        from sqlalchemy import select
        if db.scalar(select(LedgerEntry.id).where(LedgerEntry.task_id == task_id)):
            settle(db, task)
