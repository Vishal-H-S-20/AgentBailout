# Actual progress

## Five-page navigation and pictorial UX — November 1, 2026 IST

Replaced seven primary sections and repeated sidebar controls with Home, Build Pipeline, Run & Recover, Compare Results and Settings & History. Added one-click valid demo setup, one-screen task controls, icon-based pipeline/recovery steps, outcome chart, persistent browser drafts and a combined agent/provider/pool builder. Saved recovery choices now persist with workflow records. Previous code/repository tools remain in advanced settings.

Connected Cost/Time/Balanced selection, configurable simulated budgets and enforced deadlines to the backend. Added Gemini/Ollama adapters plus real provider-test endpoints; credentials/services were unavailable for live model verification, so adapter integration uses explicit HTTP mocks. Existing offline/OpenAI behavior remains tested. 70 backend tests pass and the comprehensive five-page UI script passes. Native browser verification reached a real completed recovered task. Details: WEBSITE_NAVIGATION.md.

## AgentBailout 3.0 critical repair and dashboard upgrade — November 1, 2026 IST

Reproduced duplicate preconfigured injection 409 and identified the misleading draft-vs-saved task configuration path. Added explicit new-task UUID selection, visible saved settings, preconfigured/manual modes, action eligibility guards, friendly backend-coded errors and serialized injection checks. Redesigned the existing Streamlit UI using the supplied visual references, verified in a browser, and saved Overview/recovery screenshots. Added persisted bounded Python runtime normalization and read-only GitHub/source syntax diagnostics.

59 tests passed in 32.57s. Existing and critical dashboard scripts passed against the running backend. Browser-created crash task completed with a recovered Formatter and settled ledger. GitHub CPython colorsys.py fetched and syntax-validated without execution. Full report: AGENTBAILOUT3_REPAIR.md. This update does not claim all earlier Phase 5–8 roadmap features or arbitrary repository self-repair.

## Phase 4 — configurable workflows and universal replacement verified

Preserved Phase 3 commit 6438d16 with tag phase3-working-6438d16. Added versioned database agent registry, three templates, saved/ordered workflows, immutable execution snapshots, offline/OpenAI provider abstraction, all-stage watchdog/runtime limits, universal compatible replacement pool, actual backend protection toggle, controlled baseline/protected comparison, per-attempt usage/history, repeated-failure stop and additive backed-up database migration. Extended settlement to arbitrary supported stage counts and bounded replacement expenses. Dashboard exposes builder, registry, pool, protection and comparison controls.

Final suite: 48 passed in 27.18 seconds, one upstream deprecation warning. Live HTTP coding comparison: baseline FAILED in 1.250s, protected COMPLETED in 2.032s, both balanced/settled. Dashboard callbacks verified original normal/rescue/rejection plus workflow save and paired comparison. Backend health phase=4 and frontend HTTP 200 verified. No live provider call: credentials/model absent; adapter and full engine path tested through HTTP mocks only. Detailed evidence and limitations are in PHASE4_TEST_REPORT.md and PHASE4.md.

Phase 4 checkpoint reached. Cost/time optimization, safe repair, persistent fix reuse and premium UI remain Phases 5–6. Await CONTINUE PHASE 5.

## Phase 3 — dashboard and settlement verified

Implemented dark Streamlit dashboard with task creation, start, failure selection/injection, history, auto/manual refresh, directional workflow graph, decision details, events, ledger chart/journal, metrics and final output. Added simulated double-entry ledger, atomic terminal settlement, unique per-task settlement marker, refunds, ledger API and metrics API.

Verification: 14 backend tests passed in 9.08 seconds. Streamlit AppTest exercised actual dashboard controls against the live backend for normal execution, crash rescue and expensive rejected rescue, then confirmed balanced journals and zero escrow. Refunds were $1.50, $2.20 and $4.00. Repeated the dashboard checks successfully after updating layout parameters. Frontend HTTP returned 200; backend started successfully on port 8003. Frontend is on port 8501. Visual appearance was not manually inspected in a browser; dashboard rendering and controls were verified with Streamlit's testing runtime.

No penalties are charged. Budget remains fixed at $5.00. Legacy unfunded tasks remain historical and are not retroactively funded. Full instructions and accounting assumptions are in PHASE3.md and ECONOMIC_MODEL.md. One upstream Starlette deprecation warning remains in backend tests; Streamlit AppTest emits its expected bare-thread context warning. Prior Phase 2 gaps remain documented.

## Phase 2 — core recovery verified; remaining scope documented

Added watchdog, Decimal economic evaluator, formatter heartbeats, real failure injection, primary cancellation, bounded backup execution, persisted recovery states and recovery events. Full suite: 10 passed. Live HTTP crash rescue completed on port 8002. See PHASE2.md for reproduction and explicit gaps: configurable registry, runtime timeout, all-stage heartbeats and finance integration remain unfinished.

## Phase 1 — complete and verified

Implemented: SQLite models, three deterministic agents, ordered supervisor, atomic start claim, input/output persistence, UTC events, health/create/list/detail/start/events API, initial pipeline/API tests, Windows demo and Ubuntu scripts.

Initial environment: Windows PowerShell; Git 2.53.0. `python` resolves to an unusable Windows Store alias. No `py` or `uv` found. Initial Python download failed DNS resolution in the sandbox; an escalated download was requested. Runtime test results will be recorded after execution.

Verification: Python 3.12.10 installed locally; dependencies installed in `.venv`. `python -m pytest -q --basetemp=.verified-tests` passed all 4 tests in 1.81 seconds outside the sandbox. One upstream Starlette warning advises migrating its test client from httpx to httpx2; current tests pass. An earlier test run raced dependency installation and failed collection; rerun after installation passed. Sandbox runs stalled or denied sockets; local HTTP verification required escalation.

Backend startup succeeded on 127.0.0.1:8000. Live `/health` returned ok. `scripts/demo.ps1` created task `c7396d2b-7c73-4686-8535-291519dc6106`, started it, observed RUNNING then COMPLETED, and retrieved final output and all nine ordered events. All three stages completed in approximately 1.6 seconds. Temporary database tests verified persistence by disposing and reopening the database. Invalid inputs returned 422, unknown tasks 404, duplicate starts 409. Database and installer are excluded from Git.

No Phase 2 functionality has been claimed or implemented. Dashboard, watchdog, recovery, solvency and ledger remain future work. Ubuntu scripts are supplied but unverified on Linux. Phase 1 checkpoint: await CONTINUE PHASE 2.


## AgentBailout 4.0 — Phase A/B provider checkpoint

Official OpenAI Responses, Google GenAI and Claude Messages SDK adapters; model discovery; verified generation connection checks; persisted provider receipts; no real-to-offline recovery. 100 tests passed, final 35 targeted checks passed; live navigation and judge views passed. All three cloud smoke tests skipped because credentials/models are absent. Local Ollama discovery failed and is displayed Disconnected. Preserved 144/144 existing task records. See AGENTBAILOUT4_PHASE_AB.md. Stop at Phase B as requested; arbitrary custom stages are Phase C onward.
