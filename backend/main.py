import asyncio
import httpx
from datetime import datetime
from decimal import Decimal
from pydantic import BaseModel
from typing import Literal
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from sqlalchemy.exc import IntegrityError
from sqlalchemy import select, text
from jsonschema import ValidationError
from backend.database import Base, engine, SessionLocal
from backend.models import Task, Stage, Event, Agent, Workflow, Execution, Comparison
from backend.schemas import SafeInputModel, TaskCreate, TaskView, EventView, FaultDefinition, AgentCreate, WorkflowCreate
from backend.supervisor import AGENTS, claim, execute, fail
from backend.ledger import fund, snapshot


class FailureRequest(FaultDefinition):
    pass


def create_app(db_engine=engine, factory=SessionLocal) -> FastAPI:
    jobs: set[asyncio.Task] = set()

    @asynccontextmanager
    async def lifespan(app):
        from backend.provider_startup import prepare_sdks
        await asyncio.to_thread(prepare_sdks)
        from backend.migrations import migrate
        from backend.registry import seed
        migrate(db_engine)
        with factory.begin() as db:
            seed(db)
        with factory() as db:
            interrupted = list(db.scalars(select(Task.id).where(Task.status.in_(['RUNNING', 'RESCUING', 'RESCUED']))))
        for task_id in interrupted:
            fail(factory, task_id, None, 'Interrupted execution detected on startup; create a new task')
        yield
        for job in list(jobs):
            job.cancel()
        await asyncio.gather(*jobs, return_exceptions=True)

    app = FastAPI(title='AgentBailout', version='0.5.0', lifespan=lifespan)

    @app.exception_handler(RequestValidationError)
    async def invalid_request(request, exc):
        # Never echo submitted credential-bearing values in validation responses.
        return JSONResponse(status_code=422,content={'detail':[{'loc':list(e['loc']),'msg':e['msg'],'type':e['type']} for e in exc.errors()]})

    @app.exception_handler(IntegrityError)
    async def conflict(request, exc):
        return JSONResponse(status_code=409,content={'detail':'Conflicting write; operation was rolled back'})

    def get_task(task_id: str) -> TaskView:
        with factory() as db:
            task = db.get(Task, task_id)
            if task is None:
                raise HTTPException(404, 'Task not found')
            return TaskView.model_validate(task)

    @app.get('/health')
    def health():
        with factory() as db:
            db.execute(select(1))
        return {'status': 'ok', 'phase': 4, 'version':'0.5.0'}

    @app.get('/contracts')
    def contract_catalog():
        from backend.contracts import catalog
        return catalog()

    @app.post('/tasks', response_model=TaskView, status_code=201)
    def create_task(body: TaskCreate):
        if not body.prompt.strip():
            raise HTTPException(422, 'Prompt must contain text')
        with factory.begin() as db:
            from backend.workflows import create_execution
            try:
                task = create_execution(db,body)
            except ValueError as exc:
                raise HTTPException(422,str(exc)) from None
            result = TaskView.model_validate(task)
        return result

    @app.get('/tasks', response_model=list[TaskView])
    def list_tasks():
        with factory() as db:
            return [TaskView.model_validate(t) for t in db.scalars(select(Task).order_by(Task.created_at.desc()).limit(100))]

    @app.get('/tasks/{task_id}', response_model=TaskView)
    def detail(task_id: str):
        return get_task(task_id)

    @app.post('/tasks/{task_id}/start', status_code=202)
    async def start(task_id: str):
        get_task(task_id)
        if not claim(factory, task_id):
            raise HTTPException(409, 'Only a CREATED task can be started')
        job = asyncio.create_task(execute(factory, task_id))
        jobs.add(job)
        job.add_done_callback(jobs.discard)
        return {'task_id': task_id, 'status': 'RUNNING'}

    @app.get('/tasks/{task_id}/events', response_model=list[EventView])
    def events(task_id: str):
        get_task(task_id)
        with factory() as db:
            return [EventView.model_validate(e) for e in db.scalars(select(Event).where(Event.task_id == task_id).order_by(Event.id))]

    @app.post('/tasks/{task_id}/inject-failure')
    def inject(task_id: str, body: FailureRequest):
        with factory.begin() as db:
            # Serialize eligibility checking with the supervisor's pending→running write.
            # An accepted injection commits before a stage can claim its input/fault snapshot.
            db.execute(text('BEGIN IMMEDIATE'))
            task = db.get(Task, task_id)
            if task is None:
                raise HTTPException(404, 'Task not found')
            execution = db.get(Execution,task_id)
            index = body.stage_index if body.stage_index is not None else min(1,len(task.stages)-1)
            if index >= len(task.stages):
                raise HTTPException(422,'Failure stage is outside the workflow')
            if task.status not in {'CREATED','RUNNING'}:
                raise HTTPException(409,{'code':'TASK_TERMINAL','message':'This task is already complete. Create a new task to inject a failure.','task_id':task_id})
            if db.scalar(select(Event.id).where(Event.task_id == task_id, Event.type == 'FAILURE_INJECTED')):
                raise HTTPException(409,{'code':'FAULT_ALREADY_CONFIGURED','message':'A failure is already configured for this task. It will occur automatically at the saved stage.','task_id':task_id})
            if task.stages[index].status != 'PENDING':
                raise HTTPException(409,{'code':'STAGE_STARTED','message':'This stage has already started. Choose a pending stage.','task_id':task_id,'stage_index':index})
            if body.scenario=='normal':
                raise HTTPException(422,{'code':'FAULT_REQUIRED','message':'Choose an active failure type for manual injection.'})
            if execution:
                config = dict(execution.configuration)
                config['failure'] = {'scenario':body.scenario,'stage_index':index}
                execution.configuration = config
                import json
                message = json.dumps(config['failure'])
            else:
                message = body.scenario
            db.add(Event(task_id=task_id, type='FAILURE_INJECTED', message=message))
        return {'task_id':task_id,'scenario': body.scenario,'stage_index':index,'message':'Failure saved. It will occur when the selected stage begins.'}

    @app.get('/tasks/{task_id}/ledger')
    def ledger(task_id: str):
        get_task(task_id)
        with factory() as db:
            return snapshot(db, task_id)

    @app.get('/metrics')
    def metrics():
        with factory() as db:
            tasks = list(db.scalars(select(Task)))
            events = list(db.scalars(select(Event)))
            failures = sum(e.type == 'FAILURE_DETECTED' for e in events)
            recovered = sum(t.status == 'COMPLETED' and any(s.recovery_attempts for s in t.stages) for t in tasks)
            durations = []
            for task in tasks:
                starts = [e.timestamp for e in events if e.task_id == task.id and e.type == 'FAILURE_DETECTED']
                ends = [e.timestamp for e in events if e.task_id == task.id and e.type == 'BACKUP_COMPLETED']
                if starts and ends:
                    durations.append((datetime.fromisoformat(ends[0])-datetime.fromisoformat(starts[0])).total_seconds())
            from backend.models import LedgerEntry
            expenses = list(db.scalars(select(LedgerEntry).where(LedgerEntry.account.in_(['backup_expense','recovery_overhead']))))
            return {'tasks_processed':sum(t.status in {'COMPLETED','FAILED'} for t in tasks),
                    'total_workflow_executions':len(tasks),
                    'failures_detected':failures,'successful_recoveries':recovered,
                    'recovery_success_rate':recovered/failures if failures else 0,
                    'average_recovery_seconds':sum(durations)/len(durations) if durations else 0,
                    'total_simulated_rescue_cost':str(Decimal(sum(e.credit_cents-e.debit_cents for e in expenses))/100)}

    @app.get('/agents')
    @app.get('/workers')
    def agents():
        from backend.registry import public_agent
        with factory() as db:
            return [public_agent(row) for row in db.scalars(select(Agent).order_by(Agent.id,Agent.version))]

    @app.post('/agents',status_code=201)
    def register_agent(body: AgentCreate):
        from backend.registry import configuration, public_agent
        with factory.begin() as db:
            versions = list(db.scalars(select(Agent.version).where(Agent.id==body.id)))
            config = configuration(body.name,list(body.capabilities))
            config.update(body.model_dump(mode='json',exclude={'id'}))
            config['health_status'] = 'available' if body.provider=='offline' else 'configured_unverified'
            row = Agent(id=body.id,version=max(versions,default=0)+1,configuration=config)
            db.add(row)
            db.flush()
            return public_agent(row)

    @app.get('/workflows')
    def workflows():
        with factory() as db:
            return [{'id':w.id,**w.definition,'created_at':w.created_at} for w in db.scalars(select(Workflow).order_by(Workflow.id))]

    @app.post('/workflows',status_code=201)
    def create_workflow(body: WorkflowCreate):
        from backend.workflows import resolve_stages
        with factory.begin() as db:
            try:
                resolve_stages(db,[s.model_dump() for s in body.stages],require_configuration=False)
                if body.recovery_pool is not None:
                    from backend.registry import agent_snapshot
                    for ref in body.recovery_pool:
                        agent_snapshot(db,ref.agent_id,ref.version)
            except ValueError as exc:
                raise HTTPException(422,str(exc)) from None
            row = Workflow(definition=body.model_dump())
            db.add(row)
            db.flush()
            return {'id':row.id,**row.definition}

    @app.get('/tasks/{task_id}/execution')
    def execution_detail(task_id: str):
        from backend.workflows import execution_report
        get_task(task_id)
        with factory() as db:
            return execution_report(db,task_id)

    @app.post('/comparisons',status_code=202)
    async def compare(body: TaskCreate):
        from backend.workflows import create_execution
        with factory.begin() as db:
            try:
                protected = create_execution(db,body.model_copy(update={'agentbailout_enabled':True}))
                db.flush()
                config = dict(db.get(Execution,protected.id).configuration)
                config['agentbailout_enabled'] = False
                baseline = create_execution(db,body,config)
            except ValueError as exc:
                raise HTTPException(422,str(exc)) from None
            pair = Comparison(baseline_id=baseline.id,protected_id=protected.id)
            db.add(pair)
            db.flush()
            result = {'id':pair.id,'baseline_id':baseline.id,'protected_id':protected.id}
        # Execute sequentially to reduce local contention; configurations and fault are identical.
        claim(factory,baseline.id)
        claim(factory,protected.id)
        async def paired():
            try:
                await execute(factory,baseline.id)
                await execute(factory,protected.id)
            except asyncio.CancelledError:
                with factory() as db:
                    pending = db.get(Task,protected.id).status in {'RUNNING','RESCUING','RESCUED'}
                if pending:
                    fail(factory,protected.id,None,'Comparison interrupted by server shutdown')
                raise
        job = asyncio.create_task(paired())
        jobs.add(job)
        job.add_done_callback(jobs.discard)
        return result

    @app.get('/comparisons')
    def comparisons():
        with factory() as db:
            return [{'id':p.id,'baseline_id':p.baseline_id,'protected_id':p.protected_id} for p in db.scalars(select(Comparison).order_by(Comparison.created_at.desc()).limit(100))]

    @app.get('/comparisons/{comparison_id}')
    def comparison_detail(comparison_id: str):
        from backend.workflows import execution_report
        with factory() as db:
            pair = db.get(Comparison,comparison_id)
            if not pair:
                raise HTTPException(404,'Comparison not found')
            baseline,protected = execution_report(db,pair.baseline_id),execution_report(db,pair.protected_id)
            delta = None if baseline['execution_seconds'] is None or protected['execution_seconds'] is None else protected['execution_seconds']-baseline['execution_seconds']
            allocations = []
            for run in [baseline,protected]:
                allocations.append(Decimal(run['configuration'].get('task_budget','5.00'))-Decimal(run['ledger']['balances'].get('client_refund','0')) if run['ledger']['settled'] else None)
            return {'id':pair.id,'baseline':baseline,'protected':protected,'time_difference_seconds':delta,
                    'simulated_allocation_difference':str(allocations[1]-allocations[0]) if all(a is not None for a in allocations) else None,
                    'api_cost_difference':str(Decimal(protected['api_cost'])-Decimal(baseline['api_cost'])) if baseline['api_cost'] is not None and protected['api_cost'] is not None else None,
                    'note':'Sequential controlled runs with frozen agent versions and identical fault; external LLM outputs can vary. Positive time difference means protection took longer.'}

    from backend.diagnostics import DiagnosticRequest, diagnose

    class ConnectionRequest(SafeInputModel):
        provider: Literal['offline','openai','gemini','groq','anthropic','ollama']
        model: str

    def credential_fingerprint(name):
        import hashlib, os
        from backend.providers import key_for
        material=(key_for(name) or '') if name!='ollama' else __import__('backend.environment',fromlist=['ollama_url']).ollama_url()
        return hashlib.sha256(material.encode()).hexdigest()

    def save_check(name, report):
        from backend.models import ProviderCheck
        from backend.models import now
        with factory.begin() as db:
            previous=db.get(ProviderCheck,name)
            report={'models':previous.report.get('models',[]) if previous and previous.credential_fingerprint==credential_fingerprint(name) else [],**report,'checked_at':now(),'last_success_at':now() if report.get('connected') else (previous.report.get('last_success_at') if previous and previous.credential_fingerprint==credential_fingerprint(name) else None)}
            if previous:
                previous.report=report
                previous.credential_fingerprint=credential_fingerprint(name)
            else: db.add(ProviderCheck(provider=name,credential_fingerprint=credential_fingerprint(name),report=report))
        return report

    @app.get('/providers')
    def providers():
        import os
        from backend.providers import provider
        from backend.models import ProviderCheck
        with factory() as db:
            versions=list(db.scalars(select(Agent)))
            result=[]
            for name in ['offline','openai','gemini','groq','anthropic','ollama']:
                models=[a.configuration['model'] for a in versions if a.configuration['provider']==name]
                model=os.getenv(name.upper()+'_MODEL',models[-1] if models else 'deterministic-v1' if name=='offline' else '')
                row={'provider':name,'model':model,**provider(name).get_health({'model':model}),
                     'api_key_configured':bool(__import__('backend.providers',fromlist=['key_for']).key_for(name)),'available_models':[],'last_success_at':None,'last_check':None,'error':None}
                check=db.get(ProviderCheck,name)
                if check and check.credential_fingerprint==credential_fingerprint(name):
                    report=check.report
                    row.update(last_check=report.get('checked_at'),last_success_at=report.get('last_success_at'),available_models=report.get('models',[]),error=report.get('error'))
                    row['status']='verified_connected' if report.get('connected') else 'disconnected' if report.get('error') else row['status']
                    row['verified_connection']=bool(report.get('connected'))
                    row['verified_model']=report.get('model')
                result.append(row)
            return result

    @app.get('/providers/{name}/models')
    async def provider_models(name: Literal['openai','gemini','groq','anthropic','ollama']):
        from backend.providers import provider, ProviderFailure
        try:
            models=await asyncio.wait_for(provider(name).list_models(),timeout=20)
            from backend.models import ProviderCheck
            with factory.begin() as db:
                row=db.get(ProviderCheck,name)
                previous=dict(row.report) if row and row.credential_fingerprint==credential_fingerprint(name) else {}
                previous['models']=models
                if row:
                    row.report=previous
                    row.credential_fingerprint=credential_fingerprint(name)
                else: db.add(ProviderCheck(provider=name,credential_fingerprint=credential_fingerprint(name),report=previous))
            # Discovery is not a successful generation test.
            return {'provider':name,'models':models,'note':'Provider-discovered identifiers; test generation with your selected model.'}
        except ProviderFailure as exc:
            save_check(name,{'connected':False,'provider':name,'error':str(exc)})
            raise HTTPException(422,str(exc)) from None
        except TimeoutError:
            save_check(name,{'connected':False,'provider':name,'error':'Model discovery timed out'})
            raise HTTPException(422,'Model discovery timed out') from None

    @app.post('/providers/test')
    async def test_connection(body: ConnectionRequest):
        from backend.providers import provider, ProviderFailure
        from backend.contracts import validate
        if not body.model or len(body.model)>120 or 'sk-' in body.model:
            raise HTTPException(422,'Choose a valid model identifier; credentials belong in the backend environment')
        schema={'type':'object','properties':{'ok':{'type':'boolean'}},'required':['ok'],'additionalProperties':False}
        if body.provider=='offline':
            return {'connected':True,'provider':'offline','message':'Offline simulation is ready; no model call was made.'}
        try:
            response=await asyncio.wait_for(provider(body.provider).generate({'model':body.model,'max_output_tokens':512,'timeout_seconds':15},'This is a brief connection test. Reply with OK.','Reply with OK.'),timeout=20)
            if not isinstance(response.output,str) or not response.output.strip():
                raise ValueError('Connection test did not return nonempty text')
            return save_check(body.provider,{'connected':True,'provider':body.provider,'model':body.model,'usage':response.usage,'metadata':response.metadata,'message':'A real text-generation request completed; the selected model returned nonempty text.'})
        except (ProviderFailure,TimeoutError,ValueError,ValidationError) as exc:
            message=str(exc) if isinstance(exc,ProviderFailure) else 'Provider connection test timed out' if isinstance(exc,TimeoutError) else 'Connection test did not return a valid text response'
            save_check(body.provider,{'connected':False,'provider':body.provider,'model':body.model,'error':message})
            raise HTTPException(422,message) from None

    @app.post('/diagnostics',status_code=201)
    async def diagnostics(body: DiagnosticRequest):
        from backend.models import DiagnosticRun
        try:
            report=await diagnose(body)
        except (ValueError,UnicodeError,httpx.HTTPError) as exc:
            raise HTTPException(422,str(exc)) from None
        with factory.begin() as db:
            row=DiagnosticRun(report=report)
            db.add(row)
            db.flush()
            return {'id':row.id,**report}

    @app.get('/diagnostics')
    def diagnostic_history():
        from backend.models import DiagnosticRun
        with factory() as db:
            return [{'id':r.id,'created_at':r.created_at,**r.report} for r in db.scalars(select(DiagnosticRun).order_by(DiagnosticRun.created_at.desc()).limit(100))]

    return app


app = create_app()
