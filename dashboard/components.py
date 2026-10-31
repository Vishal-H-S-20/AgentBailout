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
        cards.append(f'<div class="node {style}"><small>STAGE {i+1:02d} · {label}</small><strong>{escape(s["name"])}</strong><small>{escape(s["worker_id"][:26])}</small></div>')
    st.markdown('<div class="nodegrid">'+''.join(cards)+'</div>',unsafe_allow_html=True)
