"""Generic sequential engine; fencing and recovery bounds are owned here, not by agents."""
import asyncio
import hashlib
import json
from decimal import Decimal
from time import monotonic
from sqlalchemy import select
from jsonschema import ValidationError
from backend.models import Task, Stage, Event, Execution, Attempt, Agent, AttemptEvidence, now
from backend.contracts import CONTRACTS, validate
from backend.providers import provider, ProviderFailure, ProviderResult
from backend.models import ProviderReceipt
from backend.registry import compatible
from backend.solvency import evaluate


def event(factory, task_id: str, kind: str, message: str) -> None:
    with factory.begin() as db:
        db.add(Event(task_id=task_id,type=kind,message=message))


def set_state(factory, task_id: str, status: str) -> None:
    from backend.supervisor import transition
    with factory.begin() as db:
        transition(db.get(Task,task_id),status)


async def attempt(factory, task_id: str, stage_id: str, agent: dict, operation: str,
                  data: dict, config: dict, recovery: bool, fault: str) -> dict:
    started = monotonic()
    with factory.begin() as db:
        record = Attempt(task_id=task_id,stage_id=stage_id,agent_id=agent['id'],agent_version=agent['version'],
                         recovery=recovery,simulated_cost=agent['estimated_cost'] if recovery else '0.00',
                         api_cost='0.00' if agent['provider']=='offline' or fault!='normal' else None)
        db.add(record)
        db.flush()
        attempt_id = record.id
        db.add(AttemptEvidence(attempt_id=attempt_id,input=data))
        db.get(Stage,stage_id).worker_id = agent['id']+'-v'+str(agent['version'])+'-'+attempt_id
    heartbeat = [monotonic()]

    async def pulse():
        while True:
            heartbeat[0] = monotonic()
            with factory.begin() as db:
                db.get(Stage,stage_id).heartbeat_at = now()
            await asyncio.sleep(min(.2,config['heartbeat_timeout']/3))

    async def work():
        if fault in {'crash','backup_failure','expensive','insufficient_budget','no_backup','exhausted'}:
            raise ProviderFailure('WORKER_CRASH','Controlled worker crash')
        if fault == 'shared_failure':
            raise ProviderFailure('INVALID_INPUT','Controlled shared input contract failure')
        if fault == 'tool_failure':
            raise ProviderFailure('TOOL_FAILURE','Controlled external-tool failure; no actual tool called')
        if fault in {'heartbeat_loss','timeout'}:
            await asyncio.Event().wait()
        try:
            validate(data,CONTRACTS[operation][0])
        except ValidationError:
            raise ProviderFailure('INVALID_INPUT','Input failed the declared data contract') from None
        await asyncio.sleep(agent['estimated_latency'] if agent['provider']=='offline' else 0)
        response = ProviderResult({},api_cost='0.00') if fault=='invalid_output' else await provider(agent['provider']).execute(agent,operation,data,CONTRACTS[operation][1])
        # Save real usage even if schema validation later fails.
        with factory.begin() as db:
            record = db.get(Attempt,attempt_id)
            record.usage,record.api_cost = response.usage,response.api_cost
            db.get(AttemptEvidence,attempt_id).output=response.output
            if response.metadata: db.add(ProviderReceipt(attempt_id=attempt_id,details=response.metadata))
        try:
            validate(response.output,CONTRACTS[operation][1])
        except ValidationError:
            raise ProviderFailure('INVALID_OUTPUT','Output failed the declared data contract') from None
        return response.output

    worker = asyncio.create_task(work())
    ticker = None if fault=='heartbeat_loss' else asyncio.create_task(pulse())
    failure = None
    try:
        from backend.watchdog import monitor
        try:
            timeout=max(.001,min(config['stage_timeout'],config.get('_deadline',float('inf'))-monotonic()))
            output = await asyncio.wait_for(monitor(worker,heartbeat,config['heartbeat_timeout']),timeout=timeout)
        except TimeoutError:
            raise ProviderFailure('TIMEOUT','Worker heartbeat expired' if fault=='heartbeat_loss' else 'Stage execution deadline expired') from None
        return output
    except ProviderFailure as exc:
        failure = exc
        raise
    except asyncio.CancelledError:
        failure = ProviderFailure('INTERRUPTED','Execution interrupted')
        raise
    except Exception:
        failure = ProviderFailure('UNKNOWN','Unexpected worker error; see local diagnostics')
        raise failure from None
    finally:
        worker.cancel()
        if ticker:
            ticker.cancel()
        await asyncio.gather(worker,*([ticker] if ticker else []),return_exceptions=True)
        duration = monotonic()-started
        with factory.begin() as db:
            record = db.get(Attempt,attempt_id)
            record.status = 'FAILED' if failure else 'COMPLETED'
            record.ended_at,record.duration_seconds = now(),duration
            record.output_valid = failure is None
            if failure:
                db.get(AttemptEvidence,attempt_id).error_message=str(failure)
                record.error_category = failure.category
                record.error_fingerprint = fingerprint(failure,operation,data)
            row = db.get(Agent,(agent['id'],agent['version']))
            if row:
                row.total_seconds += duration
                row.last_execution_at = now()
                row.recovery_involvement += int(recovery)
                row.successes += int(failure is None)
                row.failures += int(failure is not None)
                row.timeouts += int(failure is not None and failure.category=='TIMEOUT')


def fingerprint(error: ProviderFailure, operation: str, data: dict) -> str:
    # Content hashes, never raw sensitive inputs or provider error bodies.
    return hashlib.sha256(json.dumps([error.category,str(error),operation,data],sort_keys=True).encode()).hexdigest()


async def recover(factory, task_id: str, stage_id: str, definition: dict, data: dict,
                  config: dict, original: ProviderFailure, mode: str) -> dict:
    event(factory,task_id,'FAILURE_DETECTED',json.dumps({'stage_id':stage_id,'category':original.category,
        'message':str(original),'fingerprint':fingerprint(original,definition['operation'],data)}))
    if not config['agentbailout_enabled']:
        event(factory,task_id,'RECOVERY_DISABLED','Baseline mode: no retries or advanced recovery')
        raise original
    set_state(factory,task_id,'RESCUING')
    candidates = []
    for candidate in config['recovery_pool']:
        ok, reason = compatible(candidate,definition['operation'])
        if definition['agent']['provider']!='offline' and candidate['provider']=='offline':
            ok,reason = False,'Real LLM stages cannot recover using offline simulation'
        if candidate['estimated_latency'] > config['stage_timeout']:
            ok,reason = False,'Estimated candidate latency exceeds stage runtime limit'
        if candidate['estimated_latency'] > config.get('_deadline',float('inf'))-monotonic():
            ok,reason = False,'Candidate cannot fit the remaining task deadline'
        if candidate['id']==definition['agent']['id']:
            ok,reason = False,'Same agent identity as failed primary'
        if mode=='no_backup':
            ok,reason = False,'Controlled absence of eligible backups'
        candidates.append({'agent':candidate,'eligible':ok,'reason':reason})
    eligible = [c['agent'] for c in candidates if c['eligible']]
    from backend.policy import rank_candidates
    strategy=config.get('optimization','cost')
    eligible=rank_candidates(eligible,strategy)
    event(factory,task_id,'RECOVERY_CANDIDATES',json.dumps([{'id':c['agent']['id'],'version':c['agent']['version'],
          'eligible':c['eligible'],'reason':c['reason'],'estimated_cost':c['agent']['estimated_cost'],
          'estimated_seconds':c['agent']['estimated_latency'],'success_probability_estimate':c['agent']['selection_reliability']} for c in candidates]))
    if not eligible:
        decision = evaluate()
        decision.update(approved=False,reason='No compatible available recovery agent')
        event(factory,task_id,'RESCUE_EVALUATED',json.dumps(decision))
        event(factory,task_id,'RESCUE_REJECTED',decision['reason'])
        raise ProviderFailure('NO_BACKUP',decision['reason'])
    previous = {fingerprint(original,definition['operation'],data)}
    for candidate in eligible:
        with factory() as db:
            count = db.get(Stage,stage_id).recovery_attempts
            spent = sum(Decimal(a.simulated_cost)+Decimal('.05') for a in db.scalars(select(Attempt).where(Attempt.task_id==task_id,Attempt.recovery==True)))
        if count >= config['max_attempts']:
            break
        cost = '3.00' if mode=='expensive' else candidate['estimated_cost']
        decision = evaluate(cost,config.get('task_budget','5.00'),candidate['selection_reliability'])
        decision.update(strategy=strategy,estimated_seconds=candidate['estimated_latency'])
        if mode=='insufficient_budget' or spent+Decimal(decision['total_rescue_cost'])>Decimal(config['recovery_budget']):
            decision.update(approved=False,reason='Remaining simulated recovery budget is insufficient')
        event(factory,task_id,'RESCUE_EVALUATED',json.dumps(decision))
        if not decision['approved']:
            event(factory,task_id,'RESCUE_REJECTED',decision['reason'])
            raise ProviderFailure('BUDGET_EXCEEDED',decision['reason'])
        with factory.begin() as db:
            stage = db.get(Stage,stage_id)
            stage.recovery_attempts += 1
            stage.worker_id = candidate['id']+'-v'+str(candidate['version'])
        event(factory,task_id,'RESCUE_APPROVED',decision['reason'])
        reason=f'{strategy.title()} policy ranked {candidate["name"]} using expected cost/time and observed/prior reliability. Its quote was ${candidate["estimated_cost"]}, estimated runtime {candidate["estimated_latency"]}s and success estimate {Decimal(candidate["selection_reliability"]):.1%}; compatibility, budget and deadline checks passed.'
        event(factory,task_id,'BACKUP_SELECTED',json.dumps({'id':candidate['id'],'version':candidate['version'],'rule':reason}))
        event(factory,task_id,'BACKUP_STARTED',candidate['id'])
        backup_fault = 'shared_failure' if mode=='shared_failure' else 'crash' if mode in {'backup_failure','exhausted'} else 'normal'
        try:
            result = await attempt(factory,task_id,stage_id,candidate,definition['operation'],data,config,True,backup_fault)
        except ProviderFailure as exc:
            current = fingerprint(exc,definition['operation'],data)
            event(factory,task_id,'BACKUP_FAILED',json.dumps({'category':exc.category,'fingerprint':current}))
            if current in previous:
                event(factory,task_id,'SHARED_FAILURE_DETECTED','Identical failure fingerprint; circuit opened without inventing input data')
                raise ProviderFailure('SHARED_DEPENDENCY_FAILURE','Repeated identical failure; no verified correction available') from None
            previous.add(current)
            continue
        event(factory,task_id,'BACKUP_COMPLETED',candidate['id'])
        event(factory,task_id,'WORKFLOW_RESUMED','Validated replacement output; upstream results reused')
        set_state(factory,task_id,'RESCUED')
        return result
    raise ProviderFailure('ATTEMPTS_EXHAUSTED','Eligible candidates or recovery attempts exhausted')


async def execute(factory, task_id: str) -> None:
    from backend.supervisor import fail, STAGE_SECONDS
    from backend.ledger import settle
    started = monotonic()
    active_id = None
    try:
        with factory.begin() as db:
            execution = db.get(Execution,task_id)
            execution.started_at = now()
            config = dict(execution.configuration)
            config['_deadline']=started+config.get('deadline_seconds',120)
            task = db.get(Task,task_id)
            data = {'prompt':task.prompt}
            stage_ids = [s.id for s in task.stages]
        for index,(stage_id,definition) in enumerate(zip(stage_ids,config['stages'])):
            if monotonic()>=config['_deadline']:
                raise ProviderFailure('DEADLINE_EXCEEDED','Task deadline expired')
            active_id = stage_id
            stage_start = monotonic()
            with factory.begin() as db:
                stage = db.get(Stage,stage_id)
                stage.status,stage.started_at,stage.input = 'RUNNING',now(),data
                stage.worker_id = definition['agent']['id']+'-v'+str(definition['agent']['version'])
                db.add(Event(task_id=task_id,type='AGENT_STARTED',message=stage.name))
            await asyncio.sleep(min(STAGE_SECONDS,max(0,config['_deadline']-monotonic())))
            remaining=config['_deadline']-monotonic()
            if remaining<=0:
                raise ProviderFailure('DEADLINE_EXCEEDED','Task deadline expired before stage execution')
            stage_config={**config,'stage_timeout':min(config['stage_timeout'],remaining)}
            # Read fresh fault configuration to support injection into a running pending stage.
            with factory() as db:
                current = db.get(Execution,task_id).configuration
                fault = current['failure']
            mode = fault['scenario'] if fault['stage_index']==index else 'normal'
            try:
                output = await attempt(factory,task_id,stage_id,definition['agent'],definition['operation'],data,stage_config,False,mode)
            except ProviderFailure as exc:
                output = await recover(factory,task_id,stage_id,definition,data,stage_config,exc,mode)
            data = output
            with factory.begin() as db:
                stage = db.get(Stage,stage_id)
                stage.result,stage.status,stage.ended_at = data,'COMPLETED',now()
                stage.duration_seconds = monotonic()-stage_start
                db.add(Event(task_id=task_id,type='AGENT_COMPLETED',message=stage.name))
                # Return to RUNNING after recovered stage so later stages can independently recover.
                if db.get(Task,task_id).status=='RESCUED':
                    from backend.supervisor import transition
                    transition(db.get(Task,task_id),'RUNNING')
        with factory.begin() as db:
            from backend.supervisor import transition
            task = db.get(Task,task_id)
            task.result = data
            transition(task,'COMPLETED')
            db.add(Event(task_id=task_id,type='TASK_COMPLETED',message='All configured stages validated'))
            settle(db,task)
    except asyncio.CancelledError:
        fail(factory,task_id,active_id,'Execution interrupted by server shutdown')
        raise
    except ProviderFailure as exc:
        fail(factory,task_id,active_id,f'{exc.category}: {exc}')
    except Exception:
        fail(factory,task_id,active_id,'Unexpected orchestration error')
    finally:
        with factory.begin() as db:
            execution = db.get(Execution,task_id)
            execution.ended_at,execution.duration_seconds = now(),monotonic()-started
