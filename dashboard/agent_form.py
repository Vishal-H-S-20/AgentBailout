import uuid
import httpx
import streamlit as st
from dashboard.client import api
from dashboard.components import friendly_error

PROVIDERS={'offline':'Offline simulation','openai':'GPT / OpenAI','anthropic':'Claude', 'groq':'Groq','gemini':'Gemini','ollama':'Ollama (local)'}
OPERATIONS=['research','format','summarize','plan','code','validate','extract','transform','review']


def add_agent():
    if st.button('Add New Agent',icon=':material/person_add:'):
        st.session_state.agent_form_open=not st.session_state.get('agent_form_open',False)
    if not st.session_state.get('agent_form_open'):
        return
    with st.container(border=True):
        st.subheader('Add an agent')
        name=st.text_input('Agent name',key='new_agent_name')
        left,right=st.columns(2)
        with left:
            source=st.selectbox('Provider',list(PROVIDERS),format_func=PROVIDERS.get,key='new_agent_provider')
        with right:
            model=st.text_input('Model',value='deterministic-v1' if source=='offline' else '',key='new_agent_model_'+source,help='Use a model available in your account or installed in Ollama.')
        role=st.selectbox('Role',OPERATIONS,key='new_agent_role')
        caps=st.multiselect('Capabilities',OPERATIONS,default=[role],key='new_agent_capabilities_'+role)
        instructions=st.text_area('Instructions','Perform the assigned stage and return its declared JSON output.',key='new_agent_instructions')
        st.caption('Credentials stay in the backend environment. Test Connection makes a small real model call when using a configured provider.')
        a,b=st.columns(2)
        with a:
            if st.button('Test Connection',key='agent_connection'):
                try:
                    result=api('POST','/providers/test',json={'provider':source,'model':model})
                    st.session_state.connection_tests={**st.session_state.get('connection_tests',{}),source:result}
                    st.success(result['message'])
                except httpx.HTTPError as exc:
                    st.session_state.connection_tests={**st.session_state.get('connection_tests',{}),source:{'connected':False}}
                    friendly_error(exc)
        with b:
            if st.button('Save Agent',type='primary',disabled=not name.strip() or not model.strip() or not caps):
                try:
                    row=api('POST','/agents',json={'id':'agent-'+uuid.uuid4().hex[:12],'name':name,'provider':source,'model':model,'capabilities':caps,'system_instructions':instructions})
                    st.session_state.flash=f'{row["name"]} added · {row["provider_health"]["status"].replace("_"," ")}. Configure and test the provider before a real run.'
                    st.session_state.agent_form_open=False
                    st.rerun()
                except httpx.HTTPError as exc:
                    friendly_error(exc)
