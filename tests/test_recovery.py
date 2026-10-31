import time
import pytest
from fastapi.testclient import TestClient
from backend.database import make_database
from backend.main import create_app
from backend.solvency import evaluate


@pytest.mark.parametrize('scenario,expected', [('crash','COMPLETED'), ('heartbeat_loss','COMPLETED'), ('backup_failure','FAILED'), ('expensive','FAILED'), ('no_backup','FAILED')])
def test_recovery(tmp_path, monkeypatch, scenario, expected):
    monkeypatch.setattr('backend.supervisor.STAGE_SECONDS', 0)
    engine, factory = make_database(f'sqlite:///{tmp_path / "rescue.db"}')
    with TestClient(create_app(engine, factory)) as client:
        task_id = client.post('/tasks', json={'prompt':'Plan a garden'}).json()['id']
        assert client.post(f'/tasks/{task_id}/inject-failure', json={'scenario':scenario}).status_code == 200
        assert client.post(f'/tasks/{task_id}/inject-failure', json={'scenario':scenario}).status_code == 409
        client.post(f'/tasks/{task_id}/start')
        deadline = time.monotonic() + 8
        while time.monotonic() < deadline:
            task = client.get(f'/tasks/{task_id}').json()
            if task['status'] in {'COMPLETED','FAILED'}:
                break
            time.sleep(.05)
        assert task['status'] == expected
        events = client.get(f'/tasks/{task_id}/events').json()
        kinds = [e['type'] for e in events]
        assert 'FAILURE_DETECTED' in kinds
        assert 'RESCUE_EVALUATED' in kinds
        if expected == 'COMPLETED':
            assert kinds.count('BACKUP_STARTED') == 1
            assert 'WORKFLOW_RESUMED' in kinds
            assert task['stages'][1]['input'] == task['stages'][0]['result']
            assert task['stages'][1]['recovery_attempts'] == 1
            print('RESCUE DEMO:', ' -> '.join(kinds))
        else:
            assert task['result'] is None
    engine.dispose()


def test_economic_boundaries():
    assert evaluate()['approved']
    assert evaluate()['cost_ratio'] == '0.06'
    assert not evaluate('3')['approved']
    assert not evaluate(value='0')['approved']
    assert not evaluate('-1')['approved']
