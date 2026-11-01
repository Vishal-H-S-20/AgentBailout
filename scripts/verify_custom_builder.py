"""Live custom editor acceptance. Saves drafts without making paid model calls."""
from pathlib import Path
import httpx
from streamlit.testing.v1 import AppTest

app=AppTest.from_file(str(Path(__file__).resolve().parents[1]/'dashboard'/'app.py'),default_timeout=30).run()
def widget(items,label): return next(e for e in items if e.label==label)
def page(name):
 widget(app.radio,'Navigation').set_value(name).run()
 assert not app.exception
page('Build Pipeline')
assert widget(app.radio,'Pipeline type').value=='Custom AI pipeline'
assert len([x for x in app.text_input if x.label=='Stage name'])==3
for count in [1,2,5,10,3]:
 widget(app.number_input,'Number of stages').set_value(count).run()
 assert not app.exception
 assert len([x for x in app.text_input if x.label=='Stage name'])==count
 assert len(app.session_state['custom_stages'])==count
names=[x for x in app.text_input if x.label=='Stage name']
names[0].set_value('Detailed planner').run()
objectives=[x for x in app.text_area if x.label=='Stage objective']
objectives[0].set_value('Create a detailed plan').run()
first=app.session_state['custom_stages'][0]['id']
app.button(key='duplicate'+first).click().run()
assert len(app.session_state['custom_stages'])==4 and widget(app.number_input,'Number of stages').value==4
copy=app.session_state['custom_stages'][1]['id']
assert copy!=first and app.session_state['custom_stages'][1]['objective']=='Create a detailed plan'
app.button(key='up'+copy).click().run()
assert app.session_state['custom_stages'][0]['id']==copy
app.button(key='remove'+copy).click().run()
assert len(app.session_state['custom_stages'])==3
models=[x for x in app.text_input if x.label=='Model ID']
models[0].set_value('explicit-openai-model').run()
providers=[x for x in app.selectbox if x.label=='Provider']
providers[0].set_value('groq').run()
assert [x for x in app.text_input if x.label=='Model ID'][0].value==''
assert app.session_state['custom_stages'][0]['objective']=='Create a detailed plan'
for i in range(3):
 [x for x in app.text_area if x.label=='Stage objective'][i].set_value('Custom objective '+str(i)).run()
 [x for x in app.text_input if x.label=='Model ID'][i].set_value('explicit-model-'+str(i)).run()
page('Home'); page('Build Pipeline')
assert app.session_state['custom_stages'][0]['objective']=='Custom objective 0'
assert [x for x in app.text_input if x.label=='Model ID'][0].value=='explicit-model-0'
widget(app.button,'Save Custom Pipeline').click().run()
assert not app.exception and app.session_state['page']=='Run & Recover'
identity=app.session_state['draft']['workflow_id']
workflow=next(w for w in httpx.get('http://127.0.0.1:8003/workflows').json() if w['id']==identity)
assert len(workflow['stages'])==3 and all(s['operation']=='custom' for s in workflow['stages'])
assert workflow['stages'][0]['objective']=='Custom objective 0'
assert len({s['id'] for s in workflow['stages']})==3
widget(app.text_area,'What should the agents do?').set_value('Design a Python library management application.').run()
page('Home'); page('Run & Recover')
assert widget(app.text_area,'What should the agents do?').value=='Design a Python library management application.'
print('CUSTOM EDITOR VERIFIED: 1/2/5/10 stages; duplicate/reorder/remove; provider model reset; preserved drafts; exact saved stage count; multiline task. Saved:',identity)

page('Build Pipeline')
widget(app.selectbox,'Saved custom pipeline').set_value(identity).run()
widget(app.button,'Load pipeline into editor').click().run()
assert not app.exception
assert len(app.session_state['custom_stages'])==3
assert app.session_state['custom_stages'][0]['objective']=='Custom objective 0'
print('SAVED CUSTOM PIPELINE RELOAD VERIFIED')

# Discovered choices survive widget cleanup when navigating to another page.
app.session_state['models_groq']=['discovered-first','discovered-second']
app.run()
next(x for x in app.checkbox if x.label=='Enter model ID manually').set_value(False).run()
next(x for x in app.selectbox if x.label=='Model ID · discovered').set_value('discovered-second').run()
page('Home'); page('Build Pipeline')
assert next(x for x in app.selectbox if x.label=='Model ID · discovered').value=='discovered-second'
assert app.session_state['custom_stages'][0]['model']=='discovered-second'
print('DISCOVERED MODEL SELECTION PERSISTENCE VERIFIED')
