import time
from decimal import Decimal
import pytest
from fastapi.testclient import TestClient
from backend.database import make_database
from backend.main import create_app
from backend.models import Task
from backend.ledger import settle


@pytest.mark.parametrize('scenario,refund', [(None,'1.50'),('crash','2.20'),('expensive','4.00'),('backup_failure','3.70')])
def test_settlement(tmp_path, monkeypatch, scenario, refund):
    monkeypatch.setattr('backend.supervisor.STAGE_SECONDS', 0)
    engine, factory = make_database(f'sqlite:///{tmp_path / "ledger.db"}')
    with TestClient(create_app(engine, factory)) as client:
        task_id = client.post('/tasks', json={'prompt':'Plan a garden'}).json()['id']
        if scenario:
            client.post(f'/tasks/{task_id}/inject-failure', json={'scenario':scenario})
        client.post(f'/tasks/{task_id}/start')
        deadline = time.monotonic()+5
        while time.monotonic()<deadline:
            ledger = client.get(f'/tasks/{task_id}/ledger').json()
            if ledger['settled']:
                break
            time.sleep(.05)
        assert ledger['settled'] and ledger['balanced']
        assert ledger['balances']['escrow'] == '0.00'
        assert ledger['balances']['client_refund'] == refund
        assert sum(Decimal(e['debit']) for e in ledger['entries']) == sum(Decimal(e['credit']) for e in ledger['entries'])
        with factory.begin() as db:
            assert not settle(db, db.get(Task,task_id))
        assert client.get(f'/tasks/{task_id}/ledger').json() == ledger
    engine.dispose()
