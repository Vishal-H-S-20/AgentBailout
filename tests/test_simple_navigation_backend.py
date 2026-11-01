import asyncio
import json
import time
from decimal import Decimal
import httpx
import pytest
from fastapi.testclient import TestClient
from backend.database import make_database
from backend.main import create_app
from backend.contracts import offline
from backend.policy import rank_candidates
from backend.providers import GeminiProvider,OllamaProvider,provider as real_provider


@pytest.fixture
def client(tmp_path,monkeypatch):
    monkeypatch.setattr('backend.supervisor.STAGE_SECONDS',0)
    engine,factory=make_database(f'sqlite:///{tmp_path / "navigation.db"}')
    with TestClient(create_app(engine,factory)) as client:
        yield client
    engine.dispose()


def wait(client,identity):
    end=time.monotonic()+8
    while time.monotonic()<end:
        run=client.get(f'/tasks/{identity}/execution').json()
        if run['execution_seconds'] is not None:
            return run
        time.sleep(.02)
    pytest.fail('Execution deadline exceeded')


def test_cost_time_balanced_choose_real_candidates():
    cheap={'id':'cheap','version':1,'estimated_cost':'0.10','estimated_latency':2.0,'selection_reliability':'.95'}
    fast={'id':'fast','version':1,'estimated_cost':'0.50','estimated_latency':.1,'selection_reliability':'.95'}
    assert rank_candidates([fast,cheap],'cost')[0]['id']=='cheap'
    assert rank_candidates([cheap,fast],'time')[0]['id']=='fast'
    # 0.4*(.15/.55)+0.35*1+0.25*.05 > 0.4*1+0.35*(.1/2)+0.25*.05
    assert rank_candidates([cheap,fast],'balanced')[0]['id']=='fast'


@pytest.mark.parametrize('strategy,chosen',[('cost','cheap'),('time','fast'),('balanced','fast')])
def test_selected_policy_controls_actual_replacement(client,strategy,chosen):
    for identity,cost,latency in [('cheap','0.10',.3),('fast','0.50',.05)]:
        client.post('/agents',json={'id':identity,'name':identity,'capabilities':['format'],'estimated_cost':cost,'estimated_latency':latency})
    identity=client.post('/tasks',json={'prompt':'Choose a viable backup','optimization':strategy,'failure':{'scenario':'crash'},'recovery_pool':[{'agent_id':'cheap'},{'agent_id':'fast'}]}).json()['id']
    client.post(f'/tasks/{identity}/start')
    run=wait(client,identity)
    assert run['status']=='COMPLETED'
    assert next(a for a in run['attempts'] if a['recovery'])['agent_id']==chosen
    assert run['ledger']['balanced']


def test_custom_budget_and_deadline_are_enforced(client):
    identity=client.post('/tasks',json={'prompt':'Budget test','task_budget':'8.00'}).json()['id']
    client.post(f'/tasks/{identity}/start')
    run=wait(client,identity)
    assert run['status']=='COMPLETED'
    assert run['ledger']['balances']['client']=='-8.00'
    assert run['ledger']['balances']['client_refund']=='4.50'
    identity=client.post('/tasks',json={'prompt':'Deadline test','deadline_seconds':.15}).json()['id']
    client.post(f'/tasks/{identity}/start')
    run=wait(client,identity)
    assert run['status']=='FAILED' and run['output'] is None
    assert run['ledger']['balanced'] and run['ledger']['settled']
    assert client.post('/tasks',json={'prompt':'Impossible budget','task_budget':'1.00','recovery_budget':'1.00'}).status_code==422


def test_deadline_caps_demo_delay(client,monkeypatch):
    monkeypatch.setattr('backend.supervisor.STAGE_SECONDS',1)
    identity=client.post('/tasks',json={'prompt':'Short deadline','deadline_seconds':.15}).json()['id']
    client.post(f'/tasks/{identity}/start')
    run=wait(client,identity)
    assert run['status']=='FAILED' and run['execution_seconds']<.5


def test_saved_recovery_pool_survives_new_request(client):
    definitions=client.get('/workflows').json()
    research=next(w for w in definitions if w['id']=='template-research')
    workflow=client.post('/workflows',json={'name':'Persistent pool','stages':research['stages'],'recovery_pool':[{'agent_id':'recovery-document'}]}).json()
    created=client.post('/tasks',json={'prompt':'Use stored backup choices','workflow_id':workflow['id']}).json()
    run=client.get(f'/tasks/{created["id"]}/execution').json()
    assert [a['id'] for a in run['configuration']['recovery_pool']]==['recovery-document']


@pytest.mark.parametrize('source',['gemini','ollama'])
def test_configured_provider_registers_and_executes_with_http_mock(client,monkeypatch,source):
    monkeypatch.setenv('GEMINI_API_KEY','test-only-placeholder')
    output=offline('research',{'prompt':'Provider fixture'})
    output['source']='Mock HTTP fixture, not a real model response'
    def handler(request):
        body=json.loads(request.content)
        if source=='gemini':
            assert request.headers['x-goog-api-key']=='test-only-placeholder'
            assert body['generationConfig']['responseJsonSchema']['type']=='object'
            return httpx.Response(200,json={'candidates':[{'finishReason':'STOP','content':{'parts':[{'text':json.dumps(output)}]}}],'usageMetadata':{'promptTokenCount':10,'candidatesTokenCount':20}})
        assert body['stream'] is False and body['format']['type']=='object'
        return httpx.Response(200,json={'done':True,'message':{'content':json.dumps(output)},'prompt_eval_count':10,'eval_count':20})
    adapter=(GeminiProvider if source=='gemini' else OllamaProvider)(httpx.MockTransport(handler))
    monkeypatch.setattr('backend.execution_engine.provider',lambda name:adapter if name==source else real_provider(name))
    response=client.post('/agents',json={'id':'configured-'+source,'name':source,'provider':source,'model':'test-model','capabilities':['research']})
    assert response.status_code==201,response.text
    created=client.post('/tasks',json={'prompt':'Provider fixture','stages':[{'name':'Real adapter fixture','operation':'research','agent_id':'configured-'+source}]}).json()
    client.post(f'/tasks/{created["id"]}/start')
    run=wait(client,created['id'])
    assert run['status']=='COMPLETED' and run['output']==output
    assert run['attempts'][0]['usage'] and run['api_cost'] is None


def test_provider_connection_results_are_not_faked(client,monkeypatch):
    monkeypatch.delenv('OPENAI_API_KEY',raising=False)
    monkeypatch.delenv('GEMINI_API_KEY',raising=False)
    assert client.post('/providers/test',json={'provider':'offline','model':'deterministic-v1'}).json()['connected']
    for source in ['openai','gemini']:
        response=client.post('/providers/test',json={'provider':source,'model':'test-model'})
        assert response.status_code==422
        assert 'requires' in response.json()['detail']
    assert {p['provider'] for p in client.get('/providers').json()}=={'offline','openai','gemini','anthropic','ollama'}


def test_model_connection_test_validates_output(client,monkeypatch):
    from backend.providers import ProviderResult
    class MockProvider:
        async def execute(self,*args):
            return ProviderResult({'unexpected':'value'})
    monkeypatch.setattr('backend.providers.provider',lambda name:MockProvider())
    response=client.post('/providers/test',json={'provider':'gemini','model':'test-model'})
    assert response.status_code==422
