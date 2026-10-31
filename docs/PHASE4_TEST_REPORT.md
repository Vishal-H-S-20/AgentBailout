# Phase 4 test report

## Status

Implemented and verified locally, with live external-provider verification pending credentials. Stop at Phase 4. No completion claim is made for Phases 5–8.

## Automated verification

Files created: backend/contracts.py, execution_engine.py, migrations.py, providers.py, registry.py, workflows.py; scripts/demo_phase4.py, verify_phase4_dashboard.py; tests/test_phase4.py; docs/PHASE4.md and PHASE4_TEST_REPORT.md.

Files updated: backend/models.py, schemas.py, main.py, supervisor.py and ledger.py; dashboard/app.py; scripts/verify_dashboard.py; requirements.txt, .env.example, README.md; docs/ARCHITECTURE.md, ECONOMIC_MODEL.md and HACKATHON_PROGRESS.md. Shell scripts retain their existing behavior and are stored executable in Git at the checkpoint.

Windows / Python 3.12.10. Final command:

```powershell
.\.venv\Scripts\python.exe -m pytest -q --basetemp=.verified-tests-phase4-release
```

Result: **48 passed, 1 warning in 27.18 seconds**. All original 14 Phase 1–3 tests still pass. New tests verify universal rescue at every stage of all three templates, the controlled fault matrix, actual protection OFF behavior, frozen comparison settings, immutable registry versions, saved/reordered custom pipelines, measured agent histories, contract/tool/provider compatibility, insufficient budgets, no compatible pool, migration backup/preservation, interrupted-attempt restart reconciliation, provider request/response handling and token usage, refusals/incomplete/invalid outputs, runtime cancellation fencing and latency eligibility. Tests use isolated temporary SQLite files.

An initial regression in failure settlement was found and repaired: a local select import shadowed the module import, interrupting failed-task reconciliation. The isolated ledger tests and full suite passed after correction. No failing tests remain in the final run. One upstream Starlette test-client deprecation warning remains.

`python -m compileall -q backend dashboard scripts tests` passed. `python -m pip check` reported no broken requirements. `git diff --check` passed. No new packages needed installation because jsonschema was already present through the dashboard dependencies; it is now an explicit direct dependency.

## Actual HTTP verification

Backend started on 127.0.0.1:8003 with the migrated existing demo database. GET /health returned `{"status":"ok","phase":4}`. Frontend on port 8501 returned HTTP 200.

Live command:

```powershell
.\.venv\Scripts\python.exe scripts/demo_phase4.py
```

Comparison ID: `5db1a5bb-d693-42e6-98db-333e9a74f231`, coding template, controlled crash in stage 2:

| Observation | Baseline | Protected |
| --- | --- | --- |
| Outcome | FAILED | COMPLETED |
| Execution seconds | 1.250 | 2.032 |
| Recovery attempts | 0 | 1 |
| Actual API cost | $0.00 (offline) | $0.00 (offline) |
| Simulated refund | $4.00 | $2.20 |
| Ledger | Balanced / settled | Balanced / settled |

Protected execution took 0.782 seconds longer. Observed demo wall clock: 3.359 seconds. These are measurements from this run, not guarantees. Protected rescue expense was $0.30 simulated. Total simulated allocation difference was $1.80 because the protected run also completed/paid downstream work and reserve. It is not described as monetary savings.

## Dashboard verification

Streamlit AppTest executed real callbacks against the running backend:

- Original create/start demo: normal refund $1.50, crash rescue refund $2.20, expensive rejection refund $4.00. All settled, balanced, zero escrow.
- Workflow Builder: selected Coding template and saved a configuration.
- Agent Registry: loaded actual configuration/history and registration controls without exceptions.
- Comparison Lab: Compare Both started paired runs and displayed FAILED and COMPLETED statuses; both settled correctly. Final comparison ID: `710bb64e-b706-4df6-af94-5c85e9af875f`.

Commands: `python scripts/verify_dashboard.py` and `python scripts/verify_phase4_dashboard.py`. No UI exceptions. AppTest emits an expected bare-thread ScriptRunContext warning. This verifies controls/rendering in Streamlit's test runtime, not a manual browser appearance audit. Screenshots and premium UI work remain Phase 6.

## Data preservation

Before migration, SQLite online backup created `phase3-demo.pre-v4-20261031180927296857.db`. Migration only adds new tables and its version marker. The migration test verifies historical results remain unchanged and repeat startup does not duplicate migration backups. The live historical-record comparison against the backup also passed. Databases and backups remain untracked.

## Real-agent provider verification

OPENAI_API_KEY and model configuration were absent. **No live OpenAI execution was performed.** The adapter was verified with HTTPX mock transport, including full engine integration and token usage persistence. Mocked fixtures are explicitly labeled and are not real model outputs. Missing credentials reject external workflow execution with a meaningful validation error. Actual API costs remain unknown for external attempts without grounded pricing; no costs are fabricated.

The adapter follows [official Structured Outputs documentation](https://developers.openai.com/api/docs/guides/structured-outputs?api-mode=responses). To finish live verification, set the key in the backend environment, restart, register an external agent with an accessible model, select it and inspect GET /tasks/{id}/execution after completion.

## Known boundaries

One local backend process per database; no arbitrary DAG, distributed workers or tool grants. Nine explicit operation contracts. Fixed $5 simulated budget with bounded configurable recovery allocation. Schema validation does not establish semantic quality. No self-repair, learned repair reuse or cost/time/balanced policy yet. Those are Phase 5. Ubuntu installation and visual browser audit remain unverified on this Windows host.
