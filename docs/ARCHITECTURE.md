# Current architecture — Phase 4

`registry.py` stores immutable agent versions, compatibility rules and seeded templates. `contracts.py` defines the schema catalog and offline operations. `workflows.py` resolves ordered stages and freezes execution configuration, including primary/recovery versions and protection policy. `providers.py` is the async provider boundary: offline or OpenAI Responses, without implicit fallback or tool execution.

`execution_engine.py` is the generic sequential supervisor for new tasks. Each attempt receives heartbeats and a separate runtime deadline. Output is validated before passing downstream. On failure the controller records evidence, applies protection/budget/compatibility/attempt policies, and cancels/awaits the primary before replacement. Identical failure fingerprints open the circuit. `supervisor.py` retains lifecycle guards and historical-task compatibility; new configured tasks dispatch to the generic engine.

`migrations.py` backs up and additively migrates SQLite files. New tables store agent versions, workflows, execution snapshots, attempts and comparisons. Original tables are preserved. `ledger.py` atomically reconciles terminal allocations, per-attempt simulated expenses, reserve and refunds. `main.py` adds registry/workflow/comparison APIs. `dashboard/app.py` connects pipeline, pool and protection controls to live traces and comparison panels.

Comparisons freeze one configuration and execute baseline then protected, without claiming nondeterministic outputs match. Startup interruption fails and settles work rather than replaying it. One backend process per database remains required. See PHASE4.md.

## Historical Phase 1 foundation

`main.py` owns API routes, database initialization and background job lifecycle. `schemas.py` validates API requests and exposes response contracts. `database.py` provides isolated engine/session factories; `models.py` stores Task, Stage and Event records. `supervisor.py` atomically claims CREATED tasks and runs independent agent functions in order. Each stage saves input before execution and result after execution. Errors produce FAILED tasks, never success.

Research extracts topic keywords and creates explicit planning findings. Formatter transforms these into report sections. Synthesis combines the sections and a recommendation. All outputs are deterministic simulations, not factual web research.

Supported task transitions: CREATED → RUNNING → COMPLETED or FAILED. Start responses acknowledge scheduling only. Stage timestamps, duration, worker identity and recovery-attempt count are persisted. Heartbeat timestamp is initialized at stage start; periodic monitoring belongs to Phase 2.

Run a single backend process. Do not point multiple backend instances at the same database; startup reconciliation assumes ownership of all in-flight tasks.
