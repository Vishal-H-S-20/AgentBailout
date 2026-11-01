"""Official SDK provider boundary. No automatic retries, tools or offline fallback."""
import json
import os
from dataclasses import dataclass
from datetime import datetime, timezone
from time import monotonic
from typing import Protocol
import httpx
from backend.contracts import offline


class ProviderFailure(Exception):
    def __init__(self, category: str, message: str):
        super().__init__(message)
        self.category = category


@dataclass
class ProviderResult:
    output: dict | list | str
    usage: dict | None = None
    api_cost: str | None = None
    metadata: dict | None = None


class AgentProvider(Protocol):
    async def execute(self, config: dict, operation: str, data: dict, schema: dict) -> ProviderResult: ...
    def validate_configuration(self, config: dict) -> None: ...
    def estimate_cost(self, config: dict) -> dict: ...
    def get_health(self, config: dict) -> dict: ...


def key_for(name):
    return os.getenv('GOOGLE_API_KEY') or os.getenv('GEMINI_API_KEY') if name == 'gemini' else os.getenv({'openai':'OPENAI_API_KEY','anthropic':'ANTHROPIC_API_KEY'}.get(name,''))


def classified(exc):
    # SDK exception strings/bodies may echo credentials or task data: never forward them.
    code = getattr(exc,'status_code',None) or getattr(exc,'code',None)
    name = type(exc).__name__.lower()
    if isinstance(exc,(TimeoutError,httpx.TimeoutException)) or 'timeout' in name:
        return ProviderFailure('TIMEOUT','Provider request timed out')
    if code == 429:
        return ProviderFailure('RATE_LIMIT','Provider rate limit reached (HTTP 429)')
    if code in (401,403):
        return ProviderFailure('AUTHENTICATION_ERROR',f'Provider authorization failed (HTTP {code})')
    if code == 404:
        return ProviderFailure('MODEL_UNAVAILABLE','Requested provider model or endpoint was not found (HTTP 404)')
    return ProviderFailure('MODEL_FAILURE',f'Provider request failed'+(f' (HTTP {code})' if isinstance(code,int) else ''))


class OfflineProvider:
    def validate_configuration(self, config): pass
    def estimate_cost(self, config):
        return {'simulated_cost':config.get('estimated_cost'),'api_cost':None,'cost_status':'unknown'}
    def get_health(self, config):
        return {'status':'available','execution_mode':'offline_simulation','verified_connection':True}
    async def execute(self, config, operation, data, schema):
        return ProviderResult(offline(operation,data),api_cost='0.00')


class SDKProvider(OfflineProvider):
    name = ''
    def __init__(self, transport=None): self.transport=transport
    def validate_configuration(self, config):
        if not key_for(self.name) or not config.get('model'):
            variable={'openai':'OPENAI_API_KEY','gemini':'GEMINI_API_KEY or GOOGLE_API_KEY','anthropic':'ANTHROPIC_API_KEY'}[self.name]
            raise ProviderFailure('CONFIGURATION_ERROR',f'{self.name.title()} requires {variable} and a model identifier')
    def get_health(self, config):
        return {'status':'configured_unverified' if key_for(self.name) else 'unavailable',
                'configuration_status':'configured' if key_for(self.name) else 'not_configured',
                'execution_mode':'external_llm','verified_connection':False}
    def options(self, config):
        timeout=float(config.get('timeout_seconds',60))
        tokens=int(config.get('max_output_tokens',2000))
        if not 0 < timeout <= 300 or not 1 <= tokens <= 32768:
            raise ProviderFailure('CONFIGURATION_ERROR','Timeout or output token limit is outside supported safety bounds')
        # Temperature/tool settings are deliberately omitted until per-model capabilities are configured.
        return timeout,tokens
    async def execute(self, config, operation, data, schema):
        return await self.generate(config,config.get('system_instructions','')+'\nStage operation: '+operation,json.dumps(data,ensure_ascii=False),schema)
    async def generate(self, config, instructions, prompt, schema=None):
        self.validate_configuration(config)
        started=datetime.now(timezone.utc).isoformat(); clock=monotonic()
        try:
            content,usage,model,request_id,status=await self._generate(config,instructions,prompt,schema)
            if not content:
                raise ProviderFailure('INVALID_OUTPUT','No text response was returned (possible refusal)')
            try: output=json.loads(content) if schema else content
            except (ValueError,TypeError):
                raise ProviderFailure('INVALID_OUTPUT','Provider returned invalid structured data') from None
            return ProviderResult(output,usage=usage,metadata={'provider':self.name,'model':model,
                'status':status,'started_at':started,'ended_at':datetime.now(timezone.utc).isoformat(),
                'latency_seconds':monotonic()-clock,'request_id':request_id,'cost_status':'unknown'})
        except ProviderFailure: raise
        except Exception as exc: raise classified(exc) from None
    async def list_models(self):
        if not key_for(self.name):
            raise ProviderFailure('CONFIGURATION_ERROR',f'{self.name.title()} requires backend API credentials')
        try: return sorted(set(await self._models()))
        except ProviderFailure: raise
        except Exception as exc: raise classified(exc) from None


class OpenAIProvider(SDKProvider):
    name='openai'
    def client(self, timeout):
        from openai import AsyncOpenAI
        return AsyncOpenAI(api_key=key_for(self.name),base_url='https://api.openai.com/v1',timeout=timeout,max_retries=0,
                           http_client=httpx.AsyncClient(transport=self.transport,timeout=timeout,trust_env=False))
    async def _generate(self,config,instructions,prompt,schema):
        timeout,tokens=self.options(config)
        args={'model':config['model'],'store':False,'instructions':instructions,'input':prompt,'max_output_tokens':tokens}
        if schema: args['text']={'format':{'type':'json_schema','name':'stage_output','strict':True,'schema':schema}}
        async with self.client(timeout) as client:
            result=await client.responses.create(**args)
        if result.status!='completed': raise ProviderFailure('MODEL_FAILURE','OpenAI response was incomplete')
        usage=result.usage.model_dump(exclude_none=True) if result.usage else None
        return result.output_text,usage,result.model or config['model'],getattr(result,'_request_id',None) or result.id,result.status
    async def _models(self):
        async with self.client(15) as client:
            return [item.id async for item in client.models.list()]


class GeminiProvider(SDKProvider):
    name='gemini'
    def client(self, timeout):
        from google import genai
        from google.genai import types
        return genai.Client(api_key=key_for(self.name),http_options=types.HttpOptions(timeout=int(timeout*1000),
            retry_options=types.HttpRetryOptions(attempts=1),httpx_async_client=httpx.AsyncClient(transport=self.transport,timeout=timeout,trust_env=False))).aio
    async def _generate(self,config,instructions,prompt,schema):
        from google.genai import types
        timeout,tokens=self.options(config)
        settings={'system_instruction':instructions,'max_output_tokens':tokens,
                  'automatic_function_calling':{'disable':True}}
        if schema: settings.update(response_mime_type='application/json',response_json_schema=schema)
        async with self.client(timeout) as client:
            result=await client.models.generate_content(model=config['model'],contents=prompt,config=types.GenerateContentConfig(**settings))
        if not result.candidates or str(result.candidates[0].finish_reason).split('.')[-1]!='STOP':
            raise ProviderFailure('MODEL_FAILURE','Gemini response was incomplete or blocked')
        raw=result.usage_metadata
        usage=None if not raw else {'input_tokens':raw.prompt_token_count,'output_tokens':raw.candidates_token_count,
                                   'total_tokens':raw.total_token_count,'provider_usage':raw.model_dump(mode='json')}
        return result.text,usage,result.model_version or config['model'],result.response_id,'completed'
    async def _models(self):
        async with self.client(15) as client:
            return [item.name.removeprefix('models/') async for item in await client.models.list()
                    if 'generateContent' in (item.supported_actions or [])]


class AnthropicProvider(SDKProvider):
    name='anthropic'
    def client(self,timeout):
        from anthropic import AsyncAnthropic
        return AsyncAnthropic(api_key=key_for(self.name),base_url='https://api.anthropic.com',timeout=timeout,max_retries=0,
            http_client=httpx.AsyncClient(transport=self.transport,timeout=timeout,trust_env=False))
    async def _generate(self,config,instructions,prompt,schema):
        timeout,tokens=self.options(config)
        # Native structured output is model-dependent; use prompt + strict local schema validation in the existing engine.
        if schema: instructions+='\nReturn ONLY JSON matching this schema: '+json.dumps(schema)
        async with self.client(timeout) as client:
            result=await client.messages.create(model=config['model'],max_tokens=tokens,system=instructions,
                messages=[{'role':'user','content':prompt}])
        if result.stop_reason!='end_turn': raise ProviderFailure('MODEL_FAILURE','Claude response was incomplete or required unsupported tools')
        return ''.join(part.text for part in result.content if part.type=='text'),result.usage.model_dump(),result.model,getattr(result,'_request_id',None) or result.id,'completed'
    async def _models(self):
        async with self.client(15) as client:
            return [item.id async for item in client.models.list()]


class OllamaProvider(OfflineProvider):
    def __init__(self,transport=None): self.transport=transport
    def validate_configuration(self,config):
        if not config.get('model'): raise ProviderFailure('CONFIGURATION_ERROR','Choose an installed Ollama model')
    def get_health(self,config):
        return {'status':'configured_unverified','configuration_status':'configured','execution_mode':'local_llm','verified_connection':False}
    async def list_models(self):
        try:
            async with httpx.AsyncClient(transport=self.transport,timeout=15,trust_env=False) as client:
                response=await client.get(os.getenv('OLLAMA_URL','http://127.0.0.1:11434').rstrip('/')+'/api/tags')
                response.raise_for_status()
            return sorted(item['name'] for item in response.json()['models'])
        except Exception as exc: raise classified(exc) from None
    async def execute(self,config,operation,data,schema):
        self.validate_configuration(config)
        try:
            async with httpx.AsyncClient(transport=self.transport,timeout=60,trust_env=False) as client:
                response=await client.post(os.getenv('OLLAMA_URL','http://127.0.0.1:11434').rstrip('/')+'/api/chat',json={
                    'model':config['model'],'stream':False,'format':schema,'options':{'num_predict':2000},'messages':[
                    {'role':'system','content':config.get('system_instructions','')+'\nStage: '+operation},
                    {'role':'user','content':json.dumps(data)}]})
                response.raise_for_status()
            result=response.json()
            if not result.get('done') or result.get('done_reason')=='length': raise ProviderFailure('MODEL_FAILURE','Ollama response was incomplete')
            return ProviderResult(json.loads(result['message']['content']),usage={'input_tokens':result.get('prompt_eval_count'),'output_tokens':result.get('eval_count')})
        except ProviderFailure: raise
        except (ValueError,KeyError,TypeError): raise ProviderFailure('INVALID_OUTPUT','Provider returned invalid structured data') from None
        except Exception as exc: raise classified(exc) from None


def provider(name):
    choices={'offline':OfflineProvider,'openai':OpenAIProvider,'gemini':GeminiProvider,'anthropic':AnthropicProvider,'ollama':OllamaProvider}
    if name not in choices: raise ProviderFailure('CONFIGURATION_ERROR','Unsupported provider')
    return choices[name]()
