import asyncio
import json
from time import monotonic
from sqlalchemy import select
from backend.models import Event, Stage, Task, now
from backend.agents.formatter import run
from backend.solvency import evaluate
from backend.watchdog import monitor


def event(factory, task_id, kind, message):
    with factory.begin() as db:
        db.add(Event(task_id=task_id, type=kind, message=message))


async def formatter(factory, task_id, stage_id, data):
    heartbeat = [monotonic()]

    def scenario():
        with factory() as db:
            return db.scalar(select(Event.message).where(Event.task_id == task_id, Event.type == 'FAILURE_INJECTED').order_by(Event.id.desc()).limit(1))

    async def primary():
        for _ in range(10):
            mode = scenario()
            if mode in {'crash', 'backup_failure', 'expensive', 'no_backup'}:
                raise RuntimeError('Primary formatter crashed')
            if mode == 'heartbeat_loss':
                await asyncio.Event().wait()
            heartbeat[0] = monotonic()
            with factory.begin() as db:
                db.get(Stage, stage_id).heartbeat_at = now()
            await asyncio.sleep(0.1)
        return run(data)

    worker = asyncio.create_task(primary())
    try:
        return await monitor(worker, heartbeat)
    except asyncio.CancelledError:
        worker.cancel()
        await asyncio.gather(worker, return_exceptions=True)
        raise
    except (RuntimeError, TimeoutError) as exc:
        from backend.supervisor import transition
        with factory.begin() as db:
            transition(db.get(Task, task_id), 'RESCUING')
        event(factory, task_id, 'FAILURE_DETECTED', str(exc))
        mode = scenario()
        decision = evaluate('3.00' if mode == 'expensive' else '0.25')
        if mode == 'no_backup':
            decision.update(approved=False, reason='No eligible backup')
        event(factory, task_id, 'RESCUE_EVALUATED', json.dumps(decision))
        if not decision['approved']:
            event(factory, task_id, 'RESCUE_REJECTED', decision['reason'])
            raise RuntimeError(decision['reason'])
        with factory.begin() as db:
            stage = db.get(Stage, stage_id)
            if stage.recovery_attempts:
                raise RuntimeError('Recovery already attempted')
            stage.recovery_attempts = 1
            stage.worker_id = 'backup-formatter-01'
        event(factory, task_id, 'RESCUE_APPROVED', decision['reason'])
        event(factory, task_id, 'BACKUP_STARTED', 'backup-formatter-01')
        await asyncio.sleep(0.1)
        if mode == 'backup_failure':
            raise RuntimeError('Backup formatter failed; attempt limit reached')
        result = run(data)
        with factory.begin() as db:
            transition(db.get(Task, task_id), 'RESCUED')
        event(factory, task_id, 'BACKUP_COMPLETED', 'Validated structured formatter result')
        event(factory, task_id, 'WORKFLOW_RESUMED', 'Reused preserved research output')
        return result
