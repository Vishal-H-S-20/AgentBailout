"""Exercise the five-page UI through real Streamlit callbacks and HTTP state."""
from pathlib import Path
import time
import httpx
from streamlit.testing.v1 import AppTest

app=AppTest.from_file(str(Path(__file__).resolve().parents[1]/'dashboard'/'app.py'),default_timeout=30).run()
def widget(items,label):
    return next(e for e in items if e.label==label)
def page(value):
    widget(app.radio,'Navigation').set_value(value).run()
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
    raise AssertionError('Workflow did not finish')

assert not app.exception
assert widget(app.radio,'Navigation').options==['⌂  Home','◫  Build Pipeline','▷  Run & Recover','⇄  Compare Results','⚙  Settings & History']
page('Settings & History')
widget(app.number_input,'Maximum recovery spend (simulated $)').set_value(0.0).run()
page('Home')
widget(app.button,'Run Quick Demo').click().run()
assert not app.exception and app.session_state['page']=='Run & Recover'
assert app.session_state['current_task'] is None
assert widget(app.selectbox,'Simulate Agent Failure').value=='crash'
assert app.session_state['draft']['recovery_budget']==1.0
widget(app.button,'Start Task').click().run()
identity=app.session_state['current_task']
run=wait(identity)
assert run['status']=='COMPLETED' and run['recovery_attempts']==1
assert run['ledger']['balanced'] and run['ledger']['settled']
assert widget(app.button,'Start Task').disabled
widget(app.button,'Reset Demo').click().run()
widget(app.toggle,'AgentBailout Protection').set_value(False).run()
widget(app.button,'Start Task').click().run()
run=wait(app.session_state['current_task'])
assert run['status']=='FAILED' and run['recovery_attempts']==0
widget(app.button,'Reset Demo').click().run()
widget(app.toggle,'AgentBailout Protection').set_value(True).run()
widget(app.radio,'When should the failure happen?').set_value('Wait for manual injection').run()
widget(app.button,'Inject Failure').click().run()
manual_id=app.session_state['current_task']
assert httpx.get(f'http://127.0.0.1:8003/tasks/{manual_id}').json()['status']=='CREATED'
widget(app.button,'Start Task').click().run()
assert wait(manual_id)['recovery_attempts']==1
page('Build Pipeline')
widget(app.radio,'Pipeline type').set_value('Guided offline templates').run()
widget(app.button,'Add New Agent').click().run()
provider_form=next(e for e in app.selectbox if e.key=='new_agent_provider')
assert provider_form.options==['Offline simulation','GPT / OpenAI','Claude','Groq','Gemini','Ollama (local)']
widget(app.text_input,'Agent name').set_value('Verified local agent').run()
widget(app.button,'Test Connection').click().run()
assert any('Offline simulation is ready' in e.value for e in app.success)
widget(app.button,'Save Agent').click().run()
assert not app.exception
widget(app.button,'Save Pipeline').click().run()
assert not app.exception and app.session_state['page']=='Run & Recover'
assert app.session_state['draft']['workflow_id'].startswith('template-') is False
widget(app.text_area,'What should the agents do?').set_value('Preserve this task across every page').run()
widget(app.selectbox,'Recovery policy').select('time').run()
page('Home')
page('Run & Recover')
assert widget(app.text_area,'What should the agents do?').value=='Preserve this task across every page'
assert widget(app.selectbox,'Recovery policy').value=='time'
page('Compare Results')
widget(app.button,'Compare With vs Without AgentBailout').click().run()
comparison=app.session_state['current_comparison']
end=time.monotonic()+15
while time.monotonic()<end:
    pair=httpx.get('http://127.0.0.1:8003/comparisons/'+comparison).json()
    if all(pair[k]['execution_seconds'] is not None for k in ['baseline','protected']):
        break
    time.sleep(.1)
app.run()
assert not app.exception
assert pair['baseline']['status']=='FAILED' and pair['protected']['status']=='COMPLETED'
page('Settings & History')
assert {t.label for t in app.tabs}=={'AI Providers','Recovery Settings','History','Ledger & Analytics'}
assert not app.exception
widget(app.button,'Run diagnostic').click().run()
assert app.session_state['diagnostic']['status']=='RECOVERED'
widget(app.text_input,'Numeric input').set_value('0.1234567890123456789').run()
widget(app.button,'Run diagnostic').click().run()
assert app.session_state['diagnostic']['status']=='FAILED'
assert any('did not pass result validation' in e.value for e in app.error)
page('Home')
print('FIVE-PAGE UI VERIFIED: navigation, quick demo, real protected/baseline/manual runs, builder save, persistent inputs, comparison, settings/history/ledger.')
