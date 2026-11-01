# AgentBailout 4.0 — Phase A/B checkpoint

## Scope and audit

This checkpoint completes the repository audit and provider integration work requested before stopping. Phases C–G (general custom stages, flexible contracts/context, full builder redesign and expanded real-model recovery) are not claimed complete.

Working baseline: commit `166e350`, preserved by tag `agentbailout-pre-4-provider-166e350`.

Deterministic output sources:
- `backend/agents/research.py`: keyword extraction and fixed research findings.
- `backend/agents/formatter.py`: deterministic transformation of those findings into sections.
- `backend/agents/synthesis.py`: joins sections and adds a fixed recommendation.
- `backend/contracts.py::offline`: routes the above and constructs fixed plan/code/validate/extract/transform/review responses, including the illustrative normalize_text function.
- `backend/providers.py::OfflineProvider.execute`: the explicit offline entry point.
- `backend/supervisor.py`: older offline execution branch invokes the deterministic agents. Configured workflows use the existing sequential execution engine instead.
- `backend/registry.py`: seeds offline agents/templates; it does not perform real generation.

External adapters never call these offline generators. Recovery now rejects offline candidates for a failed real-provider stage, including the default legacy recovery pool. Cross-provider real backups must be explicitly selected in that pool. Existing immutable workflow snapshots, comparison, watchdog and simulated settlement remain in place.

## Provider implementation

OpenAI now uses official AsyncOpenAI and Responses; Gemini uses official Google GenAI async client; Claude uses official AsyncAnthropic and Messages. SDK automatic retries are disabled so recovery remains bounded by the engine. SDK HTTP transports are injectable for tests. Ollama retains its local HTTP adapter and adds /api/tags model discovery.

The adapters support text generation independently of the current strict workflow operations, full response preservation, explicit system instructions, configured model/token limit/timeout, normalized token usage, model/request identifiers, timestamps and latency. Native structured output is requested from OpenAI/Gemini. Claude uses schema instructions plus the engine's existing local JSON Schema validation; native Claude schema-constrained generation is not claimed. Unsupported temperature/tool settings are omitted. No generated code is executed.

No model IDs or prices are invented. list_models discovers account/local identifiers. Discovery does not guarantee every model supports generation or structured output; use Test Provider with your selected model. External API cost remains unknown rather than $0.00. Simulated budgets remain separate and are not hard caps on external provider billing.

## Connection configuration and persistence

Settings & History → AI Providers includes Claude, model discovery, model selection and actual bounded generation tests. Keys are backend environment values only: OPENAI_API_KEY, GOOGLE_API_KEY or GEMINI_API_KEY, ANTHROPIC_API_KEY. GOOGLE_API_KEY takes precedence for Gemini. OLLAMA_URL configures the local server.

Configured is distinct from verified connected. A successful generation and output validation are required to persist a verified model and last-success timestamp. Failed tests/discovery record a sanitized error and disconnected status. A credential fingerprint invalidates stale checks when the key/server changes; secret values are never persisted or returned. Verification is historical, not a continuous health guarantee.

Additive ProviderCheck and ProviderReceipt tables retain connection checks and attempt response metadata. Migration backup: `phase3-demo.pre-providers-20261101024345644980.db`; **144/144** pre-existing task IDs, prompts, statuses and results were unchanged. No existing tables were rebuilt.

## Modified files

`backend/providers.py`, `main.py`, `schemas.py`, `models.py`, `migrations.py`, `execution_engine.py`, `workflows.py`; `dashboard/agent_form.py`, `pages.py`; `.env.example`, `requirements.txt`, `requirements-lock.txt`; `tests/test_simple_navigation_backend.py`, new `tests/test_provider_sdks.py`; `scripts/verify_navigation.py`, new `scripts/smoke_real_providers.py`; README and the documentation linked below.

## Tests and actual connections

Full suite: **100 passed in 51.11 seconds**, one upstream Starlette TestClient deprecation warning. New SDK tests cover all three cloud providers' exact HTTP requests, full long output, usage/metadata, model discovery, authentication/rate-limit/model-unavailable/server failures, timeout, no implicit retries, sanitized errors, credential-change invalidation, real-stage/offline recovery prohibition, and Claude execution/receipt persistence.

The initial regression run found empty SDK usage fields and Gemini transport selection differences; both were fixed. A new recovery test initially failed because existing task-creation preflight correctly rejected absent credentials; the test now configures credentials for creation then removes them before execution. Navigation's old four-provider assertion was updated to require Claude. No known test failures remain.

Live `verify_navigation.py`, `verify_judge_views.py` and provider-settings AppTest passed against port 8003. The latter verifies five provider test controls and four discovery controls. Compile/dependency checks pass. After the final status refinements, 35 targeted provider/backend tests passed in 12.45 seconds.

Real cloud smoke results: **OpenAI SKIPPED; Gemini SKIPPED; Claude SKIPPED**. No credentials or explicit model identifiers are configured. No successful real cloud generation or cross-provider live recovery is claimed. Ollama discovery was attempted against the configured local address and failed; its status correctly displays Disconnected. Local generation was not verified.

## Startup and demo

Use the exact Windows startup commands in REAL_LLM_SETUP.md. Backend: 8003; dashboard: 8501. Install requirements and restart both after upgrading.

1. Configure backend keys and a model you can access. Do not paste credentials into agent prompts.
2. Settings & History → AI Providers → Discover models → select identifier → Use selected model → Test Provider. This can incur provider charges. A successful test names the verified model and records usage.
3. Build Pipeline → Add AI agent: choose provider/model, instructions and a supported operation. Save the agent, assign it to that operation, and save the pipeline. The current builder remains limited to strict operation contracts until Phase C.
4. Run & Recover: enter task, select saved pipeline and No failure, then Start Task. Inspect actual attempt inputs, output, usage and provider receipt in technical details. A real model failure never falls back to offline simulation.
5. To demonstrate recovery, explicitly register/select compatible REAL backup agents in the saved recovery pool. Choose a controlled crash and target stage, protection ON, and start. Baseline/protected comparison uses frozen settings and separate actual runs; external outputs can differ and recovery can increase cost/runtime.
6. Run `python scripts/smoke_real_providers.py` with the venv interpreter for an explicit small real text-generation smoke test per configured provider. Missing credentials/models are SKIPPED, not PASSED.

## Remaining work

Phase C must remove fixed-role restrictions for general text workflows, allow user-defined objectives/context/output settings, stable dynamic 1–10 stage editing and stage-level backup controls. Phases D/E must integrate that generic request/configuration into the existing engine, context-window handling, richer recovery options and privacy/retention controls. Current provider generate() text support is a foundation, not a claim that the existing workflow UI already supports every 4.0 acceptance criterion.

## Official references consulted

- [OpenAI Responses Python API](https://developers.openai.com/api/reference/python/resources/responses/methods/create)
- [Google GenAI SDK](https://googleapis.github.io/python-genai/)
- [Anthropic Python SDK](https://github.com/anthropics/anthropic-sdk-python)

Installed SDK checkpoint: openai 2.54.0, google-genai 2.34.0, anthropic 0.125.0. Dependency lock records the complete environment.

[Verified provider UI screenshot](screenshots/phase-b-providers.png).
