# Current 4.1 navigation

Build Pipeline now defaults to the fully custom editor; legacy guided offline templates are optional. Run & Recover uses a large multiline task prompt. Settings shows configured/verified state, model discovery, last check and backend-only credential instructions. The visual theme uses warm charcoal, ivory, terracotta, sage, mustard and plum.

Start with [provider setup](PROVIDER_SETUP.md), [custom pipelines](REAL_LLM_PIPELINES.md) and [demo](DEMO_GUIDE.md).

---

Historical navigation notes follow.

# AgentBailout — five-page navigation

The sidebar now has exactly five primary pages. The complete demonstration stays on Run & Recover. Other pages configure a pipeline or inspect recorded results. The blue/violet theme, icon buttons, numbered stage cards, outcome ring and red-to-green recovery strip use actual backend data; they do not generate fictional activity.

## 1. Home

Welcome message, backend status, selected pipeline, offline/real execution mode and AI provider configuration/last-test status. Four metrics show total executions, successful recoveries, recovery success rate and mean recovery duration. Recent activity and the outcome ring use stored records. The recovery denominator includes baseline and unfinished failures; it is not a calibrated success forecast.

Start New Workflow opens Run & Recover without starting anything. Run Quick Demo loads the Research template, an example garden-planning task, a controlled stage-two crash, protection ON and known-valid limits. It navigates to Run & Recover and waits for Start Task. Build My Own Pipeline opens the combined builder. Quick Demo restores its core example settings even if earlier advanced settings would reject rescue; it never deletes saved pipelines, agent definitions, ledger entries or history.

## 2. Build Pipeline

Five visible steps combine the former Workflow Builder, Agent Registry and Recovery Pool:

1. Choose a template or a previously saved pipeline.
2. Choose primary agents for each stage.
3. Choose Offline, GPT/OpenAI, Gemini or Ollama providers per stage. Agent choices are filtered by role/provider. Unconfigured providers remain labeled and cannot silently execute offline.
4. Choose recovery agents. The backend filters capability, schema, tool, availability, budget and deadline eligibility at execution time.
5. Name and Save Pipeline. This saves ordered stage references and recovery choices in SQLite and opens Run & Recover.

Change number or order of stages is inside an expander. The existing sequential contract catalog still applies; invalid order is rejected with an explanation. A preview shows the current pipeline. Add New Agent expands a small form with name, provider, model, role/capabilities and instructions. Test Connection performs a small real request for external/local model providers, validates the result and reports errors. Offline connection testing makes no model request. Save Agent registers a versioned configuration; it does not invent credentials or claim the model was reachable.

## 3. Run & Recover

All live demonstration controls are in the main panel:

- Saved pipeline and task input.
- Simulate Agent Failure, Cost/Time/Balanced policy, simulated task budget and task deadline.
- A prominent AgentBailout Protection toggle.
- Start Task, Inject Failure and Reset Demo.

Start Task creates the task with its saved settings and starts it in one action. The current UUID is retained. Start is disabled during execution and after a terminal result, preventing accidental duplicate runs. Reset Demo prepares another run while preserving form inputs, saved configurations and audit history; it is disabled during active execution. Backend lifecycle checks remain authoritative if the screen is stale.

Automatic failure: choose a scenario and press Start Task. The chosen fault is saved before execution; no second injection is necessary. Failure test options lets you choose the target stage. UI stage numbers are one-based; backend indices remain zero-based.

Manual failure: in Failure test options choose Wait for manual injection, select the desired failure and stage, then Inject Failure. This prepares a CREATED task with the saved fault. Press Start Task afterward. An unfaulted running task can also accept injection while the target is still pending. Duplicate injection and terminal/started-stage requests are rejected with friendly reasons and a technical-details expander.

The live view shows stage cards, failed/recovered state, a pictorial Failure → Check options → Worth rescuing? → Replace → Continue strip, diagnosis, considered options, selected replacement/reason, expected cost/time, final output and event timeline. Green means completed/recovered, red marks failure, blue/violet running/ready, and grey pending. It does not display a repaired agent unless a repair actually happened. Simulated ledger/details are available below without leaving the page; advanced analytics live in Settings.

Cost ranks estimated `(replacement cost + overhead) / probability`; Time ranks `estimated latency / probability`. Balanced uses 40% normalized expected cost, 35% normalized expected duration, 25% failure probability. The probabilities blend observed history with a small prior, are frozen in the run and are not calibrated forecasts. Compatibility, positive expected benefit, the 40% task-value cost cap, remaining recovery budget and deadline still apply. Actual attempts and spend remain bounded.

Task budget is simulated escrow, not a real provider spending cap. Actual external API cost remains unknown without grounded pricing. Deadlines cancel/await active work and cap demo delays before terminating and settling safely. Existing default $5 behavior is retained. Custom budgets change funding, reserved stage payouts, rescue policy and refunds; they are not cosmetic controls.

## 4. Compare Results

One prominent Compare With vs Without AgentBailout button runs two recorded workflows sequentially using the same task, frozen agent versions and equivalent controlled fault. Left is baseline, right protected. Both show outcome, final output/error, time, API cost or unknown, failed attempts, recovery attempts/outcome and simulated refund. A generated explanation uses measured time and allocation differences; protection is not presumed cheaper or faster. The saved task is labeled separately from editable draft controls. Real model outputs may differ.

## 5. Settings & History

Four tabs keep advanced tools out of the main demonstration:

| Tab | Contents |
| --- | --- |
| AI Providers | Configuration status, model field and Test Provider for Offline/OpenAI/Gemini/Ollama |
| Recovery Settings | Attempt/spend/runtime/deadline defaults and optimization strategy; Code & repository diagnostics in an expander |
| History | Stored tasks, failed/successful attempts, execution traces and previous code repairs/inspections |
| Ledger & Analytics | Simulated settlement/refund journal, expense chart and backend-derived metrics |

Defaults and draft inputs survive navigation in the browser session; saved agent/workflow/task data survive restarts in SQLite. An already-created task retains its frozen configuration. Provider keys never go in instructions or browser settings. Last-test status is explicitly a last test, not continuous provider monitoring.

## Start the website

From the repository root on Windows:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
$env:AGENTBAILOUT_DATABASE_URL='sqlite:///./phase3-demo.db'
.\.venv\Scripts\python.exe -m uvicorn backend.main:app --host 127.0.0.1 --port 8003
```

In another terminal in the same directory:

```powershell
$env:AGENTBAILOUT_BACKEND_URL='http://127.0.0.1:8003'
.\.venv\Scripts\python.exe -m streamlit run dashboard/app.py --server.port 8501 --server.address 127.0.0.1 --server.headless true
```

Open http://127.0.0.1:8501. Use one backend per database. If the environment does not exist, create it with Python 3.11+ (`python -m venv .venv`); on this workstation `.python\python.exe` is the installed alternative to the broken Store alias. On Ubuntu run `bash scripts/setup.sh`, `bash scripts/run_backend.sh` and `bash scripts/run_dashboard.sh` in separate terminals as appropriate. Linux execution remains unverified on this Windows host.

## Beginner walkthrough: quick recovery

1. Open Home and click Run Quick Demo.
2. Confirm Offline simulation, Agent crashes, stage two and protection ON.
3. Click Start Task. Watch the stage cards; the original formatter actually fails and a compatible backup runs.
4. Observe RECOVERED on the formatter, a completed summary, the recovery explanation and balanced settlement.
5. Click Reset Demo, switch protection OFF, and Start Task to show an actual failed baseline.
6. Turn protection back ON for a new run. To manually inject, select the manual test option and use Inject Failure before starting.

The two-click setup is verified. Understanding the product within 30 seconds is a design goal, not a measured user-study result.

## Beginner walkthrough: add GPT

1. Configure `OPENAI_API_KEY` in the backend terminal/environment. Restart the backend. Do not put a key in the agent form, instructions, source code or Git.
2. Open Build Pipeline → Add New Agent.
3. Enter a name, choose GPT / OpenAI, and enter a model identifier available to your account.
4. Choose Research as the role and include research in capabilities. Keep or edit the stage instructions.
5. Click Test Connection. This makes a small real model call and may incur provider usage. Resolve the actual returned error if it fails.
6. Click Save Agent. For the Research stage select GPT / OpenAI and the new agent.
7. Configure the other stages and compatible backups, then Save Pipeline.

The OpenAI Responses adapter and structured-output engine path remain mock-tested; no live OpenAI key was available in this environment.

## Beginner walkthrough: add Gemini

1. Configure `GEMINI_API_KEY` in the backend environment and restart the backend.
2. Build Pipeline → Add New Agent → choose Gemini.
3. Enter a valid model identifier from your account, an agent name, role, capabilities and instructions.
4. Test Connection, then Save Agent. For the relevant stage choose Gemini and the saved agent.
5. Save Pipeline and run it from Run & Recover. Each external response is independently schema-validated before downstream execution.

The Gemini adapter follows the [official structured-output REST guide](https://ai.google.dev/gemini-api/docs/generate-content/structured-output). HTTP mocks verify registration, request structure, usage handling and execution integration. No live Gemini key was available, so live Gemini execution remains unverified.

## Ollama

Run Ollama and install the desired model independently. Set OLLAMA_URL in the backend environment if it differs from http://127.0.0.1:11434. Add an Ollama agent with that installed model and Test Connection. The [Ollama chat API](https://docs.ollama.com/api/chat) adapter sends a non-streamed JSON-schema request and records token counts. The model does not get downloaded automatically. Mock integration is tested; live service availability was not established here.

## Beginner walkthrough: build and compare

1. Build Pipeline → choose Research, Coding or Document template.
2. Select primary agents/providers and backup agents on that same page. Inspect the preview.
3. Save Pipeline. Run & Recover opens with the saved pipeline selected.
4. Enter a task, choose a controlled failure and select the desired policy/budget/deadline.
5. Enable protection and press Start Task. Stay on this page for the entire recovery.
6. Open Compare Results and press Compare With vs Without AgentBailout. Both traces are saved, and measured differences are displayed.
7. Settings & History retains the results, failure evidence and simulated ledger. Its diagnostic expander preserves the previous bounded Python and read-only GitHub tools.

## Verification

The unchanged regression tests and new backend tests pass: **70 tests in 38.38 seconds**, including actual Cost/Time/Balanced candidate choices, custom budget funding/refunds, deadline cancellation, saved backup pools, provider health/error handling and Gemini/Ollama HTTP-mocked execution. The existing Starlette test-client deprecation warning remains.

`python scripts/verify_navigation.py` exercises every page, the quick demo with previously invalid limits, protected/baseline/manual runs, provider form choices, offline connection test, new agent registration, pipeline save, draft persistence, comparisons, history/ledger and retained code diagnostics. Legacy verify_dashboard.py, verify_phase4_dashboard.py and verify_critical_dashboard.py now delegate to this comprehensive five-page verification. No backend assertions were removed or skipped.

```powershell
.\.venv\Scripts\python.exe -m pytest -q --basetemp=.verified-tests-five-page-checkpoint
.\.venv\Scripts\python.exe scripts/verify_navigation.py
```

The UI script needs the backend on port 8003. Temporary databases isolate automated backend tests. A native browser check verified Home, quick-demo setup and completed recovered task 866269bb at 1280×720. Screenshots: docs/screenshots/five-page-home.png and five-page-recovery.png. No false provider-success labels, generated demo results or fake analytics were introduced.


## AgentBailout 4.0 Phase A/B checkpoint

The five pages remain. Settings & History now includes Claude and model discovery/selection; verification requires a successful model response. Build Pipeline remains contract-guided until Phase C; it does not yet expose arbitrary custom general-text stages.

See [setup](REAL_LLM_SETUP.md) and [complete audit and test report](AGENTBAILOUT4_PHASE_AB.md).
