from html import escape
import httpx
import streamlit as st


def friendly_error(exc: httpx.HTTPError) -> None:
    technical = str(exc)
    message = 'The backend could not be reached. Check that it is running, then try again.'
    if isinstance(exc,httpx.HTTPStatusError):
        try:
            detail=exc.response.json().get('detail','Request rejected')
        except ValueError:
            detail=exc.response.text
        message=detail.get('message','Request rejected') if isinstance(detail,dict) else ('Please check the form: '+'; '.join(str(e.get('msg','Invalid value')) for e in detail)) if isinstance(detail,list) else str(detail)
        technical=f'{exc.request.method} {exc.request.url}\nHTTP {exc.response.status_code}\n{exc.response.text}'
    st.error(message)
    with st.expander('Technical response'):
        st.code(technical,language='text')


def pipeline(stages: list[dict]) -> None:
    cards=[]
    for i,s in enumerate(stages):
        state=s['status']
        style='done' if state=='COMPLETED' else 'failed' if state=='FAILED' else 'active' if state=='RUNNING' else ''
        label='RECOVERED' if s['recovery_attempts'] and state=='COMPLETED' else state
        if i:
            cards.append('<div class="arrow">→</div>')
        symbol='✓' if state=='COMPLETED' else '!' if state=='FAILED' else '◉' if state=='RUNNING' else str(i+1)
        cards.append(f'<div class="node {style}"><span class="node-icon">{symbol}</span><small>STEP {i+1:02d} · {label}</small><strong>{escape(s["name"])}</strong><small>{escape(s["worker_id"][:26])}</small></div>')
    st.markdown('<div class="nodegrid">'+''.join(cards)+'</div>',unsafe_allow_html=True)


def preview(definitions: list[dict]):
    pipeline([{'name':s['name'],'status':'PENDING','worker_id':s.get('agent_id','Choose an agent'),'recovery_attempts':0} for s in definitions])


def recovery_story(events: list[dict]):
    kinds={e['type'] for e in events}
    steps=[('!','Failure','FAILURE_DETECTED'),('⌕','Check options','RECOVERY_CANDIDATES'),
           ('$','Worth rescuing?','RESCUE_APPROVED'),('⇄','Replace','BACKUP_STARTED'),('✓','Continue','WORKFLOW_RESUMED')]
    cards=[]
    for symbol,label,event in steps:
        style='failed' if event=='FAILURE_DETECTED' and event in kinds else 'done' if event in kinds else ''
        cards.append(f'<div class="story-step {style}"><span>{symbol}</span><small>{label}</small></div>')
    st.markdown('<div class="story">'+'<span class="arrow">→</span>'.join(cards)+'</div>',unsafe_allow_html=True)
