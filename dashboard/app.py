"""Five-page interface; execution and financial state remain owned by FastAPI."""
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from html import escape
import httpx
import streamlit as st
from dashboard.client import api
from dashboard.components import friendly_error
from dashboard.styles import CSS
from dashboard.state import initialize,PAGES,navigate
from dashboard.pages import home,builder,run_page,compare_page,settings

st.set_page_config(page_title='AgentBailout',page_icon='🛟',layout='wide')
initialize()
st.markdown(CSS,unsafe_allow_html=True)
with st.sidebar:
    st.markdown('<div class="brand"><span>◈</span> AgentBailout</div>',unsafe_allow_html=True)
    st.caption('Detect. Diagnose. Decide.\nRepair. Replace. Recover.')
    icons={'Home':'⌂','Build Pipeline':'◫','Run & Recover':'▷','Compare Results':'⇄','Settings & History':'⚙'}
    page=st.radio('Navigation',PAGES,key='page',format_func=lambda x:icons[x]+'  '+x)
    st.divider()
    if page!='Run & Recover' and st.button('Go to Run & Recover',icon=':material/play_arrow:',width='stretch'):
        navigate('Run & Recover')
    st.caption('Offline simulation is always available. Real providers use your configured connections.')
try:
    health=api('GET','/health')
    tasks=api('GET','/tasks')
    agents=api('GET','/agents')
    workflows=api('GET','/workflows')
    providers=api('GET','/providers')
except httpx.HTTPError as exc:
    st.title('AgentBailout')
    friendly_error(exc)
    st.info('Start the backend on port 8003, then refresh this page.')
    st.stop()
workflow=next((w for w in workflows if w['id']==st.session_state.draft['workflow_id']),workflows[0])
st.markdown(f'<div class="eyebrow">AgentBailout / {escape(page)}</div>',unsafe_allow_html=True)
st.title(page)
st.markdown(f'<div class="statusline">● Backend {escape(health["status"])} &nbsp; / &nbsp; Pipeline: {escape(workflow["name"])} &nbsp; / &nbsp; Offline demo ready</div>',unsafe_allow_html=True)
selected_providers={a['provider'] for s in workflow['stages'] for a in agents if a['id']==s['agent_id'] and a['version']==s['version']}
st.caption('Pipeline mode: Offline simulation' if selected_providers=={'offline'} else 'Pipeline providers: '+', '.join(sorted(selected_providers))+' · real models require a tested connection')
if st.session_state.get('flash'):
    st.success(st.session_state.pop('flash'))
try:
    if page=='Home':
        home(tasks,agents,workflows,providers)
    elif page=='Build Pipeline':
        builder(agents,workflows)
    elif page=='Run & Recover':
        run_page(workflows)
    elif page=='Compare Results':
        compare_page(workflows)
    else:
        settings(tasks,agents,providers)
except httpx.HTTPError as exc:
    friendly_error(exc)
