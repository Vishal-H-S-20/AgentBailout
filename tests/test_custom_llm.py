"""Custom workflows and secure provider configuration; network is always mocked."""
import asyncio
import json
import os
import httpx
import pytest
from backend.providers import GroqProvider,ProviderResult,ProviderFailure
from tests.test_simple_navigation_backend import client,wait


def register(client,monkeypatch,source='openai'):
    monkeypatch.setenv({'openai':'OPENAI_API_KEY','groq':'GROQ_API_KEY','gemini':'GEMINI_API_KEY'}[source],'mock-key')
    response=client.post('/agents',json={'id':'test-'+source,'name':source,'provider':source,'model':'model-'+source,'capabilities':['custom'],'system_instructions':'Original system policy'})
    assert response.status_code==201,response.text
    return response.json()


def definition(i,source='openai',**extra):
    return {'id':f'stage-{i}','name':f'Custom purpose {i}','operation':'custom','agent_id':'test-'+source,
            'objective':f'Objective {i}','system_instructions':f'System {i}',**extra}


@pytest.mark.parametrize('count',[1,2,3,5,10])
def test_dynamic_stage_counts_full_context_and_output(client,monkeypatch,count):
    register(client,monkeypatch)
    calls=[]
    long='Full model response '*5000
    class Model:
        async def generate(self,config,instructions,prompt,schema=None):
            data=json.loads(prompt); calls.append((config,instructions,data))
            if len(calls)>1: assert data['prior_outputs'][0]['output']['content']==long
            assert data['original_task']=='Write a complete custom report'
            return ProviderResult(long,usage={'input_tokens':5,'output_tokens':20},metadata={'provider':'openai','model':config['model'],'request_id':str(len(calls))})
    monkeypatch.setattr('backend.execution_engine.provider',lambda name:Model())
    stages=[definition(i,max_context_characters=500000) for i in range(count)]
    task=client.post('/tasks',json={'prompt':'Write a complete custom report','stages':stages,'recovery_pool':[]}).json()
    client.post('/tasks/'+task['id']+'/start')
    run=wait(client,task['id'])
    assert run['status']=='COMPLETED' and len(calls)==count and len(run['stages'])==count
    assert run['output']['content']==long
    assert run['ledger']['balanced'] and run['ledger']['settled'] and run['api_cost'] is None
    assert all(f'System {i}' in calls[i][1] and f'Objective {i}' in calls[i][1] for i in range(count))
    assert run['attempts'][-1]['provider_metadata']['request_id']==str(count)


@pytest.mark.parametrize('protection,stage_recovery',[(False,True),(True,False),(True,True)])
def test_groq_cross_provider_recovery_reuses_context_and_instructions(client,monkeypatch,protection,stage_recovery):
    register(client,monkeypatch); register(client,monkeypatch,'groq')
    calls=[]
    class Model:
        async def generate(self,config,instructions,prompt,schema=None):
            calls.append((config['provider'],instructions,json.loads(prompt)))
            return ProviderResult(config['provider']+' actual mock output')
    monkeypatch.setattr('backend.execution_engine.provider',lambda name:Model())
    stages=[definition(0),definition(1,recovery_enabled=stage_recovery,backup_agents=[{'agent_id':'test-groq'}]),definition(2)]
    task=client.post('/tasks',json={'prompt':'Design a small library application','stages':stages,'recovery_pool':[],
                                 'agentbailout_enabled':protection,'failure':{'scenario':'crash','stage_index':1}}).json()
    client.post('/tasks/'+task['id']+'/start'); run=wait(client,task['id'])
    recovered=protection and stage_recovery
    assert run['status']==('COMPLETED' if recovered else 'FAILED')
    assert len(calls)==(3 if recovered else 1)
    assert run['stages'][0]['output']['content']=='openai actual mock output'
    if recovered:
        assert calls[1][0]=='groq' and 'System 1' in calls[1][1] and 'Objective 1' in calls[1][1]
        assert calls[1][2]['prior_outputs'][0]['output']['content']=='openai actual mock output'
        attempts=run['stages'][1]['attempts']
        assert attempts[0]['input']==attempts[1]['input'] and attempts[0]['output'] is None
        assert calls[2][2]['prior_outputs'][0]['output']['content']=='groq actual mock output'
    else: assert run['stages'][2]['status']=='SKIPPED'
    assert run['ledger']['balanced'] and run['ledger']['settled']


def test_selected_context_and_model_switch_are_real_inputs(client,monkeypatch):
    register(client,monkeypatch); register(client,monkeypatch,'groq')
    calls=[]
    class Model:
        async def generate(self,config,instructions,prompt,schema=None):
            calls.append((config['provider'],config['model'],json.loads(prompt)))
            return ProviderResult('output-'+str(len(calls)))
    monkeypatch.setattr('backend.execution_engine.provider',lambda name:Model())
    stages=[definition(0),definition(1,'groq'),definition(2,context_policy='selected',selected_prior_ids=['stage-0'])]
    task=client.post('/tasks',json={'prompt':'Translate and improve this document','stages':stages}).json()
    client.post('/tasks/'+task['id']+'/start'); run=wait(client,task['id'])
    assert run['status']=='COMPLETED'
    assert calls[1][:2]==('groq','model-groq')
    assert calls[2][2]['prior_outputs']==[{'stage_id':'stage-0','name':'Custom purpose 0','output':{'content':'output-1'}}]
    assert 'original_task' not in calls[2][2]


def test_json_validation_retains_bad_output_and_recovers(client,monkeypatch):
    register(client,monkeypatch); register(client,monkeypatch,'groq')
    class Model:
        async def generate(self,config,*args,**kwargs): return ProviderResult('bad JSON' if config['provider']=='openai' else '{"answer":42}')
    monkeypatch.setattr('backend.execution_engine.provider',lambda name:Model())
    schema={'type':'object','properties':{'answer':{'type':'integer'}},'required':['answer'],'additionalProperties':False}
    task=client.post('/tasks',json={'prompt':'Calculate an answer','stages':[definition(0,output_format='json',output_schema=schema,backup_agents=[{'agent_id':'test-groq'}])],'recovery_pool':[]}).json()
    client.post('/tasks/'+task['id']+'/start'); run=wait(client,task['id'])
    assert run['status']=='COMPLETED' and run['output']=={'content':{'answer':42}}
    assert run['attempts'][0]['output']=='bad JSON' and run['attempts'][0]['error_category']=='INVALID_OUTPUT'


def test_context_limit_refuses_without_silent_truncation(client,monkeypatch):
    register(client,monkeypatch)
    class Model:
        async def generate(self,*args,**kwargs): return ProviderResult('X'*2000)
    monkeypatch.setattr('backend.execution_engine.provider',lambda name:Model())
    task=client.post('/tasks',json={'prompt':'Explain this clearly','stages':[definition(0),definition(1,max_context_characters=1000)]}).json()
    client.post('/tasks/'+task['id']+'/start'); run=wait(client,task['id'])
    assert run['status']=='FAILED' and 'CONTEXT_LIMIT' in run['error']
    assert len(run['attempts'])==1 and run['stages'][0]['output']['content']=='X'*2000


def test_env_loading_precedence_alias_and_secret_privacy(tmp_path,monkeypatch):
    from backend.environment import load_environment,credential,ollama_url
    for name in ['GROQ_API_KEY','GEMINI_API_KEY','GOOGLE_API_KEY','OLLAMA_BASE_URL']: monkeypatch.delenv(name,raising=False)
    monkeypatch.setenv('OPENAI_API_KEY','process-key')
    env=tmp_path/'test.env'; env.write_text('OPENAI_API_KEY=file-key\nGROQ_API_KEY="file-groq"\nGEMINI_API_KEY=preferred-gemini\nGOOGLE_API_KEY=alias-key\nOLLAMA_BASE_URL=http://localhost:11434/\n')
    # Track variables for teardown before dotenv populates them.
    for name in ['GROQ_API_KEY','GEMINI_API_KEY','GOOGLE_API_KEY','OLLAMA_BASE_URL']: monkeypatch.setenv(name,''); monkeypatch.delenv(name)
    load_environment(env)
    assert credential('openai')=='process-key' and credential('groq')=='file-groq'
    assert credential('gemini')=='preferred-gemini' and ollama_url()=='http://localhost:11434'
    monkeypatch.setenv('GROQ_API_KEY','<your API key>'); assert credential('groq') is None


def test_registered_agent_health_uses_verified_model(client,monkeypatch):
    register(client,monkeypatch,'groq')
    class Model:
        async def generate(self,*args): return ProviderResult('OK')
        def get_health(self,*args): return {'status':'configured_unverified','verified_connection':False}
    monkeypatch.setattr('backend.providers.provider',lambda name:Model())
    assert client.post('/providers/test',json={'provider':'groq','model':'model-groq'}).status_code==200
    agent=next(a for a in client.get('/agents').json() if a['id']=='test-groq')
    assert agent['provider_health']['status']=='verified_connected'
    monkeypatch.setenv('GROQ_API_KEY','changed-key')
    agent=next(a for a in client.get('/agents').json() if a['id']=='test-groq')
    assert not agent['provider_health']['verified_connection']


@pytest.mark.parametrize('status,category',[(401,'AUTHENTICATION_ERROR'),(404,'MODEL_UNAVAILABLE'),(429,'RATE_LIMIT'),(503,'MODEL_FAILURE')])
def test_groq_sdk_errors_do_not_leak(monkeypatch,status,category):
    monkeypatch.setenv('GROQ_API_KEY','mock-key')
    calls=[]
    def handler(request): calls.append(request); return httpx.Response(status,json={'error':{'message':'private mock-key','type':'api_error'}})
    with pytest.raises(ProviderFailure) as exc:
        asyncio.run(GroqProvider(httpx.MockTransport(handler)).generate({'model':'chosen'},'System','Prompt'))
    assert exc.value.category==category and 'mock-key' not in str(exc.value) and len(calls)==1


def test_groq_sdk_payload_model_discovery_and_usage(monkeypatch):
    monkeypatch.setenv('GROQ_API_KEY','mock-key')
    def handler(request):
        if request.method=='GET': return httpx.Response(200,json={'object':'list','data':[{'id':'chosen','object':'model','owned_by':'fixture','created':1}]})
        body=json.loads(request.content)
        assert request.url.path=='/openai/v1/chat/completions'
        assert body['model']=='chosen' and body['max_completion_tokens']==2000
        assert body['messages']==[{'role':'system','content':'Custom instruction'},{'role':'user','content':'Custom prompt'}]
        return httpx.Response(200,json={'id':'req-fixture','model':'chosen','object':'chat.completion','created':1,
            'choices':[{'index':0,'finish_reason':'stop','message':{'role':'assistant','content':'Full custom response'}}],
            'usage':{'prompt_tokens':10,'completion_tokens':20,'total_tokens':30}})
    model=GroqProvider(httpx.MockTransport(handler))
    result=asyncio.run(model.generate({'model':'chosen'},'Custom instruction','Custom prompt'))
    assert result.output=='Full custom response' and result.metadata['model']=='chosen' and result.api_cost is None
    assert result.usage['input_tokens']==10
    assert asyncio.run(model.list_models())==['chosen']


@pytest.mark.parametrize('provider_name',['openai','gemini','groq'])
def test_partial_provider_output_and_usage_are_persisted(client,monkeypatch,provider_name):
    from backend.providers import provider as real_provider,OpenAIProvider,GeminiProvider
    register(client,monkeypatch,provider_name)
    def handler(request):
        if provider_name=='openai':
            payload={'id':'partial','model':'chosen','status':'incomplete','output':[{'type':'message','content':[{'type':'output_text','text':'Partial content'}]}],'usage':{'input_tokens':10,'output_tokens':20}}
        elif provider_name=='gemini':
            payload={'responseId':'partial','modelVersion':'chosen','candidates':[{'finishReason':'MAX_TOKENS','content':{'parts':[{'text':'Partial content'}]}}],'usageMetadata':{'promptTokenCount':10,'candidatesTokenCount':20}}
        else:
            payload={'id':'partial','model':'chosen','object':'chat.completion','created':1,'choices':[{'index':0,'finish_reason':'length','message':{'role':'assistant','content':'Partial content'}}],'usage':{'prompt_tokens':10,'completion_tokens':20,'total_tokens':30}}
        return httpx.Response(200,json=payload)
    adapter={'openai':OpenAIProvider,'gemini':GeminiProvider,'groq':GroqProvider}[provider_name](httpx.MockTransport(handler))
    monkeypatch.setattr('backend.execution_engine.provider',lambda name:adapter if name==provider_name else real_provider(name))
    task=client.post('/tasks',json={'prompt':'Write a full report','stages':[definition(0,provider_name)],'recovery_pool':[],'agentbailout_enabled':False}).json()
    client.post('/tasks/'+task['id']+'/start'); run=wait(client,task['id'])
    assert run['status']=='FAILED' and run['output'] is None
    assert run['attempts'][0]['output']=='Partial content' and run['attempts'][0]['usage']['input_tokens']==10
    assert run['attempts'][0]['provider_metadata']['status']!='completed'


def test_same_model_retry_uses_original_context(client,monkeypatch):
    register(client,monkeypatch)
    calls=[]
    class Model:
        async def generate(self,config,instructions,prompt,schema=None):
            calls.append((instructions,prompt))
            if len(calls)==1: raise ProviderFailure('TIMEOUT','Mock provider timed out')
            return ProviderResult('Recovered actual mock text')
    monkeypatch.setattr('backend.execution_engine.provider',lambda name:Model())
    task=client.post('/tasks',json={'prompt':'Write a translation','stages':[definition(0,retry_same_model=True)],'recovery_pool':[]}).json()
    client.post('/tasks/'+task['id']+'/start'); run=wait(client,task['id'])
    assert run['status']=='COMPLETED' and calls[0]==calls[1]
    assert run['attempts'][0]['agent_id']==run['attempts'][1]['agent_id']


def test_custom_comparison_freezes_same_pipeline_and_fault(client,monkeypatch):
    register(client,monkeypatch); register(client,monkeypatch,'groq')
    class Model:
        async def generate(self,*args,**kwargs): return ProviderResult('Actual mocked provider output')
    monkeypatch.setattr('backend.execution_engine.provider',lambda name:Model())
    result=client.post('/comparisons',json={'prompt':'Design a small library application',
        'stages':[definition(0),definition(1,backup_agents=[{'agent_id':'test-groq'}]),definition(2)],
        'failure':{'scenario':'crash','stage_index':1},'recovery_pool':[]})
    assert result.status_code==202,result.text
    pair=result.json()
    baseline=wait(client,pair['baseline_id']); protected=wait(client,pair['protected_id'])
    assert baseline['status']=='FAILED' and protected['status']=='COMPLETED'
    assert baseline['configuration']['stages']==protected['configuration']['stages']
    assert baseline['configuration']['failure']==protected['configuration']['failure']
    assert protected['stages'][1]['attempts'][1]['input']==protected['stages'][1]['attempts'][0]['input']
    assert baseline['ledger']['balanced'] and protected['ledger']['balanced']

def test_connection_probe_does_not_require_structured_output(client,monkeypatch):
    from backend.providers import OpenAIProvider
    monkeypatch.setenv('OPENAI_API_KEY','mock-key')
    def handler(request):
        body=json.loads(request.content)
        assert 'text' not in body and body['model']=='text-only-model'
        return httpx.Response(200,json={'id':'probe','model':'text-only-model','status':'completed','output':[{'type':'message','content':[{'type':'output_text','text':'OK'}]}]})
    adapter=OpenAIProvider(httpx.MockTransport(handler))
    monkeypatch.setattr('backend.providers.provider',lambda name:adapter)
    response=client.post('/providers/test',json={'provider':'openai','model':'text-only-model'})
    assert response.status_code==200 and response.json()['connected']


def test_groq_timeout_and_missing_key_are_honest(monkeypatch):
    monkeypatch.delenv('GROQ_API_KEY',raising=False)
    with pytest.raises(ProviderFailure) as exc:
        asyncio.run(GroqProvider().generate({'model':'chosen'},'System','Prompt'))
    assert exc.value.category=='CONFIGURATION_ERROR'
    monkeypatch.setenv('GROQ_API_KEY','mock-key')
    def handler(request): raise httpx.ReadTimeout('private mock-key',request=request)
    with pytest.raises(ProviderFailure) as exc:
        asyncio.run(GroqProvider(httpx.MockTransport(handler)).generate({'model':'chosen'},'System','Prompt'))
    assert exc.value.category=='TIMEOUT' and 'mock-key' not in str(exc.value)


def test_configured_keys_are_rejected_without_echo_or_persistence(client,monkeypatch):
    monkeypatch.setenv('GROQ_API_KEY','private-credential-fixture')
    before=len(client.get('/tasks').json())
    response=client.post('/tasks',json={'prompt':'Please use private-credential-fixture'})
    assert response.status_code==422 and 'private-credential-fixture' not in response.text
    assert len(client.get('/tasks').json())==before
    response=client.post('/agents',json={'id':'unsafe','name':'unsafe','provider':'groq','model':'chosen','capabilities':['custom'],'system_instructions':'Use private-credential-fixture'})
    assert response.status_code==422 and 'private-credential-fixture' not in response.text


def test_model_field_cannot_save_or_echo_a_credential(client,monkeypatch):
    monkeypatch.setenv('GROQ_API_KEY','configured-private-fixture')
    for key in ['configured-private-fixture','gsk_'+('A'*30)]:
        response=client.post('/providers/test',json={'provider':'groq','model':key})
        assert response.status_code==422 and key not in response.text
        assert key not in json.dumps(client.get('/providers').json())
