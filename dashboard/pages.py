import json
from datetime import datetime
from zoneinfo import ZoneInfo
from html import escape
import httpx
import plotly.graph_objects as go
import streamlit as st
from dashboard.client import api
from dashboard.state import field,navigate,quick_demo
from dashboard.components import friendly_error,pipeline,preview,recovery_story
from dashboard.agent_form import add_agent,PROVIDERS,OPERATIONS
from dashboard.presentation import demo_summary,stage_schematic,final_output,stage_trace,failure_details,recovery_details,timeline,comparison_panel,comparison_diff

SCENARIOS={'normal':'No failure','crash':'Agent crashes','heartbeat_loss':'Agent stops responding','timeout':'Agent takes too long',
           'invalid_output':'Invalid response','tool_failure':'Tool fails','backup_failure':'Backup also fails','shared_failure':'Same failure repeats',
           'expensive':'Rescue is too expensive','insufficient_budget':'Recovery budget runs out','no_backup':'No compatible backup','exhausted':'Attempts exhausted'}
POLICIES={'cost':'Cost','time':'Time','balanced':'Balanced'}


def workflow_label(workflows,identity):
    name=next(w['name'] for w in workflows if w['id']==identity)
    return name if identity.startswith('template-') else name+' · '+identity[:8]


def request_body(workflows):
    d=st.session_state.draft
    return {'prompt':d['prompt'],'workflow_id':d['workflow_id'],'agentbailout_enabled':d['protected'],
        'failure':{'scenario':d['scenario'] if d['fault_mode']=='Automatic at selected stage' else 'normal','stage_index':d['stage_index']},
        **{k:d[k] for k in ['optimization','task_budget','deadline_seconds','recovery_budget','max_attempts','stage_timeout']}}


def home(tasks,agents,workflows,providers):
    tested=st.session_state.get('connection_tests',{})
    st.caption('AI connections · '+' · '.join(PROVIDERS[p['provider']]+': '+('ready' if p['provider']=='offline' else 'verified connected' if p.get('verified_connection') else 'not configured' if p['status']=='unavailable' else 'configured, not tested') for p in providers))
    st.markdown('<div class="welcome"><span class="badge">WELCOME TO AGENTBAILOUT</span><h2>One failure. A way forward.</h2><p>Build an AI pipeline, simulate a failure, and see how intelligent recovery keeps your workflow running.</p></div>',unsafe_allow_html=True)
    a,b,c=st.columns(3)
    with a:
        if st.button('Start New Workflow',icon=':material/play_arrow:',type='primary',width='stretch'):
            st.session_state.current_task=None
            st.session_state.pop('run_signature',None)
            navigate('Run & Recover')
    with b:
        if st.button('Run Quick Demo',icon=':material/bolt:',width='stretch'):
            quick_demo()
    with c:
        if st.button('Build My Own Pipeline',icon=':material/account_tree:',width='stretch'):
            navigate('Build Pipeline')
    metrics=api('GET','/metrics')
    for col,(name,value) in zip(st.columns(4),[('Workflow executions',metrics.get('total_workflow_executions',len(tasks))),('Successful recoveries',metrics['successful_recoveries']),('Recovery success rate',f'{metrics["recovery_success_rate"]:.0%}'),('Average recovery time',f'{metrics["average_recovery_seconds"]:.2f}s')]):
        col.metric(name,value)
    left,right=st.columns([1.6,1])
    with left:
        st.subheader('How rescue works')
        preview([{'name':'Research','agent_id':'Find useful information'},{'name':'Formatter','agent_id':'A controlled failure here'},{'name':'Summary','agent_id':'Finish the original task'}])
        st.caption('Quick Demo uses offline simulation. Its result is computed only after you press Start Task.')
        st.subheader('Recent activity')
        if tasks:
            st.dataframe([{'Task':t['prompt'][:60],'Status':t['status'],'ID':t['id'][:8]} for t in tasks[:6]],hide_index=True,width='stretch')
        else:
            st.info('No runs yet. Try Quick Demo to see your first recovery.')
    with right:
        st.subheader('Recovery outcomes')
        values=[metrics['successful_recoveries'],max(0,metrics['failures_detected']-metrics['successful_recoveries'])]
        if sum(values):
            figure=go.Figure(go.Pie(labels=['Recovered','Other detected failures'],values=values,hole=.78,marker_colors=['#59dab6','#344776'],textinfo='none'))
            figure.update_layout(height=250,paper_bgcolor='rgba(0,0,0,0)',font_color='#c7d5ed',margin=dict(l=10,r=10,t=10,b=10),legend_orientation='h')
            st.plotly_chart(figure,width='stretch')
        else:
            st.info('Your recovery chart appears after a failure is detected.')
        st.caption('Other failures can include baseline and unfinished runs; this is not a forecast.')
        ready=[PROVIDERS[p['provider']] for p in providers if p['status']!='unavailable' and p['provider']!='offline']
        st.write('AI providers:',', '.join(ready)+' configured; test before use.' if ready else 'No real provider configured. Offline demo is ready.')


def builder(agents,workflows):
    contracts=api('GET','/contracts')
    pending=st.session_state.pop('builder_template_pending',None)
    if pending:
        st.session_state.draft['builder_template']=pending
        for key in list(st.session_state.draft):
            if key.startswith(('b_op_'+pending,'b_provider_'+pending,'b_agent_'+pending,'builder_count_'+pending,'builder_pool_'+pending)):
                del st.session_state.draft[key]
        for key in list(st.session_state):
            if key=='field_builder_template' or key.startswith(('field_b_op_'+pending,'field_b_provider_'+pending,'field_b_agent_'+pending,'field_builder_count_'+pending)):
                del st.session_state[key]
    st.caption('Choose → assign → protect → save. Everything you need is on this page.')
    st.subheader('Suggested templates')
    for col,identity,label in zip(st.columns(3),['research','coding','document'],['Research → Format → Summarize','Plan → Generate Code → Validate','Extract → Transform → Review']):
        with col:
            if st.button(label,key='load_template_'+identity,width='stretch'):
                st.session_state.builder_template_pending='template-'+identity
                st.rerun()
    st.markdown('<div class="step-label">1 / CHOOSE A TEMPLATE</div>',unsafe_allow_html=True)
    ids=[w['id'] for w in workflows]
    chosen=field('builder_template','Workflow template','select',options=ids,default='template-research',format_func=lambda x:workflow_label(workflows,x))
    template=next(w for w in workflows if w['id']==chosen)
    st.markdown('<div class="step-label">2–3 / SELECT AGENTS & PROVIDERS</div>',unsafe_allow_html=True)
    definitions=[]
    previous_contract='Task brief'
    previous_name='the task input'
    with st.expander('Change number or order of stages'):
        count=int(field('builder_count_'+chosen,'Number of stages','number',default=len(template['stages']),min_value=1,max_value=8))
    for i in range(count):
        initial=template['stages'][i] if i<len(template['stages']) else template['stages'][-1]
        with st.container(border=True):
            heading=st.empty()
            allowed=[op for op,contract in contracts.items() if contract['input']==previous_contract]
            if not allowed:
                st.info(f'This pipeline already ends with {previous_contract}. Keep {i} stages, or load another suggested template to start a different task.')
                break
            role_key=f'b_op_{chosen}_{i}'
            old_role=st.session_state.draft.get(role_key,initial['operation'])
            if old_role not in allowed:
                st.info(f'Step {i+1} “{contracts[old_role]["label"]}” cannot follow “{previous_name}”: it expects {contracts[old_role]["input"]}, but the previous output is {previous_contract}. Choose '+', '.join(contracts[o]['label'] for o in allowed)+'. A compatible default is selected below.')
            a,b,c=st.columns([1,1,1.5])
            with a:
                operation=field(role_key,'Role','select',options=allowed,default=initial['operation'],format_func=lambda x:contracts[x]['label'])
            heading.markdown(f'**{i+1:02d} · '+(initial['name'] if operation==initial['operation'] else contracts[operation]['label'])+'**')
            initial_agent=next((a for a in agents if a['id']==initial['agent_id'] and a['version']==initial['version']),None)
            with b:
                source=field(f'b_provider_{chosen}_{i}','Provider','select',options=list(PROVIDERS),default=initial_agent['provider'] if initial_agent else 'offline',format_func=PROVIDERS.get)
            eligible=[a for a in agents if operation in a['capabilities'] and a['provider']==source and a['available']]
            with c:
                refs=[a['id']+'@'+str(a['version']) for a in eligible]
                if refs:
                    ref=field(f'b_agent_{chosen}_{i}_{operation}_{source}','Primary agent','select',options=refs,default=initial['agent_id']+'@'+str(initial['version']),format_func=lambda x, rows=tuple(eligible):next(a['name']+' · '+a['model'] for a in rows if x==a['id']+'@'+str(a['version'])))
                    agent=next(a for a in eligible if ref==a['id']+'@'+str(a['version']))
                    st.caption(agent['provider_health']['status'].replace('_',' '))
                    definitions.append({'name':initial['name'] if operation==initial['operation'] else contracts[operation]['label'],'operation':operation,'agent_id':agent['id'],'version':agent['version']})
                else:
                    st.info('Add an agent for this provider and role below.')
            contract=contracts[operation]
            st.markdown(f'<div class="contract-row"><span>IN · {escape(contract["input"])}</span><span>OUT · {escape(contract["output"])}</span><span>CAPABILITY · {escape(contract["label"])}</span></div>',unsafe_allow_html=True)
            previous_contract,previous_name=contract['output'],contract['label']
    add_agent()
    st.markdown('<div class="step-label">4 / CHOOSE RECOVERY AGENTS</div>',unsafe_allow_html=True)
    st.caption('The engine checks capabilities, tools, contracts, availability, budget and deadline before using a backup.')
    pool_options=[a['id']+'@'+str(a['version']) for a in agents if a['available']]
    pool_key='builder_pool_'+chosen
    old=st.session_state.draft.get(pool_key,[r for r in pool_options if r.startswith('recovery-')])
    selected=st.multiselect('Recovery agents',pool_options,default=[r for r in old if r in pool_options],format_func=lambda x:next(a['name']+' · '+PROVIDERS[a['provider']] for a in agents if x==a['id']+'@'+str(a['version'])))
    st.session_state.draft[pool_key]=selected
    if definitions:
        preview(definitions)
    st.markdown('<div class="step-label">5 / SAVE & RUN</div>',unsafe_allow_html=True)
    name=field('workflow_name','Pipeline name',default='My protected pipeline')
    if st.button('Save Pipeline',icon=':material/save:',type='primary',disabled=len(definitions)!=count or not name.strip()):
        try:
            pool=[{'agent_id':r.rsplit('@',1)[0],'version':int(r.rsplit('@',1)[1])} for r in selected]
            saved=api('POST','/workflows',json={'name':name,'stages':definitions,'recovery_pool':pool})
            st.session_state.draft['workflow_id']=saved['id']
            st.session_state.saved_pools=st.session_state.get('saved_pools',{})
            st.session_state.saved_pools[saved['id']]=[{'agent_id':r.rsplit('@',1)[0],'version':int(r.rsplit('@',1)[1])} for r in selected]
            st.session_state.pop('field_workflow_id',None)
            st.session_state.current_task=None
            st.session_state.flash='Pipeline saved. Enter your task and press Start Task.'
            navigate('Run & Recover')
        except httpx.HTTPError as exc:
            friendly_error(exc)


def controls(workflows):
    ids=[w['id'] for w in workflows]
    a,b=st.columns([1,2])
    with a:
        selected=field('workflow_id','Saved pipeline','select',options=ids,format_func=lambda x:workflow_label(workflows,x))
    with b:
        field('prompt','What should the agents do?','text')
    stages=next(w['stages'] for w in workflows if w['id']==selected)
    a,b,c,d=st.columns([1.5,1,1,1])
    with a:
        field('scenario','Simulate Agent Failure','select',options=list(SCENARIOS),format_func=SCENARIOS.get,help='Controlled test failure, not a real provider outage.')
    with b:
        field('optimization','Recovery policy','select',options=list(POLICIES),format_func=POLICIES.get,help='Cost favors lower expected expense; Time favors speed; Balanced weighs both with reliability.')
    with c:
        field('task_budget','Task budget (simulated $)','number',min_value=1.0,max_value=100.0,step=.5,help='Simulated funding for stage payouts, rescue, reserve and refunds. This is not a real provider billing limit.')
    with d:
        field('deadline_seconds','Deadline (seconds)','number',min_value=1.0,max_value=600.0,step=5.0,help='Maximum elapsed task time. Work is cancelled and settled safely if time runs out.')
    with st.expander('Failure test options'):
        field('fault_mode','When should the failure happen?','radio',options=['Automatic at selected stage','Wait for manual injection'])
        field('stage_index','Which stage?','select',options=list(range(len(stages))),format_func=lambda x:f'{x+1}. {stages[x]["name"]}')
    field('protected','AgentBailout Protection','toggle',help='ON evaluates recovery. OFF stops at failure without advanced recovery.')
    return stages


def run_page(workflows):
    with st.expander('Configuration',expanded=not st.session_state.current_task):
        stages=controls(workflows)
    body=request_body(workflows)
    pool=st.session_state.get('saved_pools',{}).get(body['workflow_id'])
    if pool is not None:
        body['recovery_pool']=pool
    signature=json.dumps(body,sort_keys=True)
    identity=st.session_state.current_task
    task=api('GET','/tasks/'+identity) if identity else None
    active=bool(task and task['status'] in {'RUNNING','RESCUING','RESCUED'})
    same=signature==st.session_state.get('run_signature')
    if task and not same:
        st.info('These are new settings. Reset Demo to prepare another task; the current run keeps its saved settings.')
    a,b,c=st.columns(3)
    with a:
        if st.button('Start Task',icon=':material/play_arrow:',type='primary',width='stretch',disabled=active or bool(task and task['status']!='CREATED') or bool(task and not same)):
            try:
                if not identity:
                    task=api('POST','/tasks',json=body)
                    identity=task['id']
                    st.session_state.current_task=identity
                    st.session_state.run_signature=signature
                api('POST',f'/tasks/{identity}/start')
                st.rerun()
            except httpx.HTTPError as exc:
                friendly_error(exc)
    manual=st.session_state.draft['fault_mode']=='Wait for manual injection'
    pending=bool(task and st.session_state.draft['stage_index']<len(task['stages']) and task['stages'][st.session_state.draft['stage_index']]['status']=='PENDING')
    existing=api('GET',f'/tasks/{identity}/execution') if identity else None
    fault_saved=bool(existing and existing['configuration'] and existing['configuration']['failure']['scenario']!='normal')
    with b:
        if st.button('Inject Failure',icon=':material/bolt:',width='stretch',help='Manual test only: save one controlled fault before the chosen stage starts. Automatic tests already contain their fault.',disabled=not manual or st.session_state.draft['scenario']=='normal' or fault_saved or bool(task and not pending) or bool(task and task['status'] not in {'CREATED','RUNNING'})):
            try:
                if not identity:
                    created=api('POST','/tasks',json=body)
                    identity=created['id']
                    st.session_state.current_task=identity
                    st.session_state.run_signature=signature
                api('POST',f'/tasks/{identity}/inject-failure',json={'scenario':st.session_state.draft['scenario'],'stage_index':st.session_state.draft['stage_index']})
                st.session_state.flash='Failure saved. Press Start Task; it will trigger at the selected stage.'
                st.rerun()
            except httpx.HTTPError as exc:
                friendly_error(exc)
    with c:
        if st.button('Reset Demo',icon=':material/restart_alt:',width='stretch',disabled=active):
            st.session_state.current_task=None
            st.session_state.pop('run_signature',None)
            st.rerun()
    if manual:
        st.caption('Manual test: choose a failure and stage → Inject Failure to prepare it → Start Task. You can also inject into a pending stage during execution.')
    else:
        st.caption('Automatic test: Start Task saves your settings and triggers the selected test failure. No second injection is needed.')
    if task and task['status'] in {'COMPLETED','FAILED'}:
        st.caption('This run is finished. Use Reset Demo for another task; the recorded result remains in History.')
    @st.fragment(run_every=2)
    def live():
        identity=st.session_state.current_task
        if not identity:
            preview(stages)
            st.info('Ready when you are. Start Task runs this pipeline; no result has been generated yet.')
            return
        try:
            current=api('GET','/tasks/'+identity)
            run=api('GET',f'/tasks/{identity}/execution')
            events=api('GET',f'/tasks/{identity}/events')
        except httpx.HTTPError as exc:
            friendly_error(exc)
            return
        if task and current['status']!=task['status']:
            st.rerun(scope='app')
        demo_summary(run)
        st.subheader('Workflow')
        stage_schematic(run)
        final_output(run)
        stage_trace(run)
        failure_details(run)
        recovery_details(run)
        timeline(run)
        with st.expander('Technical raw response'):
            st.json(run)

    live()


def compare_page(workflows):
    st.caption('Same task. Same agent versions. Equivalent controlled failure. Two recorded outcomes.')
    with st.expander('Comparison settings',expanded=not st.session_state.current_comparison):
        controls(workflows)
    body=request_body(workflows)
    body['failure']['scenario']=st.session_state.draft['scenario']
    pool=st.session_state.get('saved_pools',{}).get(body['workflow_id'])
    if pool is not None:
        body['recovery_pool']=pool
    current=st.session_state.current_comparison
    pair=api('GET','/comparisons/'+current) if current else None
    busy=bool(pair and any(pair[k]['status'] not in {'COMPLETED','FAILED'} for k in ['baseline','protected']))
    if st.button('Compare With vs Without AgentBailout',type='primary',icon=':material/compare_arrows:',width='stretch',disabled=busy):
        try:
            pair=api('POST','/comparisons',json=body)
            st.session_state.current_comparison=pair['id']
            st.rerun()
        except httpx.HTTPError as exc:
            friendly_error(exc)
    @st.fragment(run_every=2)
    def live():
        identity=st.session_state.current_comparison
        if not identity:
            st.info('Choose a task and test failure, then compare. Both runs will execute for real.')
            return
        result=api('GET','/comparisons/'+identity)
        st.caption('Recorded comparison '+identity[:8]+' · task: '+result['baseline'].get('prompt','See execution trace')+' · changing the form does not change this saved result.')
        if busy and all(result[k]['status'] in {'COMPLETED','FAILED'} for k in ['baseline','protected']):
            st.rerun(scope='app')
        st.markdown('**Task prompt**')
        st.write(result['baseline']['prompt'])
        failed_names=[s['name'] for s in result['baseline']['stages'] if any(a['status']=='FAILED' and not a['recovery'] for a in s['attempts'])]
        st.info(('Failure point: '+', '.join(failed_names)+'. ' if failed_names else 'No primary failure recorded yet. ')+f'Without rescue: {result["baseline"]["status"].lower()}. With rescue: {result["protected"]["status"].lower()} after {result["protected"]["recovery_attempts"]} replacement attempt(s).')
        left,right=st.columns(2)
        with left:
            comparison_panel(result['baseline'],'Without AgentBailout')
        with right:
            comparison_panel(result['protected'],'With AgentBailout')
        comparison_diff(result)
        with st.expander('Technical raw response'):
            st.json(result)

    live()


def settings(tasks,agents,providers):
    provider_tab,recovery_tab,history_tab,ledger_tab=st.tabs(['AI Providers','Recovery Settings','History','Ledger & Analytics'])
    with provider_tab:
        st.caption('Keys stay in the backend environment. A configured key is not proof of a working connection.')
        for row in providers:
            with st.container(border=True):
                a,b,c=st.columns([1,2,1])
                with a:
                    st.write(PROVIDERS[row['provider']])
                    st.caption(('not configured' if row.get('configuration_status')=='not_configured' and row['status']=='unavailable' else row['status'].replace('_',' ')))
                    if row.get('last_success_at'): st.caption('Last successful test: '+row['last_success_at'])
                    if row.get('verified_model'): st.caption('Tested model: '+row['verified_model'])
                    if row.get('error'): st.warning(row['error'])
                with b:
                    if row['provider']!='offline' and st.button('Discover models',key='discover_'+row['provider']):
                        try:
                            found=api('GET','/providers/'+row['provider']+'/models')
                            st.session_state['models_'+row['provider']]=found['models']
                        except httpx.HTTPError as exc: friendly_error(exc)
                    discovered=st.session_state.get('models_'+row['provider'],row.get('available_models',[]))
                    if discovered:
                        selected=st.selectbox('Available models',discovered,key='discovered_'+row['provider'])
                        if st.button('Use selected model',key='use_model_'+row['provider']):
                            st.session_state['provider_model_'+row['provider']]=selected
                    model=st.text_input('Model to test',value=row['model'],key='provider_model_'+row['provider'])
                with c:
                    if st.button('Test Provider',key='test_'+row['provider']):
                        try:
                            response=api('POST','/providers/test',json={'provider':row['provider'],'model':model})
                            st.session_state.connection_tests={**st.session_state.get('connection_tests',{}),row['provider']:response}
                            st.success(response['message'])
                            st.rerun()
                        except httpx.HTTPError as exc:
                            st.session_state.connection_tests={**st.session_state.get('connection_tests',{}),row['provider']:{'connected':False}}
                            friendly_error(exc)
        st.caption('Set OPENAI_API_KEY / GEMINI_API_KEY (or GOOGLE_API_KEY) / ANTHROPIC_API_KEY and an accessible model identifier, or run Ollama and install a model. No keys are entered into agent instructions.')
    with recovery_tab:
        st.write('Defaults for new tasks; existing runs keep their saved policy.')
        field('max_attempts','Maximum recovery attempts','number',min_value=1,max_value=3)
        field('recovery_budget','Maximum recovery spend (simulated $)','number',min_value=0.0,max_value=4.0,step=.05)
        field('stage_timeout','Per-agent runtime limit (seconds)','number',min_value=.1,max_value=120.0)
        field('optimization','Default optimization strategy','select',options=list(POLICIES),format_func=POLICIES.get)
        field('deadline_seconds','Task deadline (seconds)','number',min_value=1.0,max_value=600.0)
        with st.expander('Code & repository diagnostic tools'):
            from dashboard.diagnostic_view import render_diagnostics
            render_diagnostics()
    with history_tab:
        if tasks:
            st.dataframe([{'Task':t['prompt'],'Status':t['status'],'ID':t['id']} for t in tasks],hide_index=True,width='stretch')
            chosen=st.selectbox('Inspect a task',[t['id'] for t in tasks],format_func=lambda x:x[:8]+' · '+next(t['status'] for t in tasks if t['id']==x))
            run=api('GET',f'/tasks/{chosen}/execution')
            st.dataframe(run['attempts'],hide_index=True,width='stretch')
            with st.expander('Task and failure details'):
                st.json(run)
        else:
            st.info('Past tasks and attempts appear after your first run.')
        with st.expander('Previous code repairs and repository inspections'):
            st.json(api('GET','/diagnostics'))
    with ledger_tab:
        metrics=api('GET','/metrics')
        st.metric('Total simulated recovery expense','$'+metrics['total_simulated_rescue_cost'])
        if tasks:
            chosen=st.selectbox('Ledger task',[t['id'] for t in tasks],format_func=lambda x:x[:8])
            ledger=api('GET',f'/tasks/{chosen}/ledger')
            st.write('Settled:',ledger['settled'],'· Balanced:',ledger['balanced'])
            positive={k:float(v) for k,v in ledger['balances'].items() if k not in {'client','escrow'} and float(v)>0}
            if positive:
                fig=go.Figure(go.Bar(x=list(positive),y=list(positive.values()),marker_color='#658bff'))
                fig.update_layout(height=250,paper_bgcolor='rgba(0,0,0,0)',plot_bgcolor='rgba(0,0,0,0)',font_color='#b8caeb',yaxis_title='Simulated dollars',margin=dict(l=20,r=20,t=15,b=20))
                st.plotly_chart(fig,width='stretch')
            st.dataframe(ledger['entries'],hide_index=True,width='stretch')
        st.caption('These are simulated allocations. External model API costs remain separate and unknown without verified pricing.')
