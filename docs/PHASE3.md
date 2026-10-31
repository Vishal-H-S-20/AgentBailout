# Phase 3 run and demo

From the repository root, install with `.venv\Scripts\python.exe -m pip install -r requirements.txt`.

Start an isolated backend in PowerShell:

```powershell
$env:AGENTBAILOUT_DATABASE_URL='sqlite:///./phase3-demo.db'
.\.venv\Scripts\python.exe -m uvicorn backend.main:app --host 127.0.0.1 --port 8003
```

In a second terminal:

```powershell
.\.venv\Scripts\python.exe -m streamlit run dashboard/app.py --server.port 8501 --server.headless true
```

Open http://127.0.0.1:8501. Select crash, click Create task, then Start task. Auto refresh polls every second. Inspect the economic decision, backup activation, event timeline, final output, and settled ledger. Repeat with expensive to show rejection and refund; normal shows ordinary execution. Failure is configured at creation so the short formatter execution window cannot be missed. Inject failure can also be used on an existing task before formatter completion.

Reset demo selection clears only the selected task; it preserves history and financial audit records. Refresh updates current state. Set AGENTBAILOUT_BACKEND_URL to override port 8003. Single backend process per database only. Earlier servers on ports 8000/8002 run earlier code; use 8003 for Phase 3.

API additions: GET /tasks/{id}/ledger returns balance map, balanced flag, settlement outcome and journal. GET /metrics returns processed tasks, detections, successful rescues, success rate, average detection-to-backup completion seconds and actual settled simulated rescue cost. Costs are posted at terminal settlement.

Automated checks: `python -m pytest -q --basetemp=.verified-tests-phase3`. With the backend on 8003, `python scripts/verify_dashboard.py` exercises Streamlit controls against real HTTP endpoints for normal, rescue and rejected rescue paths. No external AI or payment service is used.

Known limits inherited from Phase 2: fixed backup identity, fixed budget, formatter-only periodic heartbeat, no separate elapsed-runtime timeout injection. Task terminal status remains independent of settlement status. No penalties, authentication, distributed queue or real payments.
