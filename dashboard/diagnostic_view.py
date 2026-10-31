import streamlit as st
import httpx
from dashboard.client import api
from dashboard.components import friendly_error

def render_diagnostics():
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
