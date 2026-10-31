from copy import deepcopy
from decimal import Decimal, ROUND_DOWN
from sqlalchemy import select
from backend.models import Task, Stage, Event, Workflow, Execution, Agent, Attempt
from backend.registry import agent_snapshot, compatible
from backend.contracts import CONTRACTS, PROMPT
from backend.ledger import fund, snapshot


def resolve_stages(db, definitions: list[dict]) -> list[dict]:
    previous_schema = PROMPT
    result = []
    for definition in definitions:
        operation = definition['operation']
        agent = agent_snapshot(db,definition['agent_id'],definition['version'])
        ok, reason = compatible(agent,operation)
        if not ok:
            raise ValueError(f'{definition["name"]}: {reason}')
        if previous_schema != CONTRACTS[operation][0]:
            raise ValueError(f'{definition["name"]}: preceding output does not match input contract')
        result.append({**definition,'agent':agent})
        previous_schema = CONTRACTS[operation][1]
    return result


def create_execution(db, body, config_override: dict | None = None) -> Task:
    if config_override is None:
        if body.stages is not None:
            definitions = [s.model_dump() for s in body.stages]
        else:
            workflow = db.get(Workflow,body.workflow_id)
            if not workflow:
                raise ValueError('Workflow not found')
            definitions = workflow.definition['stages']
        stages = resolve_stages(db,definitions)
        pool = [agent_snapshot(db,r.agent_id,r.version) for r in body.recovery_pool]
        config = body.model_dump(mode='json',exclude={'prompt','stages','recovery_pool'})
        config.update(stages=stages,recovery_pool=pool)
        config['failure']['stage_index'] = body.failure.stage_index if body.failure.stage_index is not None else min(1,len(stages)-1)
        if config['failure']['stage_index'] >= len(stages):
            raise ValueError('Failure stage is outside the workflow')
        # Reserve the maximum recovery allocation before deciding stage payouts.
        config['stage_payout'] = str(min(Decimal('1'),(Decimal('4.50')-body.recovery_budget)/len(stages)).quantize(Decimal('.01'),rounding=ROUND_DOWN))
    else:
        config = deepcopy(config_override)
    task = Task(prompt=body.prompt)
    task.stages = [Stage(name=s['name'],position=i) for i,s in enumerate(config['stages'])]
    db.add(task)
    db.flush()
    db.add(Execution(task_id=task.id,configuration=config))
    fund(db,task.id)
    db.add(Event(task_id=task.id,type='TASK_CREATED',message='Versioned workflow snapshot persisted'))
    if config['failure']['scenario'] != 'normal':
        import json
        db.add(Event(task_id=task.id,type='FAILURE_INJECTED',message=json.dumps(config['failure'])))
    return task


def execution_report(db, task_id: str) -> dict:
    task = db.get(Task,task_id)
    execution = db.get(Execution,task_id)
    attempts = list(db.scalars(select(Attempt).where(Attempt.task_id==task_id).order_by(Attempt.started_at)))
    return {'task_id':task_id,'status':task.status,'configuration':execution.configuration if execution else None,
            'execution_seconds':execution.duration_seconds if execution else None,
            'output':task.result,'error':task.error,
            'output_valid':bool(task.result) and all(s.status=='COMPLETED' for s in task.stages),
            'failed_attempts':sum(a.status=='FAILED' for a in attempts),
            'recovery_attempts':sum(a.recovery for a in attempts),
            'recovery_success':task.status=='COMPLETED' and any(a.recovery for a in attempts),
            'api_cost':str(sum(Decimal(a.api_cost) for a in attempts)) if attempts and all(a.api_cost is not None for a in attempts) else None,
            'api_cost_note':'Actual API cost is unknown unless all attempts report a grounded value; simulated allocations are separate.',
            'attempts':[{key:getattr(a,key) for key in ('id','stage_id','agent_id','agent_version','recovery','status','started_at','ended_at','duration_seconds','error_category','error_fingerprint','usage','api_cost','simulated_cost','output_valid')} for a in attempts],
            'ledger':snapshot(db,task_id)}
