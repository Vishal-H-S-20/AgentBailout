import time
from fastapi.testclient import TestClient
from backend.database import make_database
from backend.main import create_app


def test_api_lifecycle(tmp_path, monkeypatch):
    monkeypatch.setattr('backend.supervisor.STAGE_SECONDS', 0.01)
    engine, factory = make_database(f'sqlite:///{tmp_path / "api.db"}')
    with TestClient(create_app(engine, factory)) as client:
        assert client.get('/health').json()['status'] == 'ok'
        assert client.post('/tasks', json={'prompt': 'x'}).status_code == 422
        assert client.post('/tasks', json={'prompt': '   '}).status_code == 422
        assert client.get('/tasks/missing').status_code == 404
        response = client.post('/tasks', json={'prompt': 'Design a water saving plan'})
        assert response.status_code == 201
        task_id = response.json()['id']
        assert response.json()['status'] == 'CREATED'
        assert client.post(f'/tasks/{task_id}/start').status_code == 202
        assert client.post(f'/tasks/{task_id}/start').status_code == 409
        deadline = time.monotonic() + 5
        while time.monotonic() < deadline:
            task = client.get(f'/tasks/{task_id}').json()
            if task['status'] in {'COMPLETED', 'FAILED'}:
                break
            time.sleep(0.01)
        assert task['status'] == 'COMPLETED'
        assert task['result']['summary']
        events = client.get(f'/tasks/{task_id}/events').json()
        assert [e['message'] for e in events if e['type'] == 'AGENT_COMPLETED'] == ['Research', 'Formatter', 'Synthesis']
        assert len(client.get('/tasks').json()) == 1
    engine.dispose()
