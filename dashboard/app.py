import json
import os
import httpx
import plotly.express as px
import streamlit as st

st.set_page_config(page_title='AgentBailout', page_icon='🛟', layout='wide')
st.markdown('<style>.stApp{background:#0b1020;color:#e4eafa} h1{letter-spacing:.12em} [data-testid="stMetric"]{background:#151e34;padding:16px;border-radius:12px}</style>', unsafe_allow_html=True)
BASE = os.getenv('AGENTBAILOUT_BACKEND_URL', 'http://127.0.0.1:8003')


def api(method: str, path: str, **kwargs):
    response = httpx.request(method, BASE + path, timeout=10, **kwargs)
    response.raise_for_status()
    return response.json()


st.title('AGENTBAILOUT')
st.caption('The Self-Healing Control Plane for AI Agents · Detect. Diagnose. Decide. Repair. Replace. Recover.')
st.caption('Phase 4: compatible replacement is implemented. Repair and optimization arrive in Phase 5. All ledger amounts are simulations.')
try:
    tasks = api('GET', '/tasks')
    agents = api('GET','/agents')
    workflows = api('GET','/workflows')
except httpx.HTTPError as exc:
    st.error(f'Backend unavailable at {BASE}: {exc}')
    st.stop()

with st.sidebar:
    view = st.radio('Workspace',['Live Execution','Workflow Builder','Agent Registry','Recovery Pool','Comparison Lab'])
    st.header('Task control')
    prompt = st.text_area('Task', 'Plan a community garden with a measurable pilot')
    scenario = st.selectbox('Failure scenario', ['normal','crash','heartbeat_loss','timeout','invalid_output','tool_failure','backup_failure','shared_failure','expensive','insufficient_budget','no_backup','exhausted'])
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
               'agentbailout_enabled':protected,'failure':{'scenario':scenario,'stage_index':target-1},
               'max_attempts':max_attempts,'recovery_budget':str(recovery_budget),'stage_timeout':stage_timeout}
    if st.button('Create task', type='primary'):
        try:
            task = api('POST', '/tasks', json=request)
            st.session_state.selected = task['id']
            st.rerun()
        except httpx.HTTPError as exc:
            st.error(str(exc))
    ids = [t['id'] for t in tasks]
    selected = st.session_state.get('selected', ids[0] if ids else None)
    task_id = st.selectbox('Task history', ids, index=ids.index(selected) if selected in ids else 0) if ids else None
    if st.button('Start task',disabled=not task_id):
        try:
            api('POST', f'/tasks/{task_id}/start')
        except httpx.HTTPError as exc:
            st.error(str(exc))
    if st.button('Inject failure', disabled=scenario == 'normal' or not task_id):
        try:
            api('POST', f'/tasks/{task_id}/inject-failure', json={'scenario':scenario,'stage_index':target-1})
        except httpx.HTTPError as exc:
            st.error(str(exc))
    if st.button('Reset demo selection'):
        st.session_state.pop('selected', None)
        st.rerun()
    auto = st.toggle('Auto refresh', value=True)
    st.button('Refresh')


@st.fragment(run_every=1 if auto else None)
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
        st.error(str(exc))
        return
    st.subheader(f"Workflow · {task['status']}")
    if execution['configuration']:
        st.caption('Protection ON' if execution['configuration']['agentbailout_enabled'] else 'Protection OFF · baseline')
    colors = {'COMPLETED':'🟢','RUNNING':'🔵','FAILED':'🔴','PENDING':'⚪'}
    columns = st.columns(len(task['stages']))
    for col, stage in zip(columns, task['stages']):
        col.metric(f"{colors.get(stage['status'],'🟡')} {stage['name']}", stage['status'])
    st.caption(' → '.join(s['name'] for s in task['stages']))
    graph = 'digraph { rankdir=LR; bgcolor="transparent"; node [style=filled,fillcolor="#24344f",fontcolor=white]; '
    for i,stage in enumerate(task['stages']):
        graph += f'n{i} [label={json.dumps(stage["name"]+" · "+stage["status"])}]; '
        if i:
            graph += f'n{i-1} -> n{i}; '
        if stage['recovery_attempts']:
            graph += f'n{i} -> b{i} [label="recovery"]; b{i} [label={json.dumps(stage["worker_id"])}]; '
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
        col.metric(key.replace('_',' ').title(), f'{value:.1%}' if 'rate' in key else value)
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
            st.error(str(exc))
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
                    st.error(str(exc))
else:
    st.subheader('Comparison Lab')
    st.write('Runs use the same task, frozen agent versions and controlled fault. Runs execute sequentially. Real model outputs may differ.')
    if st.button('Compare both',type='primary'):
        try:
            pair = api('POST','/comparisons',json=request)
            st.session_state.comparison = pair['id']
        except httpx.HTTPError as exc:
            st.error(str(exc))
    pairs = api('GET','/comparisons')
    pair_ids = [p['id'] for p in pairs]
    if pair_ids:
        current = st.session_state.get('comparison',pair_ids[0])
        pair_id = st.selectbox('Comparison history',pair_ids,index=pair_ids.index(current) if current in pair_ids else 0)
        @st.fragment(run_every=1 if auto else None)
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
                st.error(str(exc))
        comparison_live()
    else:
        st.info('Choose a task and fault, then Compare both.')

