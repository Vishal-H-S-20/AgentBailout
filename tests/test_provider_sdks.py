"""Official SDK calls use mock HTTP, never credentials or network."""
import asyncio
import json
import httpx
import pytest
from backend.providers import OpenAIProvider, GeminiProvider, AnthropicProvider, ProviderFailure
from tests.test_simple_navigation_backend import client


def adapter(name,handler):
    return {'openai':OpenAIProvider,'gemini':GeminiProvider,'anthropic':AnthropicProvider}[name](httpx.MockTransport(handler))


@pytest.mark.parametrize('name',['openai','gemini','anthropic'])
def test_sdk_text_and_full_metadata(monkeypatch,name):
    monkeypatch.setenv({'openai':'OPENAI_API_KEY','gemini':'GEMINI_API_KEY','anthropic':'ANTHROPIC_API_KEY'}[name],'fixture-secret')
    text='A genuine mocked provider response. '*2000
    def handler(request):
        body=json.loads(request.content)
        assert body['model']=='account-model' if name!='gemini' else 'account-model' in str(request.url)
        assert 'Explain quantum computing' in request.content.decode()
        assert 'tools' not in body
        if name=='openai':
            assert body['max_output_tokens']==4096 and body['instructions']=='Teach clearly'
            assert 'text' not in body and body['store'] is False
            payload={'id':'resp_fixture','model':'actual-model','status':'completed','output':[{'type':'message','content':[{'type':'output_text','text':text}]}],'usage':{'input_tokens':10,'output_tokens':20,'total_tokens':30}}
        elif name=='gemini':
            assert body['generationConfig']['maxOutputTokens']==4096
            assert body['systemInstruction']['parts'][0]['text']=='Teach clearly'
            payload={'responseId':'gem_fixture','modelVersion':'actual-model','candidates':[{'finishReason':'STOP','content':{'parts':[{'text':text}]}}],'usageMetadata':{'promptTokenCount':10,'candidatesTokenCount':20,'totalTokenCount':30}}
        else:
            assert body['max_tokens']==4096 and body['system']=='Teach clearly'
            payload={'id':'msg_fixture','model':'actual-model','type':'message','role':'assistant','content':[{'type':'text','text':text}],'stop_reason':'end_turn','usage':{'input_tokens':10,'output_tokens':20}}
        return httpx.Response(200,json=payload,headers={'request-id':'request_fixture','x-request-id':'request_fixture'})
    result=asyncio.run(adapter(name,handler).generate({'model':'account-model','max_output_tokens':4096},'Teach clearly','Explain quantum computing'))
    assert result.output==text and result.api_cost is None
    assert result.usage['input_tokens']==10 and result.usage['output_tokens']==20
    assert result.metadata['provider']==name and result.metadata['model']=='actual-model'
    assert result.metadata['request_id'] and result.metadata['latency_seconds']>=0
    assert result.metadata['cost_status']=='unknown'


@pytest.mark.parametrize('name',['openai','gemini','anthropic'])
@pytest.mark.parametrize('status,category',[(429,'RATE_LIMIT'),(401,'AUTHENTICATION_ERROR'),(404,'MODEL_UNAVAILABLE'),(503,'MODEL_FAILURE')])
def test_sdk_errors_redacted_and_no_retry(monkeypatch,name,status,category):
    monkeypatch.setenv({'openai':'OPENAI_API_KEY','gemini':'GEMINI_API_KEY','anthropic':'ANTHROPIC_API_KEY'}[name],'fixture-secret')
    requests=[]
    def handler(request):
        requests.append(request)
        return httpx.Response(status,json={'error':{'message':'fixture-secret private prompt','code':status,'type':'api_error'}})
    with pytest.raises(ProviderFailure) as error:
        asyncio.run(adapter(name,handler).generate({'model':'account-model'},'System','Prompt'))
    assert error.value.category==category and 'fixture-secret' not in str(error.value)
    assert len(requests)==1


@pytest.mark.parametrize('name',['openai','gemini','anthropic'])
def test_sdk_model_discovery(monkeypatch,name):
    monkeypatch.setenv({'openai':'OPENAI_API_KEY','gemini':'GEMINI_API_KEY','anthropic':'ANTHROPIC_API_KEY'}[name],'fixture-secret')
    def handler(request):
        assert request.method=='GET'
        payload={'models':[{'name':'models/available-model','supportedGenerationMethods':['generateContent']}]} if name=='gemini' else {'data':[{'id':'available-model','object':'model','type':'model','display_name':'Available','created_at':'2026-01-01T00:00:00Z'}],'has_more':False}
        return httpx.Response(200,json=payload)
    assert asyncio.run(adapter(name,handler).list_models())==['available-model']


def test_connection_status_survives_request_but_invalidates_changed_key(client,monkeypatch):
    from backend.providers import ProviderResult
    monkeypatch.setenv('ANTHROPIC_API_KEY','fixture-one')
    class Connection:
        async def execute(self,*args): return ProviderResult({'ok':True},metadata={'provider':'anthropic','model':'verified-model'})
    monkeypatch.setattr('backend.providers.provider',lambda name:Connection())
    response=client.post('/providers/test',json={'provider':'anthropic','model':'verified-model'})
    assert response.status_code==200 and response.json()['checked_at']
    # Restore the factory: readiness comes from persisted successful generation, not a frontend session.
    from backend.providers import SDKProvider
    Connection.get_health=lambda self,config:{'status':'configured_unverified','verified_connection':False}
    rows=client.get('/providers').json()
    row=next(p for p in rows if p['provider']=='anthropic')
    assert row['status']=='verified_connected' and row['last_success_at']
    monkeypatch.setenv('ANTHROPIC_API_KEY','fixture-two')
    row=next(p for p in client.get('/providers').json() if p['provider']=='anthropic')
    assert not row['verified_connection'] and row['last_success_at'] is None
    assert 'fixture-' not in json.dumps(rows)

@pytest.mark.parametrize('name',['openai','gemini','anthropic'])
def test_sdk_timeout_is_classified(monkeypatch,name):
    monkeypatch.setenv({'openai':'OPENAI_API_KEY','gemini':'GEMINI_API_KEY','anthropic':'ANTHROPIC_API_KEY'}[name],'fixture-secret')
    def handler(request): raise httpx.ReadTimeout('fixture-secret',request=request)
    with pytest.raises(ProviderFailure) as error:
        asyncio.run(adapter(name,handler).generate({'model':'account-model'},'System','Prompt'))
    assert error.value.category=='TIMEOUT' and 'fixture-secret' not in str(error.value)


def test_real_failure_never_uses_offline_recovery(client,monkeypatch):
    from tests.test_simple_navigation_backend import wait
    monkeypatch.setenv('ANTHROPIC_API_KEY','temporary-configured-key')
    assert client.post('/agents',json={'id':'claude-missing','name':'Claude unavailable','provider':'anthropic','model':'account-model','capabilities':['research']}).status_code==201
    task=client.post('/tasks',json={'prompt':'Explain quantum computing','stages':[{'name':'Explain','operation':'research','agent_id':'claude-missing'}]}).json()
    monkeypatch.delenv('ANTHROPIC_API_KEY')
    client.post('/tasks/'+task['id']+'/start')
    report=wait(client,task['id'])
    assert report['status']=='FAILED' and report['output'] is None
    assert len(report['attempts'])==1 and report['attempts'][0]['error_category']=='CONFIGURATION_ERROR'
    assert any('Real LLM stages cannot recover using offline simulation' in e['message'] for e in report['events'])


def test_claude_sdk_engine_persists_receipt_and_usage(client,monkeypatch):
    from tests.test_simple_navigation_backend import wait
    from backend.contracts import offline
    from backend.providers import provider as real_provider
    monkeypatch.setenv('ANTHROPIC_API_KEY','fixture-secret')
    output=offline('research',{'prompt':'fixture'})
    output['source']='Mock SDK fixture'
    def handler(request):
        assert 'Return ONLY JSON matching this schema' in json.loads(request.content)['system']
        return httpx.Response(200,json={'id':'msg_fixture','model':'actual-model','type':'message','role':'assistant','content':[{'type':'text','text':json.dumps(output)}],'stop_reason':'end_turn','usage':{'input_tokens':10,'output_tokens':20}})
    monkeypatch.setattr('backend.execution_engine.provider',lambda name:AnthropicProvider(httpx.MockTransport(handler)) if name=='anthropic' else real_provider(name))
    assert client.post('/agents',json={'id':'claude-fixture','name':'Claude fixture','provider':'anthropic','model':'account-model','capabilities':['research']}).status_code==201
    task=client.post('/tasks',json={'prompt':'Explain quantum computing','stages':[{'name':'Explain','operation':'research','agent_id':'claude-fixture'}]}).json()
    client.post('/tasks/'+task['id']+'/start')
    report=wait(client,task['id'])
    assert report['status']=='COMPLETED' and report['output']==output
    attempt=report['attempts'][0]
    assert attempt['usage']['input_tokens']==10 and report['api_cost'] is None
    assert attempt['provider_metadata']['model']=='actual-model'
    assert attempt['provider_metadata']['provider']=='anthropic'
