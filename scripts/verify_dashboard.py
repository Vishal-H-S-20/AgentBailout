"""Exercise real dashboard controls against a running backend (isolated demo DB)."""
import time
from pathlib import Path
import httpx
from streamlit.testing.v1 import AppTest


def button(app, label):
    return next(b for b in app.button if b.label == label)


for scenario in ['normal', 'crash', 'expensive']:
    app = AppTest.from_file(str(Path(__file__).resolve().parents[1] / 'dashboard' / 'app.py'), default_timeout=20).run()
    assert not app.exception
    app.selectbox[0].select(scenario).run()
    button(app,'Create task').click().run()
    assert not app.exception
    task_id = app.selectbox[1].value
    button(app,'Start task').click().run()
    deadline = time.monotonic()+10
    while time.monotonic()<deadline:
        ledger = httpx.get(f'http://127.0.0.1:8003/tasks/{task_id}/ledger').json()
        if ledger['settled']:
            break
        time.sleep(.1)
    app.run()
    assert not app.exception
    assert ledger['settled'] and ledger['balanced']
    assert ledger['balances']['escrow']=='0.00'
    assert any('Final output' == h.value for h in app.subheader) if scenario != 'expensive' else len(app.error)>0
    print(f'DASHBOARD VERIFIED {scenario}: task={task_id}, refund={ledger["balances"]["client_refund"]}, balanced=True')
