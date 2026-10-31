"""Bounded diagnostics for code/workflow failures; never executes submitted repository code."""
import ast
import asyncio
import json
import re
import sys
from decimal import Decimal, InvalidOperation
from pydantic import BaseModel, Field
from typing import Literal
import httpx


class DiagnosticRequest(BaseModel):
    kind: Literal['python','repository'] = 'python'
    source: str = Field(default='def total(value):\nreturn value * 2\n',max_length=20000)
    repository_url: str = Field(default='',max_length=300)
    amount: str = Field(default='12.50',max_length=30)
    protection: bool = True


async def diagnose(body: DiagnosticRequest) -> dict:
    events=[]
    if body.kind=='python':
        # Only this developer-authored program executes. Submitted source is AST-inspected only.
        program='import json,sys\ndata=json.loads(sys.argv[1])\nprint(json.dumps({"total": data["amount"] + 1}))'
        async def run(value):
            child=await asyncio.create_subprocess_exec(sys.executable,'-I','-S','-c',program,json.dumps({'amount':value}),
                stdout=asyncio.subprocess.PIPE,stderr=asyncio.subprocess.PIPE)
            try:
                stdout,stderr=await asyncio.wait_for(child.communicate(),3)
            except (TimeoutError,asyncio.CancelledError):
                child.kill()
                await child.wait()
                raise
            return {'exit_code':child.returncode,'stdout':stdout.decode()[:4000],'stderr':stderr.decode()[:4000]}
        primary=await run(body.amount)
        events.append({'event':'PYTHON_EXECUTION_FAILED' if primary['exit_code'] else 'PYTHON_EXECUTION_COMPLETED','exit_code':primary['exit_code']})
        report={'kind':'python','primary':primary,'events':events,'status':'FAILED','recovery':None,
                'scope':'Real execution of a fixed local numeric program; user and repository code is never executed.'}
        if body.protection and primary['exit_code']:
            try:
                number=Decimal(body.amount)
                if not number.is_finite() or abs(number)>Decimal('1000000000'):
                    raise ValueError('Finite bounded numeric value required')
                # A known representation is normalized; no missing amount is invented.
                normalized=float(number)
            except (InvalidOperation,ValueError):
                events.append({'event':'REPAIR_REJECTED','reason':'Amount is not a valid bounded number; no value invented'})
                return report
            result=await run(normalized)
            valid=result['exit_code']==0 and Decimal(str(json.loads(result['stdout'])['total']))==number+1
            report.update(recovery=result,status='RECOVERED' if valid else 'FAILED')
            events.extend([{'event':'INPUT_NORMALIZED','from_type':'string','to_type':'number'},
                           {'event':'REPAIR_VALIDATED' if valid else 'REPAIR_FAILED','validation':'Output total checked against Decimal arithmetic'}])
        return report
    source=body.source
    origin='Submitted Python source (static analysis only)'
    if body.repository_url:
        match=re.fullmatch(r'https://github\.com/([A-Za-z0-9_.-]+)/([A-Za-z0-9_.-]+)(?:/blob/([A-Za-z0-9_.-]+)/([A-Za-z0-9_./-]+\.py))?/?',body.repository_url)
        if not match:
            raise ValueError('Use a public github.com owner/repository URL or a Python file blob URL')
        owner,repo,branch,path=match.groups()
        branch,path=branch or 'HEAD',path or 'main.py'
        if '..' in path.split('/'):
            raise ValueError('Invalid repository path')
        url=f'https://raw.githubusercontent.com/{owner}/{repo}/{branch}/{path}'
        async with httpx.AsyncClient(timeout=10,follow_redirects=False) as client:
            async with client.stream('GET',url) as response:
                if response.status_code!=200:
                    raise ValueError(f'GitHub source fetch returned HTTP {response.status_code}; choose a public Python file blob URL')
                raw=bytearray()
                async for chunk in response.aiter_bytes():
                    raw.extend(chunk)
                    if len(raw)>20000:
                        raise ValueError('Source file exceeds 20 KB inspection limit')
                source=raw.decode('utf-8')
        origin=body.repository_url
    try:
        ast.parse(source)
        return {'kind':'repository','status':'VALID','origin':origin,'events':[{'event':'AST_VALIDATED'}],
                'scope':'Python syntax only; dependencies, tests and runtime behavior were not verified.'}
    except SyntaxError as exc:
        return {'kind':'repository','status':'FAILED','origin':origin,
                'events':[{'event':'SYNTAX_FAILURE','line':exc.lineno,'message':exc.msg},
                          {'event':'REPAIR_REQUIRES_REVIEW','reason':'No automatic code edits: inspect the reported line and submit corrected source for revalidation.'}],
                'scope':'Read-only diagnosis of submitted/GitHub Python source; downloaded code is never executed.'}
