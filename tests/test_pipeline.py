import asyncio
from backend.database import Base, make_database
from backend.models import Task, Stage
from backend.supervisor import AGENTS, claim, execute, transition
import pytest


def test_pipeline_and_persistence(tmp_path, monkeypatch):
    monkeypatch.setattr('backend.supervisor.STAGE_SECONDS', 0)
    url = f'sqlite:///{tmp_path / "test.db"}'
    engine, factory = make_database(url)
    Base.metadata.create_all(engine)
    with factory.begin() as db:
        task = Task(prompt='Plan a community garden')
        task.stages = [Stage(name=n, position=i) for i, (n, _) in enumerate(AGENTS)]
        db.add(task)
        db.flush()
        task_id = task.id
    assert claim(factory, task_id)
    assert not claim(factory, task_id)
    asyncio.run(execute(factory, task_id))
    engine.dispose()
    reopened, sessions = make_database(url)
    with sessions() as db:
        task = db.get(Task, task_id)
        assert task.status == 'COMPLETED'
        assert 'community garden' in task.result['summary']
        assert [s.name for s in task.stages] == ['Research', 'Formatter', 'Synthesis']
        assert all(s.status == 'COMPLETED' and s.duration_seconds >= 0 for s in task.stages)
        assert task.stages[1].input == task.stages[0].result
        assert task.stages[2].input == task.stages[1].result
    reopened.dispose()


def test_invalid_transition():
    task = Task(prompt='Example', status='CREATED')
    with pytest.raises(ValueError):
        transition(task, 'COMPLETED')


def test_agent_error_never_completes_task(tmp_path, monkeypatch):
    monkeypatch.setattr('backend.supervisor.STAGE_SECONDS', 0)
    def broken(data):
        raise ValueError('Invalid research output')
    monkeypatch.setattr('backend.supervisor.AGENTS', [('Research', broken)])
    engine, factory = make_database(f'sqlite:///{tmp_path / "failure.db"}')
    Base.metadata.create_all(engine)
    with factory.begin() as db:
        task = Task(prompt='Example task', stages=[Stage(name='Research', position=0)])
        db.add(task)
        db.flush()
        task_id = task.id
    assert claim(factory, task_id)
    asyncio.run(execute(factory, task_id))
    with factory() as db:
        task = db.get(Task, task_id)
        assert task.status == 'FAILED'
        assert task.result is None
        assert task.stages[0].error == 'Invalid research output'
    engine.dispose()
