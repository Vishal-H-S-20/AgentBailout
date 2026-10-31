"""Reproduce task-selection and injection responses through real widgets/API."""
from pathlib import Path
import httpx
from streamlit.testing.v1 import AppTest

app=AppTest.from_file(str(Path(__file__).resolve().parents[1]/'dashboard'/'app.py'),default_timeout=30).run()
def widget(elements,label):
    return next(e for e in elements if e.label==label)
for scenario in ['normal','crash','crash']:
    widget(app.selectbox,'Failure scenario').select(scenario).run()
    widget(app.button,'Create task').click().run()
    selected=widget(app.selectbox,'Task history').value
    stored=app.session_state['selected']
    run=httpx.get(f'http://127.0.0.1:8003/tasks/{selected}/execution').json()
    print('SELECTED',selected,'CREATED',stored,'SCENARIO',run['configuration']['failure'],flush=True)
    response=httpx.post(f'http://127.0.0.1:8003/tasks/{selected}/inject-failure',json={'scenario':'crash','stage_index':1})
    print('INJECT RESPONSE',response.status_code,response.text,flush=True)
