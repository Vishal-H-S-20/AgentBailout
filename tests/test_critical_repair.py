import time
import pytest
from fastapi.testclient import TestClient
from backend.database import make_database
from backend.main import create_app
from backend.diagnostics import diagnose, DiagnosticRequest
import asyncio


@pytest.fixture
def client(tmp_path,monkeypatch):
    monkeypatch.setattr('backend.supervisor.STAGE_SECONDS',.05)
    engine,factory=make_database(f'sqlite:///{tmp_path / "critical.db"}')
    with TestClient(create_app(engine,factory)) as client:
        yield client
    engine.dispose()


def wait(client,identity):
    end=time.monotonic()+8
    while time.monotonic()<end:
        run=client.get(f'/tasks/{identity}/execution').json()
        if run['status'] in {'COMPLETED','FAILED'} and run['execution_seconds'] is not None:
            return run
        time.sleep(.02)
    pytest.fail('Execution deadline exceeded')


@pytest.mark.parametrize('scenario,protected,outcome,recovery',[('normal',True,'COMPLETED',0),('crash',False,'FAILED',0),('crash',True,'COMPLETED',1)])
def test_preconfigured_fault_persisted_and_executed(client,scenario,protected,outcome,recovery):
    identity=client.post('/tasks',json={'prompt':'Critical acceptance task','agentbailout_enabled':protected,'failure':{'scenario':scenario,'stage_index':1}}).json()['id']
    run=client.get(f'/tasks/{identity}/execution').json()
    assert run['configuration']['failure']=={'scenario':scenario,'stage_index':1}
    client.post(f'/tasks/{identity}/start')
    run=wait(client,identity)
    assert run['status']==outcome and run['recovery_attempts']==recovery
    stages=client.get(f'/tasks/{identity}').json()['stages']
    assert stages[0]['status']=='COMPLETED'
    if scenario=='crash':
        primary=[a for a in run['attempts'] if a['stage_id']==stages[1]['id'] and not a['recovery']]
        assert len(primary)==1 and primary[0]['status']=='FAILED' and primary[0]['error_category']=='WORKER_CRASH'
    if outcome=='COMPLETED':
        assert stages[2]['status']=='COMPLETED' and run['output_valid']
    assert run['ledger']['settled'] and run['ledger']['balanced']


def test_manual_injection_duplicate_and_terminal_reason(client):
    identity=client.post('/tasks',json={'prompt':'Manual acceptance task'}).json()['id']
    injected=client.post(f'/tasks/{identity}/inject-failure',json={'scenario':'crash','stage_index':1})
    assert injected.status_code==200 and injected.json()['task_id']==identity
    duplicate=client.post(f'/tasks/{identity}/inject-failure',json={'scenario':'crash','stage_index':1})
    assert duplicate.status_code==409 and duplicate.json()['detail']['code']=='FAULT_ALREADY_CONFIGURED'
    client.post(f'/tasks/{identity}/start')
    run=wait(client,identity)
    assert run['status']=='COMPLETED' and run['recovery_attempts']==1
    terminal=client.post(f'/tasks/{identity}/inject-failure',json={'scenario':'crash','stage_index':1})
    assert terminal.status_code==409 and terminal.json()['detail']['code']=='TASK_TERMINAL'


def test_manual_injection_while_upstream_running(client,monkeypatch):
    monkeypatch.setattr('backend.supervisor.STAGE_SECONDS',.3)
    identity=client.post('/tasks',json={'prompt':'Inject during upstream'}).json()['id']
    client.post(f'/tasks/{identity}/start')
    response=client.post(f'/tasks/{identity}/inject-failure',json={'scenario':'crash','stage_index':1})
    assert response.status_code==200,response.text
    assert wait(client,identity)['recovery_attempts']==1


def test_stage_started_and_preconfigured_duplicate(client,monkeypatch):
    monkeypatch.setattr('backend.supervisor.STAGE_SECONDS',.4)
    identity=client.post('/tasks',json={'prompt':'Started stage test'}).json()['id']
    client.post(f'/tasks/{identity}/start')
    end=time.monotonic()+2
    while time.monotonic()<end:
        if client.get(f'/tasks/{identity}').json()['stages'][0]['status']=='RUNNING':
            break
        time.sleep(.01)
    response=client.post(f'/tasks/{identity}/inject-failure',json={'scenario':'crash','stage_index':0})
    assert response.status_code==409 and response.json()['detail']['code']=='STAGE_STARTED'
    identity=client.post('/tasks',json={'prompt':'Preconfigured duplicate test','failure':{'scenario':'crash','stage_index':1}}).json()['id']
    response=client.post(f'/tasks/{identity}/inject-failure',json={'scenario':'crash','stage_index':1})
    assert response.status_code==409 and response.json()['detail']['code']=='FAULT_ALREADY_CONFIGURED'
    assert client.get(f'/tasks/{identity}/execution').json()['configuration']['failure']['stage_index']==1


def test_repeated_creation_exact_ids(client):
    identities=[]
    for i,scenario in enumerate(['normal','crash','normal','crash']):
        task=client.post('/tasks',json={'prompt':f'Task {i}','failure':{'scenario':scenario,'stage_index':1}}).json()
        identities.append(task['id'])
        run=client.get(f'/tasks/{task["id"]}/execution').json()
        assert run['configuration']['failure']['scenario']==scenario
        assert task['status']=='CREATED'
    assert len(set(identities))==4


def test_runtime_normalization_and_rejection(client):
    result=client.post('/diagnostics',json={'kind':'python','amount':'12.50','protection':True}).json()
    assert result['primary']['exit_code']!=0 and 'TypeError' in result['primary']['stderr']
    assert result['status']=='RECOVERED' and result['recovery']['exit_code']==0
    baseline=client.post('/diagnostics',json={'kind':'python','protection':False}).json()
    assert baseline['status']=='FAILED' and baseline['recovery'] is None
    invalid=client.post('/diagnostics',json={'kind':'python','amount':'missing'}).json()
    assert invalid['status']=='FAILED' and invalid['recovery'] is None
    assert len(client.get('/diagnostics').json())==3


def test_repository_static_diagnosis_no_execution(client):
    result=client.post('/diagnostics',json={'kind':'repository','source':'def value():\nreturn 1'}).json()
    assert result['status']=='FAILED' and result['events'][0]['event']=='SYNTAX_FAILURE'
    result=client.post('/diagnostics',json={'kind':'repository','source':'raise RuntimeError("never execute this")'}).json()
    assert result['status']=='VALID'
    assert client.post('/diagnostics',json={'kind':'repository','repository_url':'http://localhost/private'}).status_code==422


def test_friendly_conflict_message():
    from streamlit.testing.v1 import AppTest
    app=AppTest.from_string('''
import httpx
from dashboard.components import friendly_error
request=httpx.Request('POST','http://localhost/tasks/test/inject-failure')
response=httpx.Response(409,request=request,json={'detail':{'code':'FAULT_ALREADY_CONFIGURED','message':'A failure is already configured for this stage.'}})
friendly_error(httpx.HTTPStatusError('raw exception',request=request,response=response))
''').run()
    assert not app.exception
    assert app.error[0].value=='A failure is already configured for this stage.'
    assert 'HTTP 409' in app.code[0].value


def test_lossy_numeric_repair_is_not_success(client):
    result=client.post('/diagnostics',json={'kind':'python','amount':'0.1234567890123456789'}).json()
    assert result['status']=='FAILED'
    assert result['events'][-1]['event']=='REPAIR_FAILED'
