# Phase 4 — configurable agents and universal recovery

Phase 3 checkpoint: `6438d16`, tagged `phase3-working-6438d16`. Existing endpoints remain compatible. New tasks use the generic sequential engine; historical executions remain inspectable. No Phase 5–8 completion is claimed.

## Run

From the repository root, in PowerShell terminal 1:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
$env:AGENTBAILOUT_DATABASE_URL='sqlite:///./phase3-demo.db'
.\.venv\Scripts\python.exe -m uvicorn backend.main:app --host 127.0.0.1 --port 8003
```

Terminal 2:

```powershell
$env:AGENTBAILOUT_BACKEND_URL='http://127.0.0.1:8003'
.\.venv\Scripts\python.exe -m streamlit run dashboard/app.py --server.port 8501 --server.address 127.0.0.1 --server.headless true
```

Open http://127.0.0.1:8501. Use one backend process for each database. Stop an older backend before starting the updated version. `.env.example` documents environment variables but is not loaded automatically. The localhost-only MVP has no authentication.

## Dashboard demonstration

1. Select Workflow Builder and a workflow template: Research, Coding or Document.
2. Expand Ordered stages and agents. Select operations and agent versions for each position; Stage count supports 1–8 stages. Invalid contract order is rejected rather than silently transformed. Save workflow retains it in SQLite.
3. Enter a task, choose crash and a fault stage. Leave protection ON. Create task, select Live Execution, and Start task.
4. Inspect the decision, replacement, final output, attempt trace and settled ledger. Switch protection OFF for a new run to show no retries or recovery.
5. Select Comparison Lab and Compare both. This automatically starts a baseline followed by a protected run using one frozen configuration, task and fault. Both are stored separately. Examine actual duration and allocation differences; protection may take longer and spend more to finish.
6. Select shared_failure to show a primary and backup encountering the same injected validation failure. A matching fingerprint opens the circuit. No invented repair or extra identical retries occur.
7. Registry shows configurations, health and observed sample counts. Register new version creates an immutable version under the chosen ID. Add agents to the recovery pool with the sidebar multiselect.

The fixed contract catalog currently supports nine operations across three templates. It is not an arbitrary distributed DAG or an arbitrary-code execution framework. Code generation in offline mode emits an illustrative snippet and static review, never executes it. Offline output is always labeled.

## Registry and snapshots

Each version stores provider/model, instructions, capabilities, tool requirements, input/output schema maps, supported task types, simulated replacement estimate, expected latency, availability, health configuration and a reliability prior. Successes, failures, timeouts, measured latency, recovery involvement and last execution time are updated from attempts. Measured reliability is unknown before observations. Selection uses a two-observation prior blended with history and records the frozen sample count. These are simple estimates, not predictive ML.

Executions retain immutable copies of selected versions, pool and policy. A new registry version cannot change an already-created task. Recovery checks operation capability, exact contract compatibility, tool requirements, availability, provider configuration and latency feasibility. Tools are not granted in this phase; agents requiring them are ineligible. Selection ranks simulated cost, blended reliability, ID and version. Recovery never selects the failed primary identity.

## Recovery bounds and failure semantics

All configured stages receive periodic heartbeats and a separate runtime limit. Slow live processing continues to heartbeat; heartbeat_loss explicitly suspends the worker without heartbeats; timeout suspends it while heartbeats continue. Cancellation is awaited before any replacement runs, so stale primary output cannot overwrite recovery.

Controlled scenarios: normal, crash, heartbeat_loss, timeout, invalid_output, tool_failure, backup_failure, shared_failure, expensive, insufficient_budget, no_backup and exhausted. These inject local faults, not provider outages. invalid_output supplies an invalid object to the output validator. Faults target one stage per execution. Dynamic injection is accepted once, only while that stage is pending; creation-time injection is the most repeatable demo.

max_attempts is bounded 1–3 per stage; simulated recovery_budget applies across the entire workflow. Duplicate pool versions are rejected. An identical failure fingerprint stops the loop early, even with attempts left. Candidate runtime estimate must fit the configured stage timeout. Phase 5 adds optimization strategies, repairs, persistent fix reuse and broader economic/deadline policy.

## Accounting

Each task has a fixed simulated $5 budget. Reserve remains $0.50 on success. Per-primary payout is min($1, floor-to-cents(($4.50 − configured recovery budget) / stage count)), preserving the original three-stage defaults. Only completed unreplaced stages earn that payout. Every started replacement attempt incurs its frozen simulated estimate plus $0.05 overhead, including failed attempts. All remaining funds are refunded. Budget checks happen before each attempt; startup interruption also settles once. Actual provider API costs are separate and may be unknown. No worker stake penalty is invented.

## Real provider configuration and verification boundary

The OpenAI Responses adapter posts structured-output requests with stage instructions and prior output, rejects refusals/incomplete or malformed responses, records token usage, and independently validates output. It does not report an actual dollar API cost without grounded pricing. No SDK dependency is required; HTTPX is reused. Schema integration follows [official Structured Outputs documentation](https://developers.openai.com/api/docs/guides/structured-outputs?api-mode=responses).

Set OPENAI_API_KEY in the backend environment, restart the backend, and register an OpenAI agent with an actual model identifier accessible to your account. Select it for a compatible stage. Model identifiers are explicit; no provider/model is silently substituted. The adapter has no implicit offline fallback. A selected offline recovery candidate may execute after external failure only because it is explicitly present in the user-chosen recovery pool; inspect its source label. Remove offline agents from that pool for external-only recovery.

No key or model was configured in the implementation environment. Live provider execution therefore remains UNVERIFIED. HTTP mock tests verify request structure, response parsing, refusal/error handling, token accounting, and the complete external-adapter-to-engine path. Mocked responses are not presented as real LLM responses. Provider connection status is configuration information, not a continuous remote health probe.

## Migration and restart

Migration version 4 adds agents, workflows, executions, attempts, comparisons and schema_migrations tables. It never rebuilds or deletes original tables. Existing file databases are backed up with SQLite's online backup API to `*.pre-v4-<UTC timestamp>.db` before the first additive migration. These files are ignored by Git. Repeating the migration is safe.

The existing demo database was backed up as `phase3-demo.pre-v4-20261031180927296857.db`, then migrated. Historical tasks were retained. On restart, interrupted running/rescuing/rescued tasks fail and reconcile their funded ledger; unfinished attempts become INTERRUPTED. No automatic task replay or claimed distributed restart recovery.

## API additions

| Route | Purpose |
| --- | --- |
| GET /agents, GET /workers | Registry versions, configuration, health and observed statistics |
| POST /agents | Register immutable next version |
| GET /workflows | Seeded templates and saved workflows |
| POST /workflows | Validate and save ordered stages |
| POST /tasks | Backward compatible prompt; optional workflow/stages, pool, protection and fault policy |
| POST /tasks/{id}/inject-failure | Single controlled fault into a pending stage |
| GET /tasks/{id}/execution | Frozen configuration, attempts, usage, validation, duration and ledger |
| POST /comparisons | Create and start paired baseline/protected runs |
| GET /comparisons | Stored comparison IDs |
| GET /comparisons/{id} | Both traces and measured duration difference |

See /docs on the backend for exact schemas. Unknown IDs produce 404, bad contracts/input produce 422 and conflicting lifecycle/unique writes produce 409.

## Verification commands

```powershell
.\.venv\Scripts\python.exe -m pytest -q --basetemp=.verified-tests-phase4-final
.\.venv\Scripts\python.exe scripts/demo_phase4.py
.\.venv\Scripts\python.exe scripts/verify_dashboard.py
.\.venv\Scripts\python.exe scripts/verify_phase4_dashboard.py
```

The last three require the backend running on port 8003. The HTTP demo supports --template research|coding|document and --scenario. Streamlit AppTest operates real widget callbacks against the backend. It is not a manual browser visual audit; premium design and screenshots are Phase 6 work.
