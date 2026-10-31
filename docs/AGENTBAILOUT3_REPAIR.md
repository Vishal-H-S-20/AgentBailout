# AgentBailout 3.0 — repair and demo report

Verified November 1, 2026 (IST). This increment follows the user's new critical-repair prompt; it is not a claim that every earlier Phase 5–8 roadmap feature has shipped.

## Diagnosis and evidence

The previous create-with-crash path passed its existing dashboard and API tests. The exact claim that a persisted crash sometimes vanished in the backend was not reproduced. Fault indexing was correct: UI stage 2 maps to stored stage_index 1. Creation commits configuration before Start can claim the task.

An evidenced UI problem was found: draft sidebar inputs were independent from an existing selected task's immutable saved configuration. Creating a normal task, changing the displayed scenario to crash, and starting the existing task still ran its saved normal configuration. Similarly changing protection after creation did not alter the run. The old UI did not make this distinction visible or prevent that misleading action. Newly created UUIDs matched in the observed reproductions, but selection used separate implicit widget/default state; it is now explicit and tested through repeated creation.

Captured original duplicate-injection response:

```json
HTTP 409
{"detail":"Failure already configured"}
```

That rejection was correct: a preconfigured failure needs no second injection. The UI nevertheless offered the button and displayed HTTPX's raw exception. Terminal and already-started stages shared an unhelpfully generic reason.

## P0 changes

- Preconfigured mode persists the selected fault during creation; it fires automatically on entry to the selected stage.
- Manual mode creates an unfaulted task. Separate manual controls select a failure and a pending stage. Injection commits before that stage starts.
- An explicit task_history widget key selects the newly returned UUID. The main panel shows the short ID, full UUID, saved fault and protection status. All action URLs use that selected UUID.
- Starting an old task with conflicting draft settings is disabled; Create & select task applies new settings to a new run. Saved execution configurations remain immutable.
- Duplicate, terminal and started-stage injection requests return structured codes and useful messages. The frontend displays the backend reason and preserves the method, URL, status and response body in a Technical response expander.
- Invalid actions are disabled when the task state is known. A fragment status transition refreshes the full app so sidebar status/actions do not remain stale.
- Injection eligibility and persistence use SQLite BEGIN IMMEDIATE. This serializes the pending-stage check with stage-start writes, eliminating the check/commit race for accepted injections.

Example new rejection codes: TASK_TERMINAL, FAULT_ALREADY_CONFIGURED and STAGE_STARTED. Unknown tasks remain 404; malformed scenarios/indices remain 422. Duplicate injection does not alter the stored original fault.

## P1 interface

The supplied references informed the charcoal surfaces, violet/blue accents, compact sidebar, bordered metric cards and node-based workflow canvas. The existing Streamlit frontend remains in place. Overview charts use stored execution data. Live Execution shows completed/recovered stage cards, compatible replacement routing, economic evidence, event history and settlement. Prominent main-panel create/start controls complement the sidebar setup. No fake trend percentages or decorative activity metrics were added.

The browser was used to visually inspect Overview and a completed rescued workflow. Screenshots:

- screenshots/overview-v3.png
- screenshots/rescue-v3.png

At the default 1280×720 viewport, controls/cards rendered without UI exceptions. Other viewport sizes have not been manually audited. A Python package-path issue found by AppTest after splitting dashboard components was fixed and the UI scripts passed afterward.

## P2 bounded code/repository adapters

POST /diagnostics and GET /diagnostics expose persisted diagnostic reports; Code Recovery provides the UI.

Python execution runs a fixed developer-authored numeric program in a child Python process, with isolated Python import flags and a three-second timeout. A string amount genuinely causes TypeError. With protection enabled, the controller validates and normalizes an existing numeric representation, re-executes the fixed program, and checks its result against Decimal arithmetic. Invalid/missing numeric facts are not invented. OFF records the real failure without repair. This is not an OS sandbox and is not an arbitrary-code runner.

Repository inspection fetches a single public GitHub Python file, caps it at 20 KB, rejects non-GitHub URLs and redirects, and performs read-only AST parsing. A plain repository URL targets main.py at HEAD; a blob URL selects another file. Submitted source is likewise parsed, never executed. Syntax errors include line/reason and require review; corrected source can be submitted for revalidation. No clone, dependency installation, repository edits, generated code execution or claimed comprehensive repository repair occurs.

Live GitHub verification: CPython's public `Lib/colorsys.py` at https://github.com/python/cpython/blob/main/Lib/colorsys.py was fetched and AST-validated. Report ID: b1a0553a-c6c8-48fe-9376-a85430c7f667. This establishes syntax validity only, not dependency/test/runtime correctness. Diagnostic results are stored separately from the workflow's simulated financial ledger; no payment or insurance is implied.

Schema marker 401 adds diagnostic_runs without rebuilding existing tables. Existing databases receive another online SQLite backup before this addition. Existing task history is preserved.

## Verification

```powershell
.\.venv\Scripts\python.exe -m pytest -q --basetemp=.verified-tests-v3-final
```

**59 passed, 1 warning in 32.57 seconds.** The warning is the existing upstream Starlette TestClient deprecation. Tests cover all seven requested critical cases, original regressions, real runtime normalization, rejected/lossy numeric repairs, static inspection, URL restrictions and friendly error presentation. A failed result validation is displayed as a failed recovery even when the child process exits zero.

Live UI verification commands (backend on 8003):

```powershell
.\.venv\Scripts\python.exe scripts/verify_dashboard.py
.\.venv\Scripts\python.exe scripts/verify_phase4_dashboard.py
.\.venv\Scripts\python.exe scripts/verify_critical_dashboard.py
```

The first two verify normal/rescue/rejected-settlement and workflow/registry/comparison behavior. The critical script verifies draft mismatch blocking, exact UUID auto-selection, automatic and manual crashes, duplicate/terminal action disabling, Overview, and Python recovery through actual widget callbacks and live HTTP. All passed. AppTest emits its expected bare-thread context warning. Imports compiled and pip check reported no broken requirements.

A native browser demo additionally created task 5d46cf8d-3bc0-4175-993b-a3f47b2f6351, saved crash at stage 2, clicked Start selected task, and visibly reached COMPLETED with Formatter RECOVERED and a balanced settled ledger.

Latest paired HTTP demo: 578d67ec-2817-4420-bae5-df84c326bd86. Baseline FAILED in 1.297s with no recovery; protected COMPLETED in 2.046s with one attempt. Both settled. Protected took 0.749s longer; wall time 3.375s. Simulated refunds: $4.00 baseline, $2.20 protected. Rescue expense $0.30; total allocation difference also includes downstream payouts and reserve. No monetary savings claim is made.

## Exact startup

Repository root, terminal 1:

```powershell
$env:AGENTBAILOUT_DATABASE_URL='sqlite:///./phase3-demo.db'
.\.venv\Scripts\python.exe -m uvicorn backend.main:app --host 127.0.0.1 --port 8003
```

Terminal 2:

```powershell
$env:AGENTBAILOUT_BACKEND_URL='http://127.0.0.1:8003'
.\.venv\Scripts\python.exe -m streamlit run dashboard/app.py --server.port 8501 --server.address 127.0.0.1 --server.headless true
```

Do not start another backend against this database while one is running. Backend /health reports version 0.4.1. Open http://127.0.0.1:8501. Bash startup scripts also use backend port 8003. Dependency installation remains `python -m pip install -r requirements.txt`.

## Demonstration sequence

1. Live Execution → preconfigured mode → crash → stage 2 → protection ON → Create & select task → Start selected task. Do not press Inject failure. Observe primary failure evidence, recovered Formatter, final output and ledger.
2. Select protection OFF, Create & select task, then Start. It fails after Research; no backup runs.
3. Manual mode → Create & select task → choose Manual failure type crash and Manual fault stage 2 → Inject failure → Start selected task. Duplicate injection is disabled.
4. Overview shows actual stored statistics. Code Recovery → Python execution → 12.50 → Run diagnostic shows TypeError, validated normalization and a successful rerun.
5. Repository inspection accepts Python source or a public GitHub Python file. Demonstrate a syntax error, then submit corrected source to validate it.

This is a reproducible sequence, not a measured promise that a full narrated presentation fits three minutes. For a recording, start OBS or the team's recorder, capture the dashboard browser, follow these steps, and verify the saved video before presenting. No recording was created in this session.

## Remaining limits

Live external LLM execution still requires credentials and remains unverified. Cost/time/balanced optimization and generalized repair memory from the earlier Phase 5 plan are not claimed. Repository work is single-file read-only syntax diagnosis; Python recovery is limited to the fixed numeric program. Arbitrary repository execution/repair needs a proper isolated runner and explicit scope. All financial allocations remain simulated. No authentication or distributed multi-process execution is implemented.
