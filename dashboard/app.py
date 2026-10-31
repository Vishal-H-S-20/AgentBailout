import json
import os
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import httpx
import plotly.express as px
import streamlit as st
from html import escape
from dashboard.styles import CSS
from dashboard.components import friendly_error, pipeline

st.set_page_config(page_title='AgentBailout', page_icon='🛟', layout='wide')
st.markdown(CSS,unsafe_allow_html=True)
BASE = os.getenv('AGENTBAILOUT_BACKEND_URL', 'http://127.0.0.1:8003')


@st.cache_resource
def api_client():
    return httpx.Client(base_url=BASE,timeout=10)


def api(method: str, path: str, **kwargs):
    response = api_client().request(method,path,**kwargs)
    response.raise_for_status()
    return response.json()


st.markdown('<div class="eyebrow">Recovery control plane / workspace</div>',unsafe_allow_html=True)
st.title('AgentBailout')
if st.session_state.get('workspace','Live Execution')!='Overview':
    st.markdown('<div class="hero"><span class="badge">WORKFLOW PROTECTION</span><h2>Keep the work moving.</h2><p>Detect. Diagnose. Decide. Repair. Replace. Recover.</p></div>',unsafe_allow_html=True)
try:
    tasks = api('GET', '/tasks')
    agents = api('GET','/agents')
    workflows = api('GET','/workflows')
except httpx.HTTPError as exc:
    friendly_error(exc)
    st.stop()

with st.sidebar:
    st.markdown('<div class="brand"><span>◈</span> AgentBailout</div>',unsafe_allow_html=True)
    view = st.radio('Workspace',['Overview','Live Execution','Workflow Builder','Agent Registry','Recovery Pool','Comparison Lab','Code Recovery'],index=1,key='workspace')
    with st.expander('Execution setup',expanded=view in {'Live Execution','Workflow Builder','Comparison Lab'}):
        st.header('Task control')
        prompt = st.text_area('Task', 'Plan a community garden with a measurable pilot')
        scenario = st.selectbox('Failure scenario', ['normal','crash','heartbeat_loss','timeout','invalid_output','tool_failure','backup_failure','shared_failure','expensive','insufficient_budget','no_backup','exhausted'])
        fault_mode = st.radio('Injection mode',['Preconfigured failure','Manual injection'],help='Preconfigured faults run automatically. Manual mode creates an unfaulted task and lets you inject later.')
        protected = st.toggle('AgentBailout protection',value=True)
        st.caption('Applied to new runs. OFF means no retries or recovery.')
        template_ids = [w['id'] for w in workflows]
        template_id = st.selectbox('Workflow template',template_ids,index=template_ids.index('template-research'),format_func=lambda x:next(w['name'] for w in workflows if w['id']==x))
        template = next(w for w in workflows if w['id']==template_id)
        operations = ['research','format','summarize','plan','code','validate','extract','transform','review']
        agent_map = {a['id']+'@'+str(a['version']):a for a in agents}
        definitions = []
        with st.expander('Ordered stages and agents'):
            count = st.number_input('Stage count',min_value=1,max_value=8,value=len(template['stages']),key='count-'+template_id)
            for i in range(count):
                initial = template['stages'][i] if i<len(template['stages']) else template['stages'][-1]
                operation = st.selectbox(f'Stage {i+1} operation',operations,index=operations.index(initial['operation']),key=f'op-{template_id}-{i}')
                choices = [key for key,a in agent_map.items() if operation in a['capabilities']]
                default = initial['agent_id']+'@'+str(initial['version'])
                ref = st.selectbox(f'Stage {i+1} agent',choices,index=choices.index(default) if default in choices else 0,key=f'agent-{template_id}-{i}-{operation}',format_func=lambda x:x+' · '+agent_map[x]['provider'])
                agent = agent_map[ref]
                definitions.append({'name':initial['name'] if operation==initial['operation'] else operation.title(),'operation':operation,'agent_id':agent['id'],'version':agent['version']})
        target = st.number_input('Fault stage (1-based)',min_value=1,max_value=count,value=min(2,count))
        with st.expander('Recovery configuration'):
            pool_refs = st.multiselect('Recovery pool',list(agent_map),default=[k for k in agent_map if k.startswith('recovery-')])
            max_attempts = st.number_input('Maximum recovery attempts per stage',min_value=1,max_value=3,value=1)
            recovery_budget = st.number_input('Simulated recovery budget',min_value=0.0,max_value=4.0,value=1.0,step=.05)
            stage_timeout = st.number_input('Stage runtime timeout (seconds)',min_value=.1,max_value=120.0,value=10.0)
        request = {'prompt':prompt,'workflow_id':template_id,'stages':definitions,
                   'recovery_pool':[{'agent_id':agent_map[k]['id'],'version':agent_map[k]['version']} for k in pool_refs],
                   'agentbailout_enabled':protected,'failure':{'scenario':scenario if fault_mode=='Preconfigured failure' else 'normal','stage_index':target-1},
                   'max_attempts':max_attempts,'recovery_budget':str(recovery_budget),'stage_timeout':stage_timeout}
        if st.button('Create task', type='primary'):
            try:
                task = api('POST', '/tasks', json=request)
                st.session_state.selected = task['id']
                st.session_state.task_history = task['id']
                st.rerun()
            except httpx.HTTPError as exc:
                friendly_error(exc)
        ids = [t['id'] for t in tasks]
        if st.session_state.get('pending_task'):
            st.session_state.selected=st.session_state.pop('pending_task')
            st.session_state.task_history=st.session_state.selected
        selected = st.session_state.get('selected', ids[0] if ids else None)
        if ids and st.session_state.get('task_history') not in ids:
            st.session_state.task_history = selected if selected in ids else ids[0]
        task_id = st.selectbox('Task history',ids,key='task_history',format_func=lambda x:f'{x[:8]} · '+next(t['status'] for t in tasks if t['id']==x)) if ids else None
        selected_task = api('GET',f'/tasks/{task_id}') if task_id else None
        selected_run = api('GET',f'/tasks/{task_id}/execution') if task_id else None
        saved = selected_run['configuration'] if selected_run else None
        saved_fault = saved['failure'] if saved else {'scenario':'normal','stage_index':None}
        draft_differs = bool(saved and (saved['agentbailout_enabled']!=protected or (fault_mode=='Preconfigured failure' and saved_fault!=request['failure']) or saved['workflow_id']!=template_id or [{k:s[k] for k in ('name','operation','agent_id','version')} for s in saved['stages']]!=definitions))
        if task_id:
            st.caption(f'Selected {task_id[:8]} · {selected_task["status"]}')
            st.caption(f'Saved fault: {saved_fault["scenario"]} · stage {(saved_fault["stage_index"] or 0)+1} · protection {"ON" if saved and saved["agentbailout_enabled"] else "OFF"}')
            if draft_differs:
                st.warning('Draft settings differ from this task. Click Create task to apply them to a new run.')
        if st.button('Start task',disabled=not task_id or selected_task['status']!='CREATED' or draft_differs):
            try:
                api('POST', f'/tasks/{task_id}/start')
            except httpx.HTTPError as exc:
                friendly_error(exc)
        manual_scenario = st.selectbox('Manual failure type',['crash','heartbeat_loss','timeout','invalid_output','tool_failure']) if fault_mode=='Manual injection' else 'crash'
        pending = [s['position'] for s in selected_task['stages'] if s['status']=='PENDING'] if selected_task else []
        manual_target = st.selectbox('Manual fault stage',pending,format_func=lambda x:f'Stage {x+1} · '+selected_task['stages'][x]['name']) if fault_mode=='Manual injection' and pending else None
        can_inject = bool(task_id and fault_mode=='Manual injection' and selected_task['status'] in {'CREATED','RUNNING'} and saved_fault['scenario']=='normal' and manual_target is not None)
        if saved_fault['scenario']!='normal':
            st.caption('Fault already saved. It runs automatically; no second injection is needed.')
        elif selected_task and selected_task['status'] in {'COMPLETED','FAILED'}:
            st.caption('This task is complete. Create a new task to inject a failure.')
        if st.button('Inject failure', disabled=not can_inject):
            try:
                result=api('POST', f'/tasks/{task_id}/inject-failure', json={'scenario':manual_scenario,'stage_index':manual_target})
                st.session_state.flash=result['message']
                st.rerun()
            except httpx.HTTPError as exc:
                friendly_error(exc)
        if st.button('Reset demo selection'):
            st.session_state.pop('selected', None)
            st.rerun()
        auto = st.toggle('Auto refresh', value=True)
        st.button('Refresh')
if st.session_state.get('flash'):
    st.success(st.session_state.pop('flash'))

if view in {'Live Execution','Workflow Builder'}:
    launch,execute,context=st.columns([1,1,2])
    with launch:
        if st.button('Create & select task',type='primary',width='stretch'):
            try:
                created=api('POST','/tasks',json=request)
                st.session_state.pending_task=created['id']
                st.rerun()
            except httpx.HTTPError as exc:
                friendly_error(exc)
    with execute:
        if st.button('Start selected task',disabled=not task_id or selected_task['status']!='CREATED' or draft_differs,width='stretch'):
            try:
                api('POST',f'/tasks/{task_id}/start')
                st.rerun()
            except httpx.HTTPError as exc:
                friendly_error(exc)
    with context:
        st.caption(f'Selected: {task_id[:8] if task_id else "None"} · Saved configuration is shown below. Draft changes apply to new tasks.')


@st.fragment(run_every=2 if auto else None)
def live():
    if not task_id:
        st.info('Choose a template, create a task, then start execution.')
        return
    try:
        task = api('GET', f'/tasks/{task_id}')
        events = api('GET', f'/tasks/{task_id}/events')
        ledger = api('GET', f'/tasks/{task_id}/ledger')
        metrics = api('GET', '/metrics')
        execution = api('GET',f'/tasks/{task_id}/execution')
    except httpx.HTTPError as exc:
        friendly_error(exc)
        return
    if selected_task and task['status']!=selected_task['status']:
        st.rerun(scope='app')
    st.subheader(f"Workflow · {task['status']}")
    st.markdown(f'<div class="taskbar"><span class="badge">{task["status"]}</span> &nbsp; <b>{task["id"][:8]}</b> &nbsp; {escape(task["prompt"][:100])}<div class="small">Full ID: {task["id"]}</div></div>',unsafe_allow_html=True)
    if execution['configuration']:
        st.caption('Protection ON' if execution['configuration']['agentbailout_enabled'] else 'Protection OFF · baseline')
        persisted_fault=execution['configuration']['failure']
        st.caption('Saved fault: '+persisted_fault['scenario']+' · stage '+str(persisted_fault['stage_index']+1)+(' · triggers automatically at stage entry' if persisted_fault['scenario']!='normal' else ' · no active fault'))
    colors = {'COMPLETED':'🟢','RUNNING':'🔵','FAILED':'🔴','PENDING':'⚪'}
    pipeline(task['stages'])
    graph = 'digraph { rankdir=LR; bgcolor="transparent"; node [style=filled,fillcolor="#24344f",fontcolor=white]; '
    for i,stage in enumerate(task['stages']):
        graph += f'n{i} [label={json.dumps(stage["name"]+" · "+stage["status"])}]; '
        if i:
            graph += f'n{i-1} -> n{i}; '
        if stage['recovery_attempts']:
            graph += f'n{i} -> b{i} [label="recovery"]; b{i} [label={json.dumps(stage["worker_id"])}]; '
    if any(s['recovery_attempts'] for s in task['stages']):
        with st.expander('Recovery routing'):
            st.graphviz_chart(graph+'}')
    if any(s['recovery_attempts'] for s in task['stages']):
        st.info('Compatible recovery agent activated · completed upstream results reused')
    a,b = st.columns(2)
    with a:
        st.subheader('Economic decision')
        decisions = [json.loads(e['message']) for e in events if e['type']=='RESCUE_EVALUATED']
        if decisions:
            decision = decisions[-1]
            st.metric('Rescue cost (simulated)', '$'+decision['total_rescue_cost'])
            st.write('Approved' if decision['approved'] else 'Rejected', '—', decision['reason'])
            ratio=decision.get('cost_ratio')
            st.caption(f'Cost ratio: {float(ratio):.1%}' if ratio is not None else 'Cost ratio unavailable')
            st.caption('Expected net benefit (simulated): $'+decision['expected_net_benefit'])
            with st.expander('Decision evidence'):
                st.json(decision)
        else:
            st.caption('No rescue evaluation yet.')
    with b:
        st.subheader('Simulated ledger')
        st.write('Settled' if ledger['settled'] else 'Escrow funded / awaiting execution')
        st.write('Balanced:', ledger['balanced'])
        balances = ledger['balances']
        st.dataframe([{'Account':k,'Balance':v} for k,v in balances.items()], hide_index=True)
        positive = {k:float(v) for k,v in balances.items() if k not in {'client','escrow'} and float(v)>0}
        if positive:
            st.plotly_chart(px.bar(x=list(positive), y=list(positive.values()), labels={'x':'Account','y':'Simulated dollars'}, template='plotly_dark'), width='stretch')
    st.subheader('Recovery metrics')
    cols = st.columns(len(metrics))
    for col,(key,value) in zip(cols,metrics.items()):
        display=f'{value:.1%}' if 'rate' in key else f'{value:.2f}s' if 'seconds' in key else '$'+str(value) if 'cost' in key else value
        col.metric(key.replace('_',' ').title(), display)
    st.subheader('Event timeline')
    st.dataframe(events, hide_index=True, width='stretch')
    with st.expander('Ledger journal'):
        st.dataframe(ledger['entries'], hide_index=True, width='stretch')
    if task['result']:
        st.subheader('Final output')
        st.write(task['result'].get('summary',task['result'].get('content',task['result'])))
        if task['result'].get('recommendation'):
            st.success(task['result']['recommendation'])
        st.caption(task['result'].get('source',''))
    with st.expander('Execution configuration and attempts'):
        st.json(execution)
    if task['error']:
        st.error(task['error'])


if view == 'Live Execution':
    live()
elif view == 'Workflow Builder':
    st.subheader('Ordered workflow builder')
    st.write('Choose operations and agents in the sidebar. Positions define execution order. Saving checks adjacent data contracts.')
    st.dataframe(definitions,hide_index=True,width='stretch')
    workflow_name = st.text_input('Workflow name','My workflow')
    if st.button('Save workflow'):
        try:
            saved = api('POST','/workflows',json={'name':workflow_name,'stages':definitions})
            st.success('Saved '+saved['id'])
        except httpx.HTTPError as exc:
            friendly_error(exc)
elif view in {'Agent Registry','Recovery Pool'}:
    st.subheader(view)
    st.caption('Offline agents are deterministic simulations. Configured means credentials are present, not that a remote connection was verified. Reliability is measured from observed samples; no samples means unknown.')
    st.dataframe([{k:a[k] for k in ('id','version','name','provider','model','capabilities','estimated_cost','estimated_latency','observed_average_latency','measured_reliability','reliability_sample_count','provider_health')} for a in agents],hide_index=True,width='stretch')
    if view == 'Agent Registry':
        with st.form('register-agent'):
            identity = st.text_input('Agent ID','custom-agent')
            name = st.text_input('Agent name','Custom agent')
            source = st.selectbox('Provider',['offline','openai'])
            model = st.text_input('Model identifier','deterministic-v1',help='For OpenAI, replace this with a model identifier available to your account. Set OPENAI_API_KEY on the backend; never enter credentials here.')
            instructions = st.text_area('System instructions','Perform the stage and return the declared structured output.')
            capabilities = st.multiselect('Capabilities',operations,default=['research','format','summarize'])
            estimate = st.number_input('Estimated simulated replacement cost',min_value=0.0,max_value=100.0,value=.25,step=.01)
            available = st.checkbox('Available for selection',value=True)
            if st.form_submit_button('Register new version'):
                try:
                    row = api('POST','/agents',json={'id':identity,'name':name,'provider':source,'model':model,'system_instructions':instructions,'capabilities':capabilities,'estimated_cost':str(estimate),'available':available})
                    st.success(f'Registered {row["id"]} v{row["version"]}; availability: {row["provider_health"]["status"]}')
                except httpx.HTTPError as exc:
                    friendly_error(exc)
elif view == 'Overview':
    st.subheader('Workspace overview')
    metrics=api('GET','/metrics')
    for col,(label,value) in zip(st.columns(4),[('Tasks processed',metrics['tasks_processed']),('Failures detected',metrics['failures_detected']),('Successful recoveries',metrics['successful_recoveries']),('Recovery success',f'{metrics["recovery_success_rate"]:.0%}')]):
        col.metric(label,value)
    left,right=st.columns([2,1])
    with left:
        st.markdown('<div class="section-label">Execution history</div>',unsafe_allow_html=True)
        if tasks:
            import pandas as pd
            frame=pd.DataFrame([{'Time':t['created_at'],'Status':t['status'],'Task':t['id'][:8]} for t in tasks])
            counts=frame.groupby('Status').size().reset_index(name='Executions')
            figure=px.bar(counts,x='Status',y='Executions',color='Status',color_discrete_map={'COMPLETED':'#686dff','FAILED':'#ed687e','CREATED':'#59637a','RUNNING':'#459bff'},template='plotly_dark')
            figure.update_layout(paper_bgcolor='#14171e',plot_bgcolor='#14171e',showlegend=False,height=300,margin=dict(l=20,r=20,t=20,b=20))
            st.plotly_chart(figure,width='stretch')
            st.dataframe(frame,hide_index=True,width='stretch')
        else:
            st.info('Create your first workflow to populate the execution history.')
    with right:
        st.markdown('<div class="section-label">Recovery health</div>',unsafe_allow_html=True)
        st.metric('Mean recovery time',f'{metrics["average_recovery_seconds"]:.2f}s')
        st.metric('Simulated recovery expenditure','$'+metrics['total_simulated_rescue_cost'])
        st.caption('All charts use stored backend records. API costs and simulated allocations are distinct.')
elif view == 'Code Recovery':
    st.subheader('Code & repository recovery')
    st.caption('Inspect Python/GitHub source without running it, or demonstrate a real runtime failure and validated input normalization in a fixed local program.')
    diagnostic_mode=st.radio('Diagnostic adapter',['Python execution','Repository inspection'])
    if diagnostic_mode=='Python execution':
        amount=st.text_input('Numeric input','12.50')
        st.code('data = {"amount": "12.50"}\nprint(data["amount"] + 1)  # genuine TypeError until normalized',language='python')
        repair=st.toggle('Normalize and revalidate',value=True)
        body={'kind':'python','amount':amount,'protection':repair}
    else:
        url=st.text_input('Public GitHub repository or Python file URL','')
        source=st.text_area('Python source for static inspection','def total(value):\nreturn value * 2\n',height=160)
        body={'kind':'repository','repository_url':url,'source':source}
        st.caption('A repository URL inspects main.py at HEAD; use a /blob/branch/file.py URL for another Python file. No clone, dependency install or repository code execution occurs.')
    if st.button('Run diagnostic',type='primary'):
        try:
            st.session_state.diagnostic=api('POST','/diagnostics',json=body)
        except httpx.HTTPError as exc:
            friendly_error(exc)
    if st.session_state.get('diagnostic'):
        report=st.session_state.diagnostic
        st.caption('Last recorded diagnostic: '+report['id'][:8]+' · '+report['kind'])
        st.metric('Diagnostic result',report['status'])
        st.caption(report['scope'])
        st.dataframe(report['events'],hide_index=True,width='stretch')
        if report.get('primary'):
            st.code(report['primary']['stderr'],language='text')
        if report.get('recovery'):
            if report['status']=='RECOVERED':
                st.success('Re-executed successfully and checked the numeric result.')
            else:
                st.error('The rerun did not pass result validation. Recovery was not accepted.')
            st.code(report['recovery']['stdout'],language='json')
    with st.expander('Diagnostic history'):
        st.json(api('GET','/diagnostics'))
else:
    st.subheader('Comparison Lab')
    st.write('Runs use the same task, frozen agent versions and controlled fault. Runs execute sequentially. Real model outputs may differ.')
    if st.button('Compare both',type='primary'):
        try:
            pair = api('POST','/comparisons',json=request)
            st.session_state.comparison = pair['id']
        except httpx.HTTPError as exc:
            friendly_error(exc)
    pairs = api('GET','/comparisons')
    pair_ids = [p['id'] for p in pairs]
    if pair_ids:
        current = st.session_state.get('comparison',pair_ids[0])
        pair_id = st.selectbox('Comparison history',pair_ids,index=pair_ids.index(current) if current in pair_ids else 0)
        @st.fragment(run_every=2 if auto else None)
        def comparison_live():
            try:
                pair = api('GET','/comparisons/'+pair_id)
                for col,key,title in zip(st.columns(2),['baseline','protected'],['Without AgentBailout','With AgentBailout']):
                    run = pair[key]
                    with col:
                        st.subheader(title)
                        st.metric('Status',run['status'])
                        st.write('Execution seconds:',run['execution_seconds'])
                        st.write('Actual API cost:',run['api_cost'] if run['api_cost'] is not None else 'Unknown')
                        st.write('Simulated allocation:',run['ledger']['balances'])
                        st.write('Output valid:',run['output_valid'])
                        st.write(run['output'] or run['error'] or 'Execution pending')
                        st.dataframe(run['attempts'],hide_index=True,width='stretch')
                st.write('Protected minus baseline time (seconds):',pair['time_difference_seconds'])
                st.write('Protected minus baseline simulated allocation:',pair.get('simulated_allocation_difference'))
                st.write('Actual API cost difference:',pair.get('api_cost_difference'))
                st.caption(pair['note'])
            except httpx.HTTPError as exc:
                friendly_error(exc)
        comparison_live()
    else:
        st.info('Choose a task and fault, then Compare both.')
