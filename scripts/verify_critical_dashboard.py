from pathlib import Path
import time
import httpx
from streamlit.testing.v1 import AppTest

app=AppTest.from_file(str(Path(__file__).resolve().parents[1]/'dashboard'/'app.py'),default_timeout=30).run()
def widget(items,label):
    return next(x for x in items if x.label==label)
def report():
    identity=widget(app.selectbox,'Task history').value
    return httpx.get(f'http://127.0.0.1:8003/tasks/{identity}/execution').json()
def completed():
    end=time.monotonic()+10
    while time.monotonic()<end:
        run=report()
        if run['status'] in {'COMPLETED','FAILED'} and run['execution_seconds'] is not None:
            app.run()
            assert not app.exception
            return run
        time.sleep(.1)
    raise AssertionError('Completion deadline exceeded')

widget(app.button,'Create & select task').click().run()
normal=report()
assert normal['configuration']['failure']['scenario']=='normal'
widget(app.selectbox,'Failure scenario').select('crash').run()
assert widget(app.button,'Start selected task').disabled
assert report()['task_id']==normal['task_id']
widget(app.button,'Create & select task').click().run()
crash=report()
assert crash['task_id']!=normal['task_id']
assert crash['task_id']==app.session_state['selected']
assert crash['configuration']['failure']=={'scenario':'crash','stage_index':1}
widget(app.button,'Start selected task').click().run()
assert completed()['recovery_attempts']==1
assert widget(app.button,'Inject failure').disabled
widget(app.radio,'Injection mode').set_value('Manual injection').run()
widget(app.button,'Create & select task').click().run()
manual=report()
assert manual['configuration']['failure']['scenario']=='normal'
widget(app.selectbox,'Manual fault stage').select(1).run()
widget(app.button,'Inject failure').click().run()
assert report()['configuration']['failure']=={'scenario':'crash','stage_index':1}
assert widget(app.button,'Inject failure').disabled
widget(app.button,'Start selected task').click().run()
assert completed()['recovery_attempts']==1
widget(app.radio,'Workspace').set_value('Overview').run()
assert not app.exception and app.metric
widget(app.radio,'Workspace').set_value('Code Recovery').run()
widget(app.button,'Run diagnostic').click().run()
assert not app.exception and app.session_state['diagnostic']['status']=='RECOVERED'
widget(app.text_input,'Numeric input').set_value('0.1234567890123456789').run()
widget(app.button,'Run diagnostic').click().run()
assert app.session_state['diagnostic']['status']=='FAILED'
assert any('did not pass result validation' in e.value for e in app.error)
assert not any('Re-executed successfully' in e.value for e in app.success)
print('CRITICAL UI VERIFIED: draft mismatch blocked; automatic/manual crashes rescued; exact new UUIDs selected; terminal/duplicate actions disabled; overview and real Python normalization rendered.')
