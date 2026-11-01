import time
import pytest
from fastapi.testclient import TestClient
from backend.database import make_database
from backend.main import create_app
from backend.models import AttemptEvidence


@pytest.fixture
def client(tmp_path,monkeypatch):
    monkeypatch.setattr('backend.supervisor.STAGE_SECONDS',0)
    engine,factory=make_database(f'sqlite:///{tmp_path / "evidence.db"}')
    with TestClient(create_app(engine,factory)) as client:
        client.factory=factory
        yield client
    engine.dispose()


def wait(client,identity):
    end=time.monotonic()+8
    while time.monotonic()<end:
        report=client.get(f'/tasks/{identity}/execution').json()
        if report['execution_seconds'] is not None:
            return report
        time.sleep(.02)
    pytest.fail('Execution did not finish')


def test_invalid_chain_has_actionable_explanation(client):
    body={'name':'Invalid user example','stages':[{'name':name,'operation':op,'agent_id':'offline-'+op} for name,op in [('Research','research'),('Formatter','format'),('Plan','plan'),('Extract','extract')]]}
    response=client.post('/workflows',json=body)
    assert response.status_code==422
    message=response.json()['detail']
    assert 'Step 3' in message and 'Plan' in message and 'Formatter' in message
    assert 'Task brief' in message and 'Formatted report' in message and 'Summarize' in message
    assert 'input contract' not in message


def test_catalog_describes_real_compatibility(client):
    catalog=client.get('/contracts').json()
    assert catalog['research']['next']==['format']
    assert catalog['format']['next']==['summarize']
    assert catalog['summarize']['next']==[]
    assert 'code' in catalog['plan']['next'] and 'validate' in catalog['code']['next']
    assert catalog['format']['input']=='Research findings'
    assert catalog['format']['output']=='Formatted report'


@pytest.mark.parametrize('scenario',['crash','invalid_output'])
def test_failure_and_replacement_have_independent_persisted_evidence(client,scenario):
    identity=client.post('/tasks',json={'prompt':'Trace the actual work','failure':{'scenario':scenario,'stage_index':1}}).json()['id']
    client.post(f'/tasks/{identity}/start')
    report=wait(client,identity)
    assert report['status']=='COMPLETED'
    formatter=report['stages'][1]
    primary,backup=formatter['attempts']
    assert primary['status']=='FAILED' and backup['status']=='COMPLETED'
    assert primary['evidence_available'] and backup['evidence_available']
    assert primary['input']==backup['input']==report['stages'][0]['output']
    assert primary['output']==({} if scenario=='invalid_output' else None)
    assert primary['error_message']
    assert backup['output']==formatter['output']==report['stages'][2]['input']
    assert formatter['input_contract']=='Research findings' and formatter['output_contract']=='Formatted report'
    assert primary['agent_name'] and primary['provider']=='offline'
    assert any(e['type']=='BACKUP_SELECTED' for e in report['events'])
    with client.factory() as db:
        assert db.get(AttemptEvidence,backup['id']).output==backup['output']


def test_comparison_includes_failed_and_resumed_stages(client):
    pair=client.post('/comparisons',json={'prompt':'Judge comparison','failure':{'scenario':'crash'}}).json()
    baseline=wait(client,pair['baseline_id'])
    protected=wait(client,pair['protected_id'])
    assert [s['status'] for s in baseline['stages']]==['COMPLETED','FAILED','SKIPPED']
    assert all(s['status']=='COMPLETED' for s in protected['stages'])
    assert baseline['stages'][1]['attempts'][0]['error_message']=='Controlled worker crash'
    result=client.get('/comparisons/'+pair['id']).json()
    assert result['baseline']['stages'][1]['input']==result['protected']['stages'][1]['input']
    assert result['protected']['stages'][1]['attempts'][1]['recovery']
    assert result['protected']['ledger']['balanced']


def test_historical_attempt_output_is_not_invented(client):
    identity=client.post('/tasks',json={'prompt':'Historical missing evidence'}).json()['id']
    client.post(f'/tasks/{identity}/start')
    report=wait(client,identity)
    with client.factory.begin() as db:
        db.delete(db.get(AttemptEvidence,report['attempts'][0]['id']))
    historical=client.get(f'/tasks/{identity}/execution').json()
    assert not historical['attempts'][0]['evidence_available']
    assert historical['attempts'][0]['output'] is None
    assert historical['stages'][0]['output'] is not None
