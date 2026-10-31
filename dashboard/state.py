import streamlit as st

PAGES=['Home','Build Pipeline','Run & Recover','Compare Results','Settings & History']
DEFAULTS={'workflow_id':'template-research','prompt':'Plan a community garden with a measurable pilot',
          'scenario':'normal','stage_index':1,'protected':True,'optimization':'cost','task_budget':5.0,
          'deadline_seconds':120.0,'recovery_budget':1.0,'max_attempts':1,'stage_timeout':10.0,
          'fault_mode':'Automatic at selected stage'}


def initialize():
    st.session_state.setdefault('draft',dict(DEFAULTS))
    st.session_state.setdefault('current_task',None)
    st.session_state.setdefault('current_comparison',None)
    if 'next_page' in st.session_state:
        st.session_state.page=st.session_state.pop('next_page')
    if st.session_state.get('page') not in PAGES:
        st.session_state.page='Home'


def navigate(page: str):
    st.session_state.next_page=page
    st.rerun()


def field(name: str,label: str,kind: str='text',**kwargs):
    """Model state survives Streamlit removing widgets from an inactive page."""
    values=st.session_state.draft
    default=kwargs.pop('default',DEFAULTS.get(name))
    key='field_'+name
    options=kwargs.get('options')
    value=values.get(name,default)
    if options is not None and value not in options:
        value=default if default in options else options[0] if options else None
    if key not in st.session_state or options is not None and st.session_state[key] not in options:
        st.session_state[key]=value
    functions={'text':st.text_input,'area':st.text_area,'select':st.selectbox,'number':st.number_input,'toggle':st.toggle,'radio':st.radio}
    result=functions[kind](label,key=key,**kwargs)
    values[name]=result
    return result


def quick_demo():
    st.session_state.draft.update(DEFAULTS)
    st.session_state.draft['scenario']='crash'
    for key in list(st.session_state):
        if key.startswith('field_'):
            del st.session_state[key]
    st.session_state.current_task=None
    st.session_state.pop('run_signature',None)
    st.session_state.flash='Quick Demo is ready: offline agents, a stage-two crash, and protection ON. Press Start Task.'
    navigate('Run & Recover')
