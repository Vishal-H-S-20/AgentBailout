"""Provider boundary: no silent fallback, secrets, tool execution or invented API costs."""
import json
import os
from dataclasses import dataclass
from typing import Protocol
import httpx
from backend.contracts import offline


class ProviderFailure(Exception):
    def __init__(self, category: str, message: str):
        super().__init__(message)
        self.category = category


@dataclass
class ProviderResult:
    output: dict
    usage: dict | None = None
    api_cost: str | None = None


class AgentProvider(Protocol):
    async def execute(self, config: dict, operation: str, data: dict, schema: dict) -> ProviderResult: ...
    def validate_configuration(self, config: dict) -> None: ...
    def estimate_cost(self, config: dict) -> dict: ...
    def get_health(self, config: dict) -> dict: ...


class OfflineProvider:
    def validate_configuration(self, config: dict) -> None:
        pass

    def estimate_cost(self, config: dict) -> dict:
        return {'simulated_cost':config['estimated_cost'], 'api_cost':None}

    def get_health(self, config: dict) -> dict:
        return {'status':'available', 'execution_mode':'offline_simulation', 'verified_connection':True}

    async def execute(self, config: dict, operation: str, data: dict, schema: dict) -> ProviderResult:
        return ProviderResult(offline(operation,data), usage=None, api_cost='0.00')


class OpenAIProvider(OfflineProvider):
    def __init__(self, transport=None):
        self.transport = transport

    def validate_configuration(self, config: dict) -> None:
        if not os.getenv('OPENAI_API_KEY') or not config.get('model'):
            raise ProviderFailure('CONFIGURATION_ERROR','OpenAI requires OPENAI_API_KEY and a model identifier')

    def get_health(self, config: dict) -> dict:
        ready = bool(os.getenv('OPENAI_API_KEY') and config.get('model'))
        return {'status':'configured_unverified' if ready else 'unavailable',
                'execution_mode':'external_llm','verified_connection':False}

    async def execute(self, config: dict, operation: str, data: dict, schema: dict) -> ProviderResult:
        self.validate_configuration(config)
        try:
            async with httpx.AsyncClient(transport=self.transport, timeout=60, trust_env=False) as client:
                response = await client.post('https://api.openai.com/v1/responses',
                    headers={'Authorization':'Bearer '+os.environ['OPENAI_API_KEY']},
                    json={'model':config['model'], 'store':False,
                          'instructions':config['system_instructions']+'\nStage operation: '+operation,
                          'input':json.dumps(data), 'max_output_tokens':2000,
                          'text':{'format':{'type':'json_schema','name':'stage_output','strict':True,'schema':schema}}})
            if response.status_code >= 400:
                category = 'RATE_LIMIT' if response.status_code == 429 else 'MODEL_FAILURE'
                # Never persist provider bodies: they can echo secrets or user content.
                raise ProviderFailure(category, f'OpenAI request failed (HTTP {response.status_code})')
            payload = response.json()
            if not isinstance(payload,dict):
                raise ProviderFailure('INVALID_OUTPUT','Provider response must be an object')
            if payload.get('status') != 'completed':
                raise ProviderFailure('MODEL_FAILURE','OpenAI response was incomplete')
            texts = [c['text'] for item in payload.get('output',[]) if item.get('type')=='message'
                     for c in item.get('content',[]) if c.get('type')=='output_text']
            if not texts:
                raise ProviderFailure('INVALID_OUTPUT','No structured text response (possible refusal)')
            return ProviderResult(json.loads(''.join(texts)), usage=payload.get('usage'), api_cost=None)
        except httpx.TimeoutException:
            raise ProviderFailure('TIMEOUT','Provider request timed out') from None
        except httpx.HTTPError:
            raise ProviderFailure('MODEL_FAILURE','Provider connection failed') from None
        except (ValueError,KeyError,TypeError):
            raise ProviderFailure('INVALID_OUTPUT','Provider returned invalid structured data') from None


def provider(name: str) -> AgentProvider:
    if name == 'offline':
        return OfflineProvider()
    if name == 'openai':
        return OpenAIProvider()
    if name == 'gemini':
        return GeminiProvider()
    if name == 'ollama':
        return OllamaProvider()
    raise ProviderFailure('CONFIGURATION_ERROR','Unsupported provider')


class GeminiProvider(OpenAIProvider):
    def validate_configuration(self, config: dict) -> None:
        if not os.getenv('GEMINI_API_KEY') or not config.get('model'):
            raise ProviderFailure('CONFIGURATION_ERROR','Gemini requires GEMINI_API_KEY and a model identifier')

    def get_health(self, config: dict) -> dict:
        return {'status':'configured_unverified' if os.getenv('GEMINI_API_KEY') and config.get('model') else 'unavailable','execution_mode':'external_llm','verified_connection':False}

    async def execute(self, config: dict, operation: str, data: dict, schema: dict) -> ProviderResult:
        from urllib.parse import quote
        self.validate_configuration(config)
        return await self._request('https://generativelanguage.googleapis.com/v1beta/models/'+quote(config['model'],safe='')+':generateContent',
            {'x-goog-api-key':os.environ['GEMINI_API_KEY']},
            {'systemInstruction':{'parts':[{'text':config['system_instructions']+'\nStage: '+operation}]},
             'contents':[{'role':'user','parts':[{'text':json.dumps(data)}]}],
             'generationConfig':{'maxOutputTokens':2000,'responseFormat':{'text':{'mimeType':'application/json','schema':schema}}}},False)

    async def _request(self,url: str,headers: dict,payload: dict,local: bool) -> ProviderResult:
        try:
            async with httpx.AsyncClient(transport=self.transport,timeout=60,trust_env=False) as client:
                response=await client.post(url,headers=headers,json=payload)
            if response.status_code>=400:
                raise ProviderFailure('RATE_LIMIT' if response.status_code==429 else 'MODEL_FAILURE',f'Provider returned HTTP {response.status_code}')
            result=response.json()
            if local:
                if not result.get('done') or result.get('done_reason')=='length':
                    raise ProviderFailure('MODEL_FAILURE','Ollama response was incomplete')
                output=json.loads(result['message']['content'])
                usage={'input_tokens':result.get('prompt_eval_count'),'output_tokens':result.get('eval_count')}
            else:
                candidate=result['candidates'][0]
                if candidate.get('finishReason')!='STOP':
                    raise ProviderFailure('MODEL_FAILURE','Gemini response was incomplete or blocked')
                output=json.loads(''.join(p['text'] for p in candidate['content']['parts'] if 'text' in p))
                usage=result.get('usageMetadata')
            return ProviderResult(output,usage=usage,api_cost=None)
        except httpx.TimeoutException:
            raise ProviderFailure('TIMEOUT','Provider request timed out') from None
        except httpx.HTTPError:
            raise ProviderFailure('MODEL_FAILURE','Provider connection failed') from None
        except (ValueError,KeyError,TypeError,IndexError,AttributeError):
            raise ProviderFailure('INVALID_OUTPUT','Provider returned invalid structured data') from None


class OllamaProvider(GeminiProvider):
    def validate_configuration(self, config: dict) -> None:
        if not config.get('model'):
            raise ProviderFailure('CONFIGURATION_ERROR','Choose an installed Ollama model')

    def get_health(self,config: dict) -> dict:
        return {'status':'configured_unverified' if config.get('model') else 'unavailable','execution_mode':'local_llm','verified_connection':False}

    async def execute(self,config: dict,operation: str,data: dict,schema: dict) -> ProviderResult:
        self.validate_configuration(config)
        return await self._request(os.getenv('OLLAMA_URL','http://127.0.0.1:11434').rstrip('/')+'/api/chat',{},
            {'model':config['model'],'stream':False,'format':schema,'options':{'num_predict':2000},
             'messages':[{'role':'system','content':config['system_instructions']+'\nStage: '+operation},
                         {'role':'user','content':json.dumps(data)}]},True)
