"""Recorded evidence → readable judge-facing output. No inferred attempt results."""
import json
from decimal import Decimal
from html import escape
from datetime import datetime
from zoneinfo import ZoneInfo
import streamlit as st

FAILURE_NAMES={'WORKER_CRASH':'Worker crash','TIMEOUT':'Worker timed out','INVALID_OUTPUT':'Response did not match the expected format',
               'INVALID_INPUT':'Input did not match the expected format','TOOL_FAILURE':'Tool failure','MODEL_FAILURE':'Model request failed',
               'RATE_LIMIT':'Provider rate limit','INTERRUPTED':'Execution interrupted','UNKNOWN':'Unexpected worker error'}


def text_summary(value,limit: int=170) -> str:
    if value is None:
        return 'Not recorded'
    if isinstance(value,dict):
        if not value:
            return 'Empty response object'
        for key in ['summary','content','prompt']:
            if isinstance(value.get(key),str):
                return text_summary(value[key],limit)
        if value.get('findings'):
            return text_summary('; '.join(str(v) for v in value['findings']),limit)
        if value.get('sections'):
            return text_summary('; '.join(str(v.get('body','')) for v in value['sections']),limit)
        for key in ['title','topic']:
            if isinstance(value.get(key),str):
                return text_summary(value[key],limit)
        return text_summary('; '.join(f'{k}: {v}' for k,v in value.items() if k!='source'),limit)
    text=' '.join(str(value).split())
    return text[:limit]+'…' if len(text)>limit else text


def readable(data,operation: str | None=None,label: str='Output',limit: int=700):
    if data is None:
        st.caption('No '+label.lower()+' was recorded.')
        return
    if isinstance(data,dict):
        if not data:
            st.write('Empty response object — no fields were returned.')
            return
        heading=data.get('title') or data.get('topic')
        if heading:
            st.markdown('**'+str(heading)+'**')
        if data.get('summary'):
            readable(data['summary'],label=label,limit=limit)
        if data.get('recommendation'):
            st.markdown('**Recommendation:** '+str(data['recommendation']))
        if 'content' in data:
            readable(data['content'],operation,label,limit)
        if data.get('findings'):
            for item in data['findings']:
                st.markdown('• '+str(item))
        if data.get('sections'):
            for section in data['sections']:
                st.markdown('**'+str(section.get('heading','Section'))+'**')
                readable(section.get('body'),label=label,limit=limit)
        known={'title','topic','summary','recommendation','content','findings','sections','source','keywords'}
        for key,value in data.items():
            if key not in known:
                st.markdown('**'+key.replace('_',' ').title()+'**')
                readable(value,label=label,limit=limit)
        if data.get('keywords'):
            st.caption('Keywords: '+', '.join(map(str,data['keywords'])))
        return
    if isinstance(data,list):
        for item in data[:8]:
            readable(item,operation,label,limit)
        if len(data)>8:
            with st.expander('More '+label.lower()):
                for item in data[8:]:
                    readable(item,operation,label,limit)
        return
    text=str(data)
    if operation=='code':
        st.code(text,language='python')
    elif len(text)>limit:
        st.write(text[:limit]+'…')
        with st.expander('Full '+label.lower()):
            st.write(text)
    else:
        st.write(text)


def stage_schematic(run: dict,vertical: bool=False):
    routes=[]
    for stage in run.get('stages',[]):
        failed=next((a for a in stage['attempts'] if not a['recovery'] and a['status']=='FAILED'),None)
        replacement=next((a for a in reversed(stage['attempts']) if a['recovery']),None)
        state='FAILED' if failed else stage['status']
        style='failed' if state=='FAILED' else 'done' if state=='COMPLETED' else 'active' if state=='RUNNING' else 'pending'
        duration=failed['duration_seconds'] if failed else stage['duration_seconds']
        timing=f'{duration:.2f}s' if duration is not None else 'Not recorded'
        card=f'<div class="evidence-node {style}"><span class="stage-state">{state}</span><small>STEP {stage["position"]+1:02d} · {escape(stage.get("operation") or "stage")}</small><strong>{escape(stage["name"])}</strong><div>{escape(stage["primary_agent_name"])}</div><small>{escape(stage["provider"])} · {timing}</small></div>'
        if not vertical:
            primary_result=('No response returned' if failed['evidence_available'] else 'Not captured') if failed and failed['output'] is None else text_summary(failed['output'] if failed else stage['output'],85)
            card=card[:-6]+f'<p class="io-snippet"><b>Input:</b> {escape(text_summary(stage["input"],85))}</p><p class="io-snippet"><b>{"Primary result" if failed else "Accepted output"}:</b> {escape(primary_result)}</p></div>'
        if replacement:
            status='RECOVERED' if replacement['status']=='COMPLETED' else replacement['status']
            style='recovered' if status=='RECOVERED' else 'failed' if status=='FAILED' else 'active'
            recovery_label='same-model retry' if failed and replacement['agent_id']==failed['agent_id'] else 'compatible replacement'
            card+=f'<div class="recovery-connector">↳ {recovery_label}</div><div class="evidence-node {style}"><span class="stage-state">{status}</span><strong>{escape(replacement["agent_name"])}</strong><small>{escape(replacement["provider"])} · '+(f'{replacement["duration_seconds"]:.2f}s' if replacement['duration_seconds'] is not None else 'Running')+'</small></div>'
            if not vertical:
                card=card[:-6]+f'<p class="io-snippet"><b>Replacement output:</b> {escape(text_summary(replacement["output"],85))}</p></div>'
        routes.append('<div class="stage-route">'+card+'</div>')
    if routes:
        arrow='<div class="route-arrow">↓</div>' if vertical else '<div class="route-arrow">→</div>'
        st.markdown('<div class="trace-schematic '+('vertical' if vertical else '')+'">'+arrow.join(routes)+'</div>',unsafe_allow_html=True)
    else:
        st.info('Stage evidence will appear when this workflow is started.')


def demo_summary(run: dict):
    config=run.get('configuration') or {}
    label='Recovered' if run['recovery_success'] else run['status'].replace('_',' ').title()
    with st.container(border=True):
        st.markdown('**Task prompt**')
        st.write(run['prompt'])
        a,b,c,d=st.columns(4)
        a.metric('Final outcome',label)
        b.metric('Protection',('ON' if config['agentbailout_enabled'] else 'OFF') if 'agentbailout_enabled' in config else 'Not recorded')
        c.metric('Recovery policy',config.get('optimization','Not recorded').title())
        d.metric('Controlled failure',config.get('failure',{}).get('scenario','unknown').replace('_',' ').title())


def final_output(run: dict):
    st.subheader('Final output')
    if run['output'] is None:
        st.info('No final output was produced.' if run['status']=='FAILED' else 'The final result will appear after the workflow completes.')
        return
    stages=run.get('stages',[])
    if stages and stages[-1]['operation']=='custom':
        final=stages[-1]; definition=final.get('definition',{})
        accepted=next((a for a in reversed(final['attempts']) if a['status']=='COMPLETED'),{})
        receipt=accepted.get('provider_metadata') or {}
        st.caption('Generated by '+str(receipt.get('provider',accepted.get('provider',final['provider'])))+' · '+str(receipt.get('model',final.get('model','unknown model')))+f' · {len(stages)} stages')
        content=run['output'].get('content') if isinstance(run['output'],dict) else run['output']
        if definition.get('output_format')=='code':
            st.code(content,language=definition.get('code_language','text'))
            st.caption('Generated code is untrusted text. This workflow did not execute or test it.')
        elif definition.get('output_format')=='json': st.json(content)
        elif definition.get('output_format')=='text': st.text(content)
        else: st.markdown(str(content))
        return
    coding=next((s for s in stages if s['operation']=='code' and s['output']),None)
    if coding:
        st.markdown('**Generated code**')
        readable(coding['output'],'code',label='generated code')
        st.caption('Illustrative generated code · no generated code was executed' if coding['provider']=='offline' else 'Generated code · not executed by this workflow')
        validation=next((s for s in reversed(stages) if s['operation']=='validate' and s['output']),None)
        if validation:
            st.markdown('**Validation result**')
            output=validation['output']
            content=output.get('content') if isinstance(output,dict) else None
            generated=coding['output'].get('content') if isinstance(coding['output'],dict) else None
            if content and generated and content.endswith(generated):
                readable(content[:-len(generated)].strip(),label='validation')
            else:
                readable(output,label='validation')
            st.caption('Output contract validated. This is a review response, not a code test run.')
        last=stages[-1] if stages else None
        if last and last['operation'] not in {'code','validate'}:
            readable(run['output'],last['operation'])
    else:
        readable(run['output'],stages[-1]['operation'] if stages else None)
    modes={a['provider'] for a in run.get('attempts',[])}
    st.caption('Offline deterministic simulation · no external model execution' if modes=={'offline'} else 'Providers used: '+', '.join(sorted(modes)) if modes else 'Provider execution mode was not recorded for this historical run.')


def stage_trace(run: dict):
    st.subheader('Agent input/output trace')
    for stage in run.get('stages',[]):
        with st.container(border=True):
            st.markdown(f'**Step {stage["position"]+1} · {stage["name"]}** · {stage["status"].title()}')
            duration=f'{stage["duration_seconds"]:.2f}s' if stage['duration_seconds'] is not None else 'not recorded'
            st.caption(f'{stage["primary_agent_name"]} · {stage["provider"]} · capability {stage["operation"] or "unknown"} · duration {duration}')
            left,right=st.columns(2)
            with left:
                st.markdown('**Input · '+stage['input_contract']+'**')
                st.write(text_summary(stage['input']))
            with right:
                st.markdown('**Output · '+stage['output_contract']+'**')
                st.write(text_summary(stage['output']))
            with st.expander('Read input and output',expanded=False):
                if stage.get('operation')=='custom':
                    st.markdown('**Stage objective**')
                    st.write(stage.get('definition',{}).get('objective',''))
                    st.markdown('**System instructions**')
                    st.code(stage.get('system_instructions') or '',language='text')
                st.markdown('**Input received**')
                readable(stage['input'],label='input')
                for attempt in stage['attempts']:
                    st.markdown('**'+('Recovery attempt' if attempt['recovery'] else 'Primary attempt')+' · '+attempt['agent_name']+' · '+attempt['status'].title()+'**')
                    receipt=attempt.get('provider_metadata') or {}
                    if receipt.get('submitted_system_instructions'):
                        st.markdown('**System instructions submitted**')
                        st.code(receipt['submitted_system_instructions'],language='text')
                    if receipt:
                        st.caption('Model: '+str(receipt.get('model','unknown'))+' · Request: '+str(receipt.get('request_id','not reported'))+' · Started: '+str(receipt.get('started_at','not reported'))+' · Ended: '+str(receipt.get('ended_at','not reported')))
                    if attempt.get('usage'): st.write('Token usage',attempt['usage'])
                    st.caption('API cost: '+('$'+attempt['api_cost'] if attempt.get('api_cost') is not None else 'unknown'))
                    if not attempt['evidence_available']:
                        st.caption('This historical attempt predates detailed capture. Attempt-specific input/output is unavailable.')
                    else:
                        if attempt['recovery']:
                            st.markdown('**Input sent to recovery**')
                            readable(attempt['input'],label='recovery input')
                        if attempt['error_message']:
                            st.error(attempt['error_message'])
                            if receipt.get('status') not in {None,'completed'} and attempt['output']:
                                st.info('Partial response retained. Copy it into a new task to request an explicit continuation; this incomplete attempt was not accepted as success.')
                        readable(attempt['output'],stage['operation'],label='attempt output')
                st.markdown('**Accepted stage output**')
                readable(stage['output'],stage['operation'],label='stage output')


def failure_details(run: dict):
    failures=[(s,a) for s in run.get('stages',[]) for a in s['attempts'] if a['status']=='FAILED' and not a['recovery']]
    if not failures:
        if run['status']=='FAILED':
            st.error(run.get('error') or 'Workflow ended before a worker result was available.')
        return
    st.subheader('What failed?')
    for stage,attempt in failures:
        label=FAILURE_NAMES.get(attempt['error_category'],attempt['error_category'] or 'Unknown failure')
        if 'Controlled' in (attempt['error_message'] or ''):
            label='Controlled '+label.lower()
        st.error(f'Step {stage["position"]+1} · {stage["name"]} · {attempt["agent_name"]} — {label}')
        st.write(attempt['error_message'] or 'The detailed error was not captured for this historical attempt.')
        st.caption('Expected response: '+stage['output_contract']+' · Input received: '+text_summary(attempt['input'] if attempt['evidence_available'] else stage['input']))
        st.write('Actual failure result:',text_summary(attempt['output']) if attempt['output'] is not None else 'No response was returned.')
        with st.expander('Failed input and response details'):
            readable(attempt['input'] if attempt['evidence_available'] else stage['input'],label='failed input')
            readable(attempt['output'],label='failed response')


def recovery_details(run: dict):
    events=run.get('events',[])
    decisions=[json.loads(e['message']) for e in events if e['type']=='RESCUE_EVALUATED']
    selections=[json.loads(e['message']) for e in events if e['type']=='BACKUP_SELECTED']
    replacements=[(s,a) for s in run.get('stages',[]) for a in s['attempts'] if a['recovery']]
    if not decisions and not replacements:
        if run['failed_attempts']:
            st.info('Protection was OFF; no rescue was attempted.' if not (run.get('configuration') or {}).get('agentbailout_enabled') else 'No recovery decision was recorded.')
        return
    st.subheader('What did AgentBailout do?')
    if decisions:
        decision=decisions[-1]
        st.write(('Rescue approved' if decision['approved'] else 'Rescue declined')+' · '+decision['reason'])
        st.caption(f'Policy: {(run.get("configuration") or {}).get("optimization","cost").title()} · expected simulated cost ${decision["total_rescue_cost"]} · expected time {decision.get("estimated_seconds","not recorded")}s')
    for stage,attempt in replacements:
        retry=attempt['agent_id']==stage.get('primary_agent_id')
        st.markdown('**'+('Same-model retry' if retry else 'Replacement')+' · '+attempt['agent_name']+'**')
        selected=next((s for s in reversed(selections) if s['id']==attempt['agent_id'] and s['version']==attempt['agent_version']),None)
        if selected:
            st.write(selected['rule'])
        failed=next((a for a in stage['attempts'] if not a['recovery'] and a['status']=='FAILED'),None)
        reused=bool(failed and failed['evidence_available'] and attempt['evidence_available'] and failed['input']==attempt['input'])
        st.caption('Verified: the original input was reused unchanged.' if reused else 'Attempt-level input comparison is unavailable for this historical run.' if not attempt['evidence_available'] else 'Inspect the recorded replacement input below.')
        if attempt['status']=='COMPLETED':
            st.success('The recovery call returned a validated output format. The primary configuration was not modified.')
            downstream=next((s for s in run['stages'] if s['position']==stage['position']+1),None)
            st.write('Next stage:',downstream['name']+' · '+downstream['status'].title() if downstream else 'No downstream stage; this was the final stage.')
        else:
            st.warning('Replacement did not complete successfully. No successful repair is claimed.')
        with st.expander('Recovery input and regenerated output'):
            st.markdown('**Input reused**')
            readable(attempt['input'],label='recovery input')
            st.markdown('**Recorded replacement output**')
            readable(attempt['output'],stage['operation'],label='recovery output')
    with st.expander('Recovery options considered'):
        for event in events:
            if event['type']=='RECOVERY_CANDIDATES':
                st.dataframe(json.loads(event['message']),hide_index=True,width='stretch')


def timeline(run: dict):
    with st.expander('Event timeline'):
        st.dataframe([{'Time (IST)':datetime.fromisoformat(e['timestamp']).astimezone(ZoneInfo('Asia/Kolkata')).strftime('%H:%M:%S'),
                       'Event':e['type'].replace('_',' ').title(),'Message':e['message']} for e in run.get('events',[])],hide_index=True,width='stretch',height=230)


def comparison_panel(run: dict,title: str):
    with st.container(border=True):
        st.subheader(title)
        outcome='Recovered' if run['recovery_success'] else run['status'].title()
        duration=f'{run["execution_seconds"]:.2f}s' if run['execution_seconds'] is not None else 'Running'
        cost='$'+run['api_cost'] if run['api_cost'] is not None else 'Unknown'
        style='recovered' if run['recovery_success'] else 'failed' if run['status']=='FAILED' else 'done' if run['status']=='COMPLETED' else 'active'
        st.markdown(f'<div class="compare-summary {style}"><strong>{escape(outcome)}</strong><div class="compare-facts"><span>Total time <b>{duration}</b></span><span>API cost <b>{cost}</b></span><span>Failed attempts <b>{run["failed_attempts"]}</b></span><span>Rescue attempts <b>{run["recovery_attempts"]}</b></span><span>Simulated refund <b>${run["ledger"]["balances"].get("client_refund","0.00")}</b></span><span>Final status <b>{run["status"]}</b></span></div></div>',unsafe_allow_html=True)
        st.caption('Settlement: '+('Settled' if run['ledger']['settled'] else 'Pending'))
        stage_schematic(run,vertical=True)
        failure_details(run)
        recovery_details(run)
        final_output(run)
        with st.expander('Agent input/output trace'):
            stage_trace(run)


def comparison_diff(pair: dict):
    st.subheader('What changed?')
    baseline,protected=pair['baseline'],pair['protected']
    left,right=st.columns(2)
    for col,run in [(left,baseline),(right,protected)]:
        with col:
            failed=[s['name'] for s in run.get('stages',[]) if any(a['status']=='FAILED' and not a['recovery'] for a in s['attempts'])]
            st.write('Failure point: '+(', '.join(failed) if failed else 'No primary failure recorded'))
            st.write('Workflow '+run['status'].lower()+f' · {run["recovery_attempts"]} recovery attempts')
            skipped=[s['name'] for s in run.get('stages',[]) if s['status']=='SKIPPED']
            if skipped:
                st.caption('Did not execute: '+', '.join(skipped))
            elif run['recovery_success']:
                st.caption('A compatible backup regenerated output and the remaining workflow completed.')
    delta=pair.get('time_difference_seconds')
    if delta is not None:
        st.write(f'Additional total run time with protection: {delta:+.2f}s. Simulated allocation difference: ${pair.get("simulated_allocation_difference")}.')
    backup_expense=sum((Decimal(v) for k,v in protected['ledger']['balances'].items() if k in {'backup_expense','recovery_overhead'}),Decimal(0))
    st.caption(f'Actual recorded simulated rescue expense: ${backup_expense:.2f}. Total allocation difference also includes downstream payouts/reserve; it is not purely rescue cost.')
    st.caption('Incremental actual API cost: '+('$'+pair['api_cost_difference'] if pair.get('api_cost_difference') is not None else 'unknown; pricing was not established'))
    decisions=[json.loads(e['message']) for e in protected.get('events',[]) if e['type']=='RESCUE_EVALUATED']
    if decisions:
        d=decisions[-1]
        st.info(('Recovery was worth attempting under the saved policy: ' if d['approved'] else 'The saved policy rejected rescue: ')+d['reason']+f'. Expected net benefit was ${d["expected_net_benefit"]} (simulated estimate); observed outcome: {protected["status"].lower()}.')
    st.caption('Results are recorded, not predicted. A protected completion may cost more and take longer than an early baseline failure.')
