from copy import deepcopy
from decimal import Decimal, ROUND_DOWN
from sqlalchemy import select
from backend.models import Task, Stage, Event, Workflow, Execution, Agent, Attempt, AttemptEvidence
from backend.registry import agent_snapshot, compatible
from backend.contracts import CONTRACTS, PROMPT, contract_name, compatible_operations, OPERATION_NAMES
from backend.ledger import fund, snapshot


def resolve_stages(db, definitions: list[dict], require_configuration=True) -> list[dict]:
    previous_schema = PROMPT
    result = []
    for index,definition in enumerate(definitions):
        operation = definition['operation']
        agent = agent_snapshot(db,definition['agent_id'],definition['version'])
        ok, reason = compatible(agent,operation)
        if not ok and not (not require_configuration and operation=='custom' and reason=='Provider is not configured'):
            raise ValueError(f'{definition["name"]}: {reason}')
        if operation=='custom':
            if agent['provider']=='offline': raise ValueError('Custom LLM stages require an explicitly configured real or local model')
            prior_ids={s.get('id') for s in result}
            if any(identity not in prior_ids for identity in definition.get('selected_prior_ids',[])):
                raise ValueError('Selected context must reference earlier stage IDs')
            if definition.get('id') in prior_ids: raise ValueError('Stage IDs must be unique')
        if operation!='custom' and previous_schema != CONTRACTS[operation][0]:
            previous=definitions[index-1]['name'] if index else 'the task input'
            suggestions=', '.join(OPERATION_NAMES[o] for o in compatible_operations(previous_schema)) or 'end the pipeline here'
            raise ValueError(f'Step {index+1} “{definition["name"]}” cannot follow “{previous}”: it expects {contract_name(CONTRACTS[operation][0])}, but the preceding step produces {contract_name(previous_schema)}. Suggested next steps: {suggestions}.')
        result.append({**definition,'agent':agent})
        previous_schema = CONTRACTS[operation][1]
    return result


def create_execution(db, body, config_override: dict | None = None) -> Task:
    if config_override is None:
        workflow=None
        if body.stages is not None:
            definitions = [s.model_dump() for s in body.stages]
        else:
            workflow = db.get(Workflow,body.workflow_id)
            if not workflow:
                raise ValueError('Workflow not found')
            definitions = workflow.definition['stages']
        stages = resolve_stages(db,definitions)
        refs=body.recovery_pool
        if workflow and 'recovery_pool' not in body.model_fields_set and workflow.definition.get('recovery_pool') is not None:
            from backend.schemas import AgentRef
            refs=[AgentRef.model_validate(r) for r in workflow.definition['recovery_pool']]
        pool = [agent_snapshot(db,r.agent_id,r.version) for r in refs]
        for definition in stages:
            for ref in definition.get('backup_agents',[]):
                candidate=agent_snapshot(db,ref['agent_id'],ref['version'])
                if not any(a['id']==candidate['id'] and a['version']==candidate['version'] for a in pool): pool.append(candidate)
        config = body.model_dump(mode='json',exclude={'prompt','stages','recovery_pool'})
        config.update(stages=stages,recovery_pool=pool)
        config['failure']['stage_index'] = body.failure.stage_index if body.failure.stage_index is not None else min(1,len(stages)-1)
        if config['failure']['stage_index'] >= len(stages):
            raise ValueError('Failure stage is outside the workflow')
        # Reserve the maximum recovery allocation before deciding stage payouts.
        config['stage_payout'] = str(min(Decimal('1'),(body.task_budget-Decimal('.50')-body.recovery_budget)/len(stages)).quantize(Decimal('.01'),rounding=ROUND_DOWN))
    else:
        config = deepcopy(config_override)
    task = Task(prompt=body.prompt)
    task.stages = [Stage(name=s['name'],position=i) for i,s in enumerate(config['stages'])]
    db.add(task)
    db.flush()
    db.add(Execution(task_id=task.id,configuration=config))
    fund(db,task.id,config.get('task_budget','5.00'))
    db.add(Event(task_id=task.id,type='TASK_CREATED',message='Versioned workflow snapshot persisted'))
    if config['failure']['scenario'] != 'normal':
        import json
        db.add(Event(task_id=task.id,type='FAILURE_INJECTED',message=json.dumps(config['failure'])))
    return task


def execution_report(db, task_id: str) -> dict:
    task = db.get(Task,task_id)
    execution = db.get(Execution,task_id)
    attempts = list(db.scalars(select(Attempt).where(Attempt.task_id==task_id).order_by(Attempt.started_at)))
    config=execution.configuration if execution else {}
    definitions=config.get('stages',[])
    agent_configs=[s['agent'] for s in definitions]+config.get('recovery_pool',[])
    serialized=[]
    for attempt in attempts:
        agent=next((a for a in agent_configs if a['id']==attempt.agent_id and a['version']==attempt.agent_version),{})
        from backend.models import ProviderReceipt
        receipt=db.get(ProviderReceipt,attempt.id)
        evidence=db.get(AttemptEvidence,attempt.id)
        row={key:getattr(attempt,key) for key in ('id','stage_id','agent_id','agent_version','recovery','status','started_at','ended_at','duration_seconds','error_category','error_fingerprint','usage','api_cost','simulated_cost','output_valid')}
        row.update(provider_metadata=receipt.details if receipt else None,agent_name=agent.get('name',attempt.agent_id),provider=agent.get('provider','unknown'),
                   evidence_available=bool(evidence),input=evidence.input if evidence else None,
                   output=evidence.output if evidence else None,error_message=evidence.error_message if evidence else None)
        serialized.append(row)
    stages=[]
    for stage in task.stages:
        definition=definitions[stage.position] if stage.position<len(definitions) else {}
        operation=definition.get('operation')
        primary=definition.get('agent',{})
        stages.append({'id':stage.id,'position':stage.position,'name':stage.name,'operation':operation,
                       'primary_agent_name':primary.get('name',stage.worker_id),'primary_agent_id':primary.get('id'),
                       'definition':{k:v for k,v in definition.items() if k!='agent'},'model':primary.get('model'),'system_instructions':definition.get('system_instructions') or primary.get('system_instructions'),'provider':primary.get('provider','unknown'),'status':stage.status,'duration_seconds':stage.duration_seconds,
                       'input':stage.input,'output':stage.result,'error':stage.error,'recovery_attempts':stage.recovery_attempts,
                       'input_contract':'Selected task context' if operation=='custom' else contract_name(CONTRACTS[operation][0]) if operation else 'Historical contract unavailable',
                       'output_contract':definition.get('output_format','markdown').title()+' output' if operation=='custom' else contract_name(CONTRACTS[operation][1]) if operation else 'Historical contract unavailable',
                       'attempts':[a for a in serialized if a['stage_id']==stage.id]})
    events=[{'id':e.id,'timestamp':e.timestamp,'type':e.type,'message':e.message} for e in db.scalars(select(Event).where(Event.task_id==task_id).order_by(Event.id))]
    return {'task_id':task_id,'prompt':task.prompt,'status':task.status,'configuration':execution.configuration if execution else None,
            'execution_seconds':execution.duration_seconds if execution else None,
            'output':task.result,'error':task.error,
            'output_valid':bool(task.result) and all(s.status=='COMPLETED' for s in task.stages),
            'failed_attempts':sum(a.status=='FAILED' for a in attempts),
            'recovery_attempts':sum(a.recovery for a in attempts),
            'recovery_success':task.status=='COMPLETED' and any(a.recovery for a in attempts),
            'api_cost':str(sum(Decimal(a.api_cost) for a in attempts)) if attempts and all(a.api_cost is not None for a in attempts) else None,
            'api_cost_note':'Actual API cost is unknown unless all attempts report a grounded value; simulated allocations are separate.',
            'attempts':serialized,'stages':stages,'events':events,
            'ledger':snapshot(db,task_id)}
