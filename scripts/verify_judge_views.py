"""Live UI acceptance for contract guidance, code output, traces and richer comparison."""
from pathlib import Path
import time
import httpx
from streamlit.testing.v1 import AppTest

app=AppTest.from_file(str(Path(__file__).resolve().parents[1]/'dashboard'/'app.py'),default_timeout=30).run()
def widget(items,label):
    return next(e for e in items if e.label==label)
def page(name):
    widget(app.radio,'Navigation').set_value(name).run()
    assert not app.exception
def wait(identity):
    end=time.monotonic()+15
    while time.monotonic()<end:
        result=httpx.get(f'http://127.0.0.1:8003/tasks/{identity}/execution').json()
        if result['execution_seconds'] is not None:
            app.run()
            assert not app.exception
            return result
        time.sleep(.1)
    raise AssertionError('Completion deadline exceeded')

page('Build Pipeline')
roles=[s for s in app.selectbox if s.label=='Role']
assert roles[1].options==['Format'] and roles[2].options==['Summarize']
widget(app.number_input,'Number of stages').set_value(4).run()
assert widget(app.button,'Save Pipeline').disabled
assert any('already ends' in e.value for e in app.info)
for template,label,expected in [('document','Extract → Transform → Review',['extract','transform','review']),('coding','Plan → Generate Code → Validate',['plan','code','validate'])]:
    widget(app.button,label).click().run()
    assert not app.exception
    assert [s.value for s in app.selectbox if s.label=='Role']==expected
    assert any('IN ·' in e.value and 'OUT ·' in e.value for e in app.markdown)
widget(app.button,'Save Pipeline').click().run()
saved_id=app.session_state['draft']['workflow_id']
widget(app.selectbox,'Simulate Agent Failure').select('crash').run()
assert app.session_state['draft']['workflow_id']==saved_id
widget(app.button,'Start Task').click().run()
report=wait(app.session_state['current_task'])
assert report['status']=='COMPLETED' and report['recovery_attempts']==1
assert any('def normalize_text' in code.value and code.language=='python' for code in app.code)
assert any('Validation result' in e.value for e in app.markdown)
assert any('Primary result' in e.value and 'No response returned' in e.value for e in app.markdown)
assert any(e.value=='Agent input/output trace' for e in app.subheader)
assert any(e.value=='What failed?' for e in app.subheader)
assert any(e.value=='What did AgentBailout do?' for e in app.subheader)
assert any(e.label=='Technical raw response' for e in app.expander)
assert widget(app.button,'Start Task').disabled
page('Compare Results')
widget(app.button,'Compare With vs Without AgentBailout').click().run()
identity=app.session_state['current_comparison']
end=time.monotonic()+15
while time.monotonic()<end:
    pair=httpx.get('http://127.0.0.1:8003/comparisons/'+identity).json()
    if all(pair[key]['execution_seconds'] is not None for key in ['baseline','protected']):
        break
    time.sleep(.1)
app.run()
assert not app.exception
assert pair['baseline']['status']=='FAILED' and pair['protected']['status']=='COMPLETED'
assert any(e.value=='What changed?' for e in app.subheader)
assert any('compatible replacement' in e.value for e in app.markdown)
assert any('No response was returned' in str(e.value) for e in app.markdown)
assert any(e.label=='Technical raw response' for e in app.expander)
print('JUDGE VIEWS VERIFIED: guided compatible roles; terminal-chain guard; templates; actual failure/recovery traces; readable Python output; side-by-side stage evidence and diff. Comparison:',identity)
