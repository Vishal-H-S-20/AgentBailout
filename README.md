# AgentBailout

**4.1 update:** custom 1–10 stage multi-LLM pipelines, Groq, secure `.env` loading, repaired connection checks and a warm multicolor interface. **126 tests pass. Live cloud calls remain unverified because credentials are absent.** [Windows CMD setup](docs/PROVIDER_SETUP.md) · [Custom pipelines](docs/REAL_LLM_PIPELINES.md) · [Implementation report](docs/AGENTBAILOUT41_REPORT.md).



The interface now has five pages: **Home, Build Pipeline, Run & Recover, Compare Results, Settings & History**. For real execution, start with the provider setup and custom pipeline guides above. Home → Run Quick Demo → Start Task is explicitly offline. See [the beginner navigation guide](docs/WEBSITE_NAVIGATION.md) for provider setup and complete click-by-click instructions. Cost/Time/Balanced policies, simulated budgets and deadlines affect backend execution. Gemini and Ollama adapters are mock-tested; live provider verification requires configured services.


**The Self-Healing Control Plane for AI Agents**

Detect. Diagnose. Decide. Repair. Replace. Recover.

The current build extends the Phase 4 foundation with a five-page interface, working Cost/Time/Balanced selection, simulated budgets and deadline limits. Versioned agents execute ordered workflows under heartbeat monitoring. Baseline failures stop; protected failures trigger bounded compatible replacement. Tasks reuse upstream results and settle a simulated ledger. General configuration self-repair and validated fix reuse remain future work.

## Implemented

- Arbitrary custom 1–10 stage pipelines: objective, system prompt, provider/model, selected context, output format, limits and explicitly authorized recovery.
- Official OpenAI, Gemini, Groq and Claude SDK adapters, optional Ollama, backend-only .env loading, model discovery and verified plain-text connection checks.

- Three templates: Research → Format → Summarize; Plan → Code → Validate; Extract → Transform → Review.
- Database-backed agent registry, immutable versions, ordered workflow builder and selected recovery pool.
- Actual backend protection ON/OFF and baseline/protected comparison using frozen configurations and equivalent controlled faults.
- Crash, heartbeat loss, runtime timeout, invalid output and other controlled fault scenarios.
- Contract validation, compatibility checks, bounded recovery, repeated-failure circuit breaking, cancellation fencing and persistent attempts.
- Simulated double-entry settlement, budget limits, idempotent settlement, refunds and measured metrics.
- Streamlit dashboard with workflow controls, registry, comparison panels, events, ledger and output.
- OpenAI Responses adapter with structured output and token usage. **Live provider execution is unverified: no API key or model was configured.** Mock HTTP and engine integration are tested. Offline runs are clearly labeled deterministic simulations.

## Windows startup

From the repository root with Python 3.11+:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
$env:AGENTBAILOUT_DATABASE_URL='sqlite:///./phase3-demo.db'
.\.venv\Scripts\python.exe -m uvicorn backend.main:app --host 127.0.0.1 --port 8003
```

On this workstation use `.\.python\python.exe` if the system python command resolves to the broken Store alias. In another terminal:

```powershell
$env:AGENTBAILOUT_BACKEND_URL='http://127.0.0.1:8003'
.\.venv\Scripts\python.exe -m streamlit run dashboard/app.py --server.port 8501 --server.address 127.0.0.1 --server.headless true
```

Open [Dashboard](http://127.0.0.1:8501) or [API docs](http://127.0.0.1:8003/docs). Select a template and crash, then Compare With vs Without AgentBailout in Compare Results. No paid service is required for offline execution. To use real agents set OPENAI_API_KEY only in the backend environment, restart, register an OpenAI agent with an actual accessible model identifier, and select it. The backend loads a root `.env` file without overriding existing process variables; copy the safe `.env.example` locally and follow the current setup guide.

## Ubuntu startup

```bash
bash scripts/setup.sh
export AGENTBAILOUT_DATABASE_URL=sqlite:///./phase3-demo.db
.venv/bin/python -m uvicorn backend.main:app --host 127.0.0.1 --port 8003
# Separate terminal, same repository root:
export AGENTBAILOUT_BACKEND_URL=http://127.0.0.1:8003
.venv/bin/python -m streamlit run dashboard/app.py --server.port 8501 --server.address 127.0.0.1 --server.headless true
```

Ubuntu commands were not executed on this Windows host. Run one backend process per database.

## Verify

```powershell
.\.venv\Scripts\python.exe -m pytest -q --basetemp=.verified-tests-phase4
.\.venv\Scripts\python.exe scripts/demo_phase4.py
.\.venv\Scripts\python.exe scripts/verify_dashboard.py
.\.venv\Scripts\python.exe scripts/verify_phase4_dashboard.py
```

The last three require backend port 8003. Tests use temporary databases. See [Phase 4 guide](docs/PHASE4.md) and [test report](docs/PHASE4_TEST_REPORT.md) for results and measured live timings.

## API and persistence

Existing health, tasks, start, injection, events, ledger, workers and metrics endpoints remain. New: GET/POST /agents, GET/POST /workflows, GET /tasks/{id}/execution, POST/GET /comparisons and GET /comparisons/{id}. Backend /docs defines exact schemas. Invalid inputs/contracts return 422, unknown IDs 404, duplicate lifecycle operations 409.

Migration v4 is additive and makes an online backup before upgrading existing file databases. Existing results/journals remain intact. Interrupted executions fail safely and settle funded balances once; work is not silently replayed. Git excludes databases, backups, credentials, virtual environments and installers.

## Limits and roadmap

All ledger allocations are simulations. Actual model costs are separate and unknown without grounded pricing. Offline research is a planning outline, not web research. Schema validation does not establish factual quality. Generated/repository code is never executed; the advanced diagnostic tool runs only a fixed developer-authored program. Agents receive no tool grants. This is a local single-process sequential engine without authentication, a distributed queue or arbitrary DAG support. The nine-operation contract catalog is extensible in code.

The earlier phase roadmap remains useful for remaining work: generalized verified repairs and recovery memory, deeper visual polish, presentation documentation, then final validation/freeze. Basic strategy selection and the requested simplified pictorial UI are implemented now; full Phase 5–8 completion is not claimed.
