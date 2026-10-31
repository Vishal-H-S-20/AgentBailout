import asyncio
import json
import time
from copy import deepcopy
import httpx
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from backend.database import Base, make_database
from backend.main import create_app
from backend.models import Task, Stage, Event, Agent, Execution, Attempt
from backend.providers import OpenAIProvider, ProviderFailure
from backend.contracts import CONTRACTS, offline
from backend.registry import configuration, compatible
from backend.migrations import migrate


@pytest.fixture
def client(tmp_path,monkeypatch):
    monkeypatch.setattr('backend.supervisor.STAGE_SECONDS',0)
    engine,factory = make_database(f'sqlite:///{tmp_path / "phase4.db"}')
    with TestClient(create_app(engine,factory)) as client:
        client.factory = factory
        yield client
    engine.dispose()


def wait(client,task_id):
    deadline = time.monotonic()+10
    while time.monotonic()<deadline:
        report = client.get(f'/tasks/{task_id}/execution').json()
        if report['status'] in {'COMPLETED','FAILED'} and report['execution_seconds'] is not None:
            assert report['ledger']['balanced'] and report['ledger']['settled']
            assert report['ledger']['balances']['escrow']=='0.00'
            return report
        time.sleep(.02)
    pytest.fail('Execution exceeded test deadline')


@pytest.mark.parametrize('template',['research','coding','document'])
@pytest.mark.parametrize('index',[0,1,2])
def test_universal_recovery_any_stage(client,template,index):
    response = client.post('/tasks',json={'prompt':'Build a useful project','workflow_id':'template-'+template,
                                        'failure':{'scenario':'crash','stage_index':index}})
    assert response.status_code==201,response.text
    task_id=response.json()['id']
    assert client.post(f'/tasks/{task_id}/start').status_code==202
    run=wait(client,task_id)
    assert run['status']=='COMPLETED' and run['output_valid']
    assert run['recovery_attempts']==1
    assert run['api_cost']=='0.00'
    stages=client.get(f'/tasks/{task_id}').json()['stages']
    assert all(s['status']=='COMPLETED' for s in stages)
    for i in range(1,len(stages)):
        assert stages[i]['input']==stages[i-1]['result']
    assert len(run['attempts'])==4


@pytest.mark.parametrize('scenario,expected',[
    ('normal','COMPLETED'),('timeout','COMPLETED'),('heartbeat_loss','COMPLETED'),
    ('invalid_output','COMPLETED'),('tool_failure','COMPLETED'),
    ('backup_failure','FAILED'),('shared_failure','FAILED'),('expensive','FAILED'),
    ('insufficient_budget','FAILED'),('no_backup','FAILED'),('exhausted','FAILED')])
def test_fault_matrix(client,scenario,expected):
    body={'prompt':'Controlled fault test','failure':{'scenario':scenario},'stage_timeout':.5,'heartbeat_timeout':.2,'max_attempts':3}
    task_id=client.post('/tasks',json=body).json()['id']
    client.post(f'/tasks/{task_id}/start')
    run=wait(client,task_id)
    assert run['status']==expected
    assert run['recovery_attempts']<=3
    if scenario in {'shared_failure','backup_failure','exhausted'}:
        kinds=[e['type'] for e in client.get(f'/tasks/{task_id}/events').json()]
        assert 'SHARED_FAILURE_DETECTED' in kinds
        assert run['recovery_attempts']==1


def test_baseline_and_frozen_comparison(client):
    pair=client.post('/comparisons',json={'prompt':'Compare controlled runs','workflow_id':'template-coding',
                                       'failure':{'scenario':'crash','stage_index':2}})
    assert pair.status_code==202,pair.text
    pair=pair.json()
    baseline=wait(client,pair['baseline_id'])
    protected=wait(client,pair['protected_id'])
    assert baseline['status']=='FAILED' and baseline['recovery_attempts']==0
    assert protected['status']=='COMPLETED' and protected['recovery_attempts']==1
    baseconfig=deepcopy(baseline['configuration'])
    baseconfig['agentbailout_enabled']=True
    assert baseconfig==protected['configuration']
    kinds=[e['type'] for e in client.get(f'/tasks/{pair["baseline_id"]}/events').json()]
    assert 'RECOVERY_DISABLED' in kinds and 'RESCUE_EVALUATED' not in kinds
    response=client.get('/comparisons/'+pair['id']).json()
    assert isinstance(response['time_difference_seconds'],float)


def test_registry_versions_custom_workflow_and_snapshot(client):
    body={'id':'custom','name':'Custom document agent','capabilities':['plan','code','validate']}
    assert client.post('/agents',json=body).json()['version']==1
    body['name']='New immutable version'
    assert client.post('/agents',json=body).json()['version']==2
    definitions=[{'name':op,'operation':op,'agent_id':'custom','version':1} for op in ['plan','validate','code','validate']]
    saved=client.post('/workflows',json={'name':'Reordered four-stage flow','stages':definitions})
    assert saved.status_code==201,saved.text
    task_id=client.post('/tasks',json={'prompt':'Test saved workflow','workflow_id':saved.json()['id']}).json()['id']
    client.post(f'/tasks/{task_id}/start')
    report=wait(client,task_id)
    assert report['status']=='COMPLETED'
    assert all(a['agent_version']==1 for a in report['attempts'])
    assert report['configuration']['stages'][0]['agent']['name']=='Custom document agent'
    agents=client.get('/agents').json()
    first=next(a for a in agents if a['id']=='custom' and a['version']==1)
    assert first['successful_executions']==4
    assert first['observed_average_latency']>0
    assert first['measured_reliability']==1
    assert client.post('/tasks',json={'prompt':'Invalid order','stages':list(reversed(definitions[:2]))}).status_code==422


def test_compatibility_and_missing_provider(client,monkeypatch):
    monkeypatch.delenv('OPENAI_API_KEY',raising=False)
    row=client.post('/agents',json={'id':'external','name':'External','provider':'openai','model':'configured-model','capabilities':['research']}).json()
    assert row['provider_health']['status']=='unavailable'
    assert client.post('/tasks',json={'prompt':'Real execution','stages':[{'name':'Research','operation':'research','agent_id':'external'}]}).status_code==422
    config=configuration('Tools',['research'])
    config['required_tools']=['shell']
    assert not compatible(config,'research')[0]
    config['required_tools']=[]
    config['output_schema']['research']={}
    assert not compatible(config,'research')[0]


def test_no_compatible_pool_and_budget(client):
    task_id=client.post('/tasks',json={'prompt':'Plan protected test','workflow_id':'template-coding',
        'failure':{'scenario':'crash','stage_index':0},'recovery_pool':[{'agent_id':'recovery-document'}]}).json()['id']
    client.post(f'/tasks/{task_id}/start')
    report=wait(client,task_id)
    assert report['status']=='FAILED' and report['recovery_attempts']==0
    assert report['ledger']['balances']['client_refund']=='5.00'
    task_id=client.post('/tasks',json={'prompt':'Budget protected test','recovery_budget':'0.29','failure':{'scenario':'crash'}}).json()['id']
    client.post(f'/tasks/{task_id}/start')
    report=wait(client,task_id)
    assert report['status']=='FAILED' and report['recovery_attempts']==0


def test_real_adapter_mocked_http(monkeypatch):
    monkeypatch.setenv('OPENAI_API_KEY','test-only-placeholder')
    config=configuration('External',['research'])
    config.update(provider='openai',model='configured-model')
    output=offline('research',{'prompt':'Plan a garden'})
    def handler(request):
        body=json.loads(request.content)
        assert body['model']=='configured-model'
        assert body['text']['format']['schema']==CONTRACTS['research'][1]
        assert body['store'] is False
        return httpx.Response(200,json={'status':'completed','usage':{'input_tokens':10,'output_tokens':20},
            'output':[{'type':'message','content':[{'type':'output_text','text':json.dumps(output)}]}]})
    adapter=OpenAIProvider(httpx.MockTransport(handler))
    result=asyncio.run(adapter.execute(config,'research',{'prompt':'Plan a garden'},CONTRACTS['research'][1]))
    assert result.output==output and result.usage['input_tokens']==10
    assert result.api_cost is None
    bad=OpenAIProvider(httpx.MockTransport(lambda request:httpx.Response(429,text='secret provider body')))
    with pytest.raises(ProviderFailure) as error:
        asyncio.run(bad.execute(config,'research',{'prompt':'Plan'},CONTRACTS['research'][1]))
    assert error.value.category=='RATE_LIMIT' and 'secret' not in str(error.value)


def test_additive_migration_preserves_old_data(tmp_path):
    engine,factory=make_database(f'sqlite:///{tmp_path / "old.db"}')
    Base.metadata.create_all(engine,tables=[Task.__table__,Stage.__table__,Event.__table__])
    with factory.begin() as db:
        task=Task(prompt='Historical result',status='COMPLETED',result={'summary':'Keep me'})
        db.add(task)
        db.flush()
        identity=task.id
    migrate(engine)
    migrate(engine)
    with factory() as db:
        assert db.get(Task,identity).result=={'summary':'Keep me'}
    assert len(list(tmp_path.glob('old.pre-v4-*.db')))==1
    engine.dispose()


def test_restart_reconciles_interrupted_attempts(tmp_path):
    from backend.models import now
    engine,factory=make_database(f'sqlite:///{tmp_path / "restart.db"}')
    with TestClient(create_app(engine,factory)) as first:
        task_id=first.post('/tasks',json={'prompt':'Interrupted persisted task'}).json()['id']
        with factory.begin() as db:
            task=db.get(Task,task_id)
            task.status='RUNNING'
            stage=task.stages[0]
            stage.status='RUNNING'
            db.get(Execution,task_id).started_at=now()
            db.add(Attempt(task_id=task_id,stage_id=stage.id,agent_id='offline-research',agent_version=1,recovery=False))
    with TestClient(create_app(engine,factory)) as second:
        run=second.get(f'/tasks/{task_id}/execution').json()
        assert run['status']=='FAILED' and run['ledger']['settled']
        assert run['attempts'][0]['status']=='FAILED'
        assert run['attempts'][0]['error_category']=='INTERRUPTED'
        assert run['ledger']['balances']['client_refund']=='5.00'
        assert run['execution_seconds'] is not None
    engine.dispose()


@pytest.mark.parametrize('valid',[True,False])
def test_external_adapter_through_engine_with_mock_http(client,monkeypatch,valid):
    from backend.providers import provider as real_provider
    monkeypatch.setenv('OPENAI_API_KEY','test-only-placeholder')
    config={'id':'mock-external','name':'External fixture','provider':'openai','model':'configured-model','capabilities':['research']}
    assert client.post('/agents',json=config).status_code==201
    output=offline('research',{'prompt':'Plan a garden'})
    output['source']='Mocked external HTTP fixture; not a live model response'
    if not valid:
        output={}
    transport=httpx.MockTransport(lambda request:httpx.Response(200,json={'status':'completed',
        'usage':{'input_tokens':12,'output_tokens':30},
        'output':[{'type':'message','content':[{'type':'output_text','text':json.dumps(output)}]}]}))
    monkeypatch.setattr('backend.execution_engine.provider',lambda name:OpenAIProvider(transport) if name=='openai' else real_provider(name))
    task_id=client.post('/tasks',json={'prompt':'Plan a garden','agentbailout_enabled':False,'stages':[{'name':'External research','operation':'research','agent_id':'mock-external'}]}).json()['id']
    client.post(f'/tasks/{task_id}/start')
    run=wait(client,task_id)
    assert run['status']==('COMPLETED' if valid else 'FAILED')
    assert run['attempts'][0]['usage']=={'input_tokens':12,'output_tokens':30}
    assert run['api_cost'] is None
    assert run['output']==(output if valid else None)


def test_timeout_fences_slow_provider_output(client,monkeypatch):
    from backend.providers import OfflineProvider, ProviderResult
    class SlowProvider(OfflineProvider):
        cancelled=False
        async def execute(self,*args):
            try:
                await asyncio.sleep(10)
            except asyncio.CancelledError:
                self.cancelled=True
                raise
            return ProviderResult({'stale':'must never be saved'})
    slow=SlowProvider()
    monkeypatch.setattr('backend.execution_engine.provider',lambda name:slow)
    task_id=client.post('/tasks',json={'prompt':'Slow baseline','agentbailout_enabled':False,'stage_timeout':.25}).json()['id']
    client.post(f'/tasks/{task_id}/start')
    run=wait(client,task_id)
    assert run['status']=='FAILED' and run['output'] is None and slow.cancelled
    assert run['attempts'][0]['error_category']=='TIMEOUT'
    assert run['attempts'][0]['output_valid'] is False
    assert all(a['status']!='RUNNING' for a in run['attempts'])


def test_candidate_latency_budget_and_duplicate_pool(client):
    duplicate={'prompt':'Duplicate recovery pool','recovery_pool':[{'agent_id':'recovery-general'},{'agent_id':'recovery-general'}]}
    assert client.post('/tasks',json=duplicate).status_code==422
    assert client.post('/agents',json={'id':'too-slow','name':'Slow estimate','capabilities':['format'],'estimated_latency':20}).status_code==201
    task_id=client.post('/tasks',json={'prompt':'Latency constrained','failure':{'scenario':'crash'},
        'recovery_pool':[{'agent_id':'too-slow'}],'stage_timeout':1}).json()['id']
    client.post(f'/tasks/{task_id}/start')
    run=wait(client,task_id)
    assert run['status']=='FAILED' and run['recovery_attempts']==0
    events=client.get(f'/tasks/{task_id}/events').json()
    evaluation=json.loads(next(e['message'] for e in events if e['type']=='RECOVERY_CANDIDATES'))
    assert 'latency' in evaluation[0]['reason']


@pytest.mark.parametrize('payload,category',[
    ({'status':'incomplete','output':[]},'MODEL_FAILURE'),
    ({'status':'completed','output':[{'type':'message','content':[{'type':'refusal','refusal':'No'}]}]},'INVALID_OUTPUT'),
    ({'status':'completed','output':[{'type':'message','content':[{'type':'output_text','text':'bad JSON'}]}]},'INVALID_OUTPUT')])
def test_provider_rejects_incomplete_refusal_and_invalid_json(monkeypatch,payload,category):
    monkeypatch.setenv('OPENAI_API_KEY','test-only-placeholder')
    adapter=OpenAIProvider(httpx.MockTransport(lambda request:httpx.Response(200,json=payload)))
    with pytest.raises(ProviderFailure) as error:
        asyncio.run(adapter.execute(configuration('Test',['research']),'research',{'prompt':'Test'},CONTRACTS['research'][1]))
    assert error.value.category==category
