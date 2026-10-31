# AgentBailout

Phase 3 dashboard and simulated ledger are now implemented. See [Phase 3 run/demo instructions](docs/PHASE3.md) and [accounting policy](docs/ECONOMIC_MODEL.md). The historical Phase 1 notes below describe the initial foundation; Phase 3 uses backend port 8003 and dashboard port 8501.

Autonomous Recovery & Liquidity Layer for Multi-Agent Workflows.

The persistent Research → Formatter → Synthesis pipeline supports formatter crash and heartbeat-loss rescue, economic decisions, backup execution, simulated settlement and refunds. Research produces a deterministic planning outline derived from the user's topic, not externally verified facts. All financial records are simulations.

## Windows setup

Run from the repository root with Python 3.11 or later:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe -m uvicorn backend.main:app --host 127.0.0.1 --port 8000
```

In a second terminal, from this same directory:

```powershell
.\scripts\demo.ps1
```

## Ubuntu setup

```bash
bash scripts/setup.sh
bash scripts/run_tests.sh
bash scripts/run_backend.sh
```

Visit http://127.0.0.1:8000/docs for interactive request and response schemas. Create a task with `POST /tasks` using `{"prompt":"Plan a community garden"}`, copy its ID, then call `POST /tasks/{id}/start`. Poll `GET /tasks/{id}` until `COMPLETED`; inspect `result` and `stages`. Inspect `GET /tasks/{id}/events` for stage order.

## API

| Endpoint | Behavior |
| --- | --- |
| GET /health | Database connectivity check |
| POST /tasks | Persist task and three pending stages; 201 |
| GET /tasks | Most recent 100 tasks |
| GET /tasks/{id} | Status, stage inputs/outputs, final result |
| POST /tasks/{id}/start | Start once; 202, repeated starts 409 |
| GET /tasks/{id}/events | Persisted events in insertion order |

Unknown task IDs return 404; invalid input returns 422. SQLite defaults to `agentbailout.db` in the working directory. Set `AGENTBAILOUT_DATABASE_URL` and `AGENTBAILOUT_STAGE_SECONDS` through environment variables; `.env` is an example, not automatically loaded.

## Architecture and limits

FastAPI validates requests, SQLAlchemy persists tasks/stages/events, and the supervisor schedules async execution. Each stage consumes its predecessor's stored structured output. UTC timestamps and unique worker IDs provide traceability. An atomic conditional update prevents duplicate starts. Use one Uvicorn process: this is a local MVP, not a distributed queue. SQLite calls are synchronous and suitable only for this low-volume demo.

Shutdown cancels running jobs and marks them failed. On startup, persisted RUNNING tasks are marked FAILED rather than silently rerun. Create a new task after interruption. Completed results survive restarts. Periodic heartbeat monitoring, automatic rescue and settlement are not implemented in Phase 1. Tests use temporary databases.

Next: Phase 4 stability work and the documented remaining detection/registry improvements.
