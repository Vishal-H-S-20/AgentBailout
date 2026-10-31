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
st.caption('Autonomous Recovery & Liquidity Layer · All financial amounts are simulations')
try:
    tasks = api('GET', '/tasks')
except httpx.HTTPError as exc:
    st.error(f'Backend unavailable at {BASE}: {exc}')
    st.stop()

with st.sidebar:
    st.header('Task control')
    prompt = st.text_area('Task', 'Plan a community garden with a measurable pilot')
    scenario = st.selectbox('Failure scenario', ['normal','crash','heartbeat_loss','backup_failure','expensive','no_backup'])
    if st.button('Create task', type='primary'):
        try:
            task = api('POST', '/tasks', json={'prompt':prompt})
            st.session_state.selected = task['id']
            if scenario != 'normal':
                api('POST', f"/tasks/{task['id']}/inject-failure", json={'scenario':scenario})
            st.rerun()
        except httpx.HTTPError as exc:
            st.error(str(exc))
    ids = [t['id'] for t in tasks]
    if not ids:
        st.info('Create a task to begin.')
        st.stop()
    selected = st.session_state.get('selected', ids[0])
    task_id = st.selectbox('Task history', ids, index=ids.index(selected) if selected in ids else 0)
    if st.button('Start task'):
        try:
            api('POST', f'/tasks/{task_id}/start')
        except httpx.HTTPError as exc:
            st.error(str(exc))
    if st.button('Inject failure', disabled=scenario == 'normal'):
        try:
            api('POST', f'/tasks/{task_id}/inject-failure', json={'scenario':scenario})
        except httpx.HTTPError as exc:
            st.error(str(exc))
    if st.button('Reset demo selection'):
        st.session_state.pop('selected', None)
        st.rerun()
    auto = st.toggle('Auto refresh', value=True)
    st.button('Refresh')


@st.fragment(run_every=1 if auto else None)
def live():
    try:
        task = api('GET', f'/tasks/{task_id}')
        events = api('GET', f'/tasks/{task_id}/events')
        ledger = api('GET', f'/tasks/{task_id}/ledger')
        metrics = api('GET', '/metrics')
    except httpx.HTTPError as exc:
        st.error(str(exc))
        return
    st.subheader(f"Workflow · {task['status']}")
    colors = {'COMPLETED':'🟢','RUNNING':'🔵','FAILED':'🔴','PENDING':'⚪'}
    columns = st.columns(3)
    for col, stage in zip(columns, task['stages']):
        col.metric(f"{colors.get(stage['status'],'🟡')} {stage['name']}", stage['status'])
    st.caption('Research → Formatter → Synthesis · Failure → Economic policy → Backup Formatter → Synthesis')
    st.graphviz_chart('digraph { rankdir=LR; bgcolor="transparent"; node [style=filled,fillcolor="#24344f",fontcolor=white]; Research -> Formatter -> Synthesis; Formatter -> "Economic policy" [label="failure",color=red]; "Economic policy" -> "Backup Formatter" [label="approve",color=green]; "Backup Formatter" -> Synthesis [color=green]; }')
    if any(s['recovery_attempts'] for s in task['stages']):
        st.info('Backup Formatter activated · preserved research input reused')
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
        st.write(task['result']['summary'])
        st.success(task['result']['recommendation'])
    if task['error']:
        st.error(task['error'])


live()

