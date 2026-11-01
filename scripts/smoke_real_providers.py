"""Opt-in real generation smoke test. Never prints credentials or task content."""
import asyncio
import json
import os
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from backend.providers import provider, key_for, ProviderFailure

async def main():
    results=[]
    for name in ['openai','gemini','anthropic']:
        model=os.getenv(name.upper()+'_MODEL','')
        if not key_for(name) or not model:
            results.append({'provider':name,'status':'SKIPPED','reason':'Backend API credentials and an explicit *_MODEL are required'})
            continue
        try:
            result=await provider(name).generate({'model':model,'max_output_tokens':256,'timeout_seconds':20},'Reply briefly.','Explain quantum computing to a beginner in two sentences.')
            if not isinstance(result.output,str) or not result.output.strip(): raise ValueError('Empty response')
            results.append({'provider':name,'status':'PASSED','metadata':result.metadata,'usage':result.usage,'characters':len(result.output)})
        except ProviderFailure as exc:
            results.append({'provider':name,'status':'FAILED','category':exc.category,'error':str(exc)})
    print(json.dumps(results,indent=2))
    return 1 if any(r['status']=='FAILED' for r in results) else 0

if __name__=='__main__': raise SystemExit(asyncio.run(main()))
