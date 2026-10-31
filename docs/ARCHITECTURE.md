# Phase 1 architecture

`main.py` owns API routes, database initialization and background job lifecycle. `schemas.py` validates API requests and exposes response contracts. `database.py` provides isolated engine/session factories; `models.py` stores Task, Stage and Event records. `supervisor.py` atomically claims CREATED tasks and runs independent agent functions in order. Each stage saves input before execution and result after execution. Errors produce FAILED tasks, never success.

Research extracts topic keywords and creates explicit planning findings. Formatter transforms these into report sections. Synthesis combines the sections and a recommendation. All outputs are deterministic simulations, not factual web research.

Supported task transitions: CREATED → RUNNING → COMPLETED or FAILED. Start responses acknowledge scheduling only. Stage timestamps, duration, worker identity and recovery-attempt count are persisted. Heartbeat timestamp is initialized at stage start; periodic monitoring belongs to Phase 2.

Run a single backend process. Do not point multiple backend instances at the same database; startup reconciliation assumes ownership of all in-flight tasks.
