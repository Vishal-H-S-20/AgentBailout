"""Live dashboard comparison and workflow configuration verification."""
from pathlib import Path
import time
import httpx
from streamlit.testing.v1 import AppTest

app=AppTest.from_file(str(Path(__file__).resolve().parents[1]/'dashboard'/'app.py'),default_timeout=30).run()
assert not app.exception
def widget(elements,label):
    return next(e for e in elements if e.label==label)

widget(app.radio,'Workspace').set_value('Workflow Builder').run()
widget(app.selectbox,'Workflow template').select('template-coding').run()
assert not app.exception
widget(app.button,'Save workflow').click().run()
assert app.success and not app.exception
widget(app.radio,'Workspace').set_value('Agent Registry').run()
assert not app.exception
assert any(f.label=='Register new version' for f in app.button)
widget(app.radio,'Workspace').set_value('Comparison Lab').run()
widget(app.selectbox,'Failure scenario').select('crash').run()
widget(app.button,'Compare both').click().run()
assert not app.exception
comparison_id=widget(app.selectbox,'Comparison history').value
deadline=time.monotonic()+15
while time.monotonic()<deadline:
    pair=httpx.get('http://127.0.0.1:8003/comparisons/'+comparison_id).json()
    if all(pair[k]['execution_seconds'] is not None for k in ['baseline','protected']):
        break
    time.sleep(.1)
app.run()
assert not app.exception
assert pair['baseline']['status']=='FAILED'
assert pair['protected']['status']=='COMPLETED'
assert all(pair[k]['ledger']['balanced'] and pair[k]['ledger']['settled'] for k in ['baseline','protected'])
assert {m.value for m in app.metric if m.label=='Status'}=={'COMPLETED','FAILED'}
print('PHASE 4 DASHBOARD VERIFIED:',comparison_id,'baseline FAILED; protected COMPLETED; both settled')
