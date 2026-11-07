# 🛟 AgentBailout
### The Self-Healing Recovery Layer for Multi-Agent AI Workflows

**Detect. Diagnose. Decide. Recover.**

AgentBailout is an AI workflow orchestration and fault-recovery platform designed to make multi-agent systems more reliable, resilient, and cost-efficient.

When an AI agent crashes, times out, or produces an invalid result, AgentBailout detects the failure, evaluates available recovery strategies, selects a compatible replacement, and attempts to resume the workflow without restarting successfully completed stages.

The platform supports configurable AI workflows, model-provider integrations, automated failure recovery, economic decision-making, execution monitoring, and side-by-side comparisons with and without recovery.

---

## 🎯 Problem Statement

Modern AI applications increasingly depend on multiple specialized agents collaborating to complete complex tasks.

For example:

```text
User Request
     |
     v
Planning Agent (GPT)
     |
     v
Code Generation Agent (Gemini)
     |
     v
Validation Agent (Claude / Groq)
     |
     v
Final Output
```

However, these workflows are vulnerable to failures.

A single agent may:

- Crash during execution.
- Exceed its timeout.
- Lose connectivity to an AI provider.
- Encounter an API rate limit.
- Return invalid or incompatible output.
- Become unavailable.
- Fail to complete its assigned task.

Because subsequent agents depend on previous outputs, one failure can interrupt the entire workflow.

Traditional recovery mechanisms typically involve retries, restarting failed tasks, or manually selecting alternatives.

These approaches may waste completed work, increase API costs, and fail to consider available time and recovery budgets.

**Our challenge: How can multi-agent workflows automatically recover from failures while making intelligent, economical recovery decisions?**

---

## 💡 Our Solution

AgentBailout introduces a recovery control layer that monitors workflow execution and evaluates recovery options whenever an agent fails.

Instead of blindly restarting the entire workflow, AgentBailout attempts to recover the failed stage while preserving previously completed results.

### Recovery Workflow

```text
              USER TASK
                  |
                  v
          WORKFLOW SUPERVISOR
                  |
                  v
             AGENT 1
             COMPLETED
                  |
                  v
             AGENT 2
              FAILED
                  |
                  v
          FAILURE DETECTION
                  |
                  v
        RECOVERY DECISION ENGINE
                  |
          +-------+-------+
          |               |
          v               v
     RESCUE VIABLE    RESCUE NOT VIABLE
          |               |
          v               v
    SELECT BACKUP     SAFE TERMINATION
          |           AND SETTLEMENT
          v
    EXECUTE BACKUP
          |
          v
    VALIDATE OUTPUT
          |
          v
    RESUME WORKFLOW
          |
          v
        AGENT 3
          |
          v
      FINAL OUTPUT
          |
          v
    EXECUTION HISTORY
      AND SETTLEMENT
```

### What makes AgentBailout different?

AgentBailout does more than identify errors.

It combines:

1. Automated failure detection.
2. Recovery-agent compatibility checking.
3. Cost-aware and time-aware recovery policies.
4. Alternative worker selection.
5. Preservation of completed stages.
6. Automatic workflow continuation after successful recovery.
7. Recovery attempt limits and safeguards.
8. Execution history and auditability.
9. Comparison of protected and unprotected workflows.

---

## ✨ Key Features

### 1. Configurable Multi-Agent Workflows

Create workflows containing multiple ordered stages.

Configure the agents responsible for planning, research, coding, analysis, summarization, validation, or other supported tasks.

The workflow builder supports registered agents and reusable workflow definitions.

### 2. Multi-LLM Provider Architecture

AgentBailout is designed to support different AI providers through a unified execution interface.

Providers targeted by the project include:

- **OpenAI** — GPT models.
- **Google Gemini** — Gemini models.
- **Anthropic** — Claude models.
- **Groq** — Hosted high-speed model inference.
- **Ollama** — Locally hosted models.

Real provider execution requires appropriate API access, supported model identifiers, and correctly configured backend connections.

Provider availability and live verification depend on the installed project version.

### 3. Intelligent Failure Detection

The execution engine monitors workflow status and detects failure conditions such as:

- Worker crashes.
- Execution timeouts.
- Heartbeat loss.
- Invalid output contracts.
- Provider or tool errors.

Controlled failure injection is also supported for testing and demonstrations.

### 4. Cost-Aware Recovery

The recovery engine can prioritize economically viable recovery options.

Candidate evaluation considers factors such as:

- Estimated recovery expense.
- Available task budget.
- Compatibility.
- Estimated completion time.
- Reliability estimates.
- Remaining deadline.

Financial budgets and settlements in the current demonstration are simulated.

### 5. Time-Aware Recovery

When speed matters, AgentBailout can prioritize recovery candidates with lower estimated execution time, subject to compatibility and other policy restrictions.

### 6. Compatible Backup-Agent Selection

The recovery pool contains agents capable of handling different workflow operations.

Before choosing a backup, the platform checks whether it can perform the failed stage and satisfy its input/output requirements.

### 7. Workflow Continuation

Completed upstream stage results are preserved.

Following successful recovery, execution can continue from the next stage rather than restarting the entire pipeline.

### 8. Recovery ON/OFF Comparison

Run equivalent controlled failure scenarios with:

**AgentBailout OFF:** The baseline pipeline executes without AgentBailout recovery.

**AgentBailout ON:** The recovery controller evaluates and attempts a suitable intervention.

Compare:

- Workflow completion.
- Execution time.
- Failed attempts.
- Recovery attempts.
- Recovery outcomes.
- Costs and simulated settlements.
- Final output.

### 9. Detailed Execution Monitoring

Inspect workflow execution through the dashboard.

Available execution information includes:

- Agent status.
- Execution events.
- Failure details.
- Recovery decisions.
- Selected replacement worker.
- Execution timing.
- Task results.
- Simulated ledger information.

### 10. Persistent Recovery History

Workflow configurations, task results, execution attempts, and recovery events are recorded to support debugging and analysis.

---

## 🏗️ System Architecture

```text
┌───────────────────────────────┐
│       STREAMLIT FRONTEND      │
│                               │
│  Workflow Builder             │
│  Run & Recover                │
│  Comparison Dashboard         │
│  Settings & History           │
└───────────────┬───────────────┘
                │ HTTP API
                ▼
┌───────────────────────────────┐
│         FASTAPI BACKEND       │
│                               │
│  Task & Workflow Management   │
│  Agent Registry               │
│  Workflow Supervisor          │
│  Provider Adapters            │
└───────────────┬───────────────┘
                │
                ▼
┌───────────────────────────────┐
│      AGENT EXECUTION LAYER    │
│                               │
│  OpenAI / Gemini / Claude     │
│  Groq / Ollama / Offline      │
└───────────────┬───────────────┘
                │
                ▼
┌───────────────────────────────┐
│       AGENTBAILOUT ENGINE     │
│                               │
│  Failure Monitor              │
│  Recovery Controller          │
│  Compatibility Evaluation     │
│  Cost / Time Decision Policy  │
│  Backup Agent Selection       │
│  Recovery Validation          │
└───────────────┬───────────────┘
                │
                ▼
┌───────────────────────────────┐
│       PERSISTENCE LAYER       │
│                               │
│  SQLite + SQLAlchemy          │
│  Workflow Records             │
│  Execution Events             │
│  Recovery Attempts            │
│  Simulated Ledger             │
└───────────────────────────────┘
```

The architecture separates user interaction, workflow execution, recovery decisions, and persistent storage.

---

## 🛠️ Technology Stack

| Technology | Purpose |
|---|---|
| Python | Core application and orchestration |
| FastAPI | Backend REST API |
| Streamlit | Interactive web dashboard |
| SQLite | Workflow and execution data storage |
| SQLAlchemy | Database access and persistence |
| Pydantic | API and model validation |
| HTTPX | HTTP communication and testing |
| Uvicorn | ASGI application server |
| Pytest | Unit and integration testing |
| OpenAI API | GPT model integration |
| Google GenAI API | Gemini integration |
| Anthropic API | Claude integration |
| Groq API | Additional hosted-model integration |

The application supports an offline simulation mode for deterministic testing without external API calls.

---

## 📁 Project Structure

The main repository is organized around these components:

```text
AgentBailout/
│
├── backend/
│   ├── API endpoints
│   ├── Agent registry
│   ├── Workflow supervisor
│   ├── Recovery engine
│   ├── Provider integrations
│   ├── Database models
│   └── Ledger management
│
├── dashboard/
│   ├── app.py
│   ├── pages/
│   ├── components/
│   └── styles/
│
├── tests/
│
├── scripts/
│
├── docs/
│
├── .env.example
├── .gitignore
├── requirements.txt
└── README.md
```

Exact internal module names may vary across implementation versions.

---

## 🚀 Getting Started

### Prerequisites

- Python 3.11 or newer.
- Git.
- Windows or Linux.
- A modern web browser.
- Optional API keys for real cloud LLM execution.

### 1. Clone the Repository

```bash
git clone https://github.com/YOUR_USERNAME/AgentBailout.git
cd AgentBailout
```

Replace `YOUR_USERNAME` with the GitHub account hosting this project.

### 2. Create a Virtual Environment

**Windows CMD:**

```cmd
python -m venv .venv
.venv\Scripts\activate
```

**Linux:**

```bash
python3 -m venv .venv
source .venv/bin/activate
```

### 3. Install Dependencies

```bash
python -m pip install -r requirements.txt
```

### 4. Configure AI Providers (Optional)

To enable real LLM execution, configure the required provider credentials.

In Windows CMD:

```cmd
set "OPENAI_API_KEY=YOUR_OPENAI_KEY"
set "GEMINI_API_KEY=YOUR_GEMINI_KEY"
set "GROQ_API_KEY=YOUR_GROQ_KEY"
set "ANTHROPIC_API_KEY=YOUR_ANTHROPIC_KEY"
```

Only configure the providers you intend to use.

API access and billing depend on each provider.

Never commit credentials to GitHub.

### 5. Start the FastAPI Backend

In the project folder:

**Windows CMD:**

```cmd
set "AGENTBAILOUT_DATABASE_URL=sqlite:///./phase3-demo.db"

python -m uvicorn backend.main:app --host 127.0.0.1 --port 8003
```

**Linux:**

```bash
export AGENTBAILOUT_DATABASE_URL=sqlite:///./phase3-demo.db

python -m uvicorn backend.main:app --host 127.0.0.1 --port 8003
```

Backend API:

http://127.0.0.1:8003

Interactive API documentation:

http://127.0.0.1:8003/docs

### 6. Start the Streamlit Dashboard

Open a second terminal in the project folder.

**Windows CMD:**

```cmd
set "AGENTBAILOUT_BACKEND_URL=http://127.0.0.1:8003"

python -m streamlit run dashboard/app.py --server.port 8501
```

**Linux:**

```bash
export AGENTBAILOUT_BACKEND_URL=http://127.0.0.1:8003

python -m streamlit run dashboard/app.py --server.port 8501
```

Open:

**http://127.0.0.1:8501**

Keep both terminals running.

---

## 🖥️ Website Navigation

The documented website includes five main pages.

| Page | Purpose |
|---|---|
| Home | Project overview and quick demonstration |
| Build Pipeline | Create and configure agent workflows |
| Run & Recover | Execute tasks and observe recovery |
| Compare Results | Compare baseline and protected executions |
| Settings & History | Manage agents, providers and execution records |

### Building a Pipeline

1. Open **Build Pipeline**.
2. Select or configure workflow stages.
3. Assign compatible primary agents.
4. Configure eligible recovery agents.
5. Check pipeline compatibility.
6. Save the workflow.

### Running a Task

1. Open **Run & Recover**.
2. Select the saved pipeline.
3. Enter the task prompt.
4. Choose a failure scenario, if desired.
5. Select recovery policy.
6. Configure the simulated budget and deadline.
7. Turn AgentBailout protection ON or OFF.
8. Start the task.
9. Inspect execution and recovery results.

---

## 🧪 Demonstration Scenario

### Example User Prompt

```text
Create a Python student management application that
supports adding students, storing subject marks,
calculating grades, searching records, and generating
a summary report.

Include error handling, complete source code,
example usage, and meaningful test cases.
```

### Example Three-Stage Workflow

| Stage | Assigned task | Example provider |
|---|---|---|
| 1 — Planner | Analyze requirements and create a development plan | GPT |
| 2 — Code Generator | Generate the application code | Gemini |
| 3 — Validator | Review the code and identify potential defects | Groq or Claude |

These providers require verified API connections for real execution.

### Scenario A — Without AgentBailout

Inject a controlled crash into Stage 2.

```text
Planner        ✅ Completed
     |
Code Generator ❌ Failed
     |
Validator      ⏸ Not Executed
```

**Expected result:** The workflow fails without AgentBailout recovery.

### Scenario B — With AgentBailout

Run an equivalent controlled failure with recovery enabled.

```text
Planner          ✅ Completed
     |
Code Generator   ❌ Failed
     |
AgentBailout     🔍 Recovery Evaluation
     |
Backup Worker    ✅ Recovered
     |
Validator        ✅ Completed
     |
Final Result     ✅ Generated
```

**Expected result:** When a compatible replacement passes recovery checks, the pipeline continues and can complete.

Actual results depend on worker availability, budgets, deadlines, and validation.

### Comparison

The Compare Results page helps demonstrate:

- Which stage failed.
- What happened without recovery.
- Whether a replacement was selected.
- Whether the protected pipeline completed.
- How much additional time recovery required.
- What recovery cost was recorded.
- Whether a final output was generated.

Controlled fault injection should be clearly distinguished from real model-provider failures.

---

## 🧠 Recovery Decision Algorithm

The recovery engine evaluates candidate workers through a policy-driven selection process.

### Step 1 — Failure Detection

Identify the failed stage and capture relevant error information.

### Step 2 — Compatibility Filtering

Check:

- Required capability.
- Input contract.
- Output contract.
- Required tools.
- Worker availability.

### Step 3 — Feasibility Evaluation

Check:

- Remaining simulated budget.
- Recovery expense estimate.
- Remaining deadline.
- Expected execution duration.
- Recovery attempt limits.

### Step 4 — Candidate Ranking

Select an optimization policy.

| Policy | Objective |
|---|---|
| Cost | Prefer lower expected recovery cost |
| Time | Prefer faster viable recovery |
| Balanced | Balance cost, time and estimated reliability |

The ranking uses configured and/or observed estimates, depending on the available agent data.

### Step 5 — Recovery Execution

The chosen backup attempts the failed stage using the preserved input and workflow context.

### Step 6 — Output Validation

Verify the output against the required contract.

### Step 7 — Workflow Continuation

When recovery succeeds, execute the remaining stages.

If recovery is rejected or exhausted, terminate safely and record the result.

---

## 🔬 Testing

The project includes automated testing using Pytest.

Run:

```bash
python -m pytest -q
```

Test coverage focuses on workflow creation, execution, failure detection, recovery eligibility, output contracts, simulated settlement, and comparison behavior.

Provider adapters can be mock-tested without credentials.

**Mocked API tests are not evidence of successful live provider integration.** Live provider verification requires accessible credentials and actual API calls.

---

## 🔐 Security

AgentBailout should be run in a trusted development environment.

Security precautions:

- Keep all API keys outside source code.
- Exclude `.env` files from Git.
- Do not commit live databases containing private task prompts.
- Restrict access to the development backend.
- Validate user inputs and model responses.
- Apply execution timeouts and bounded recovery attempts.
- Avoid unrestricted execution of AI-generated code.
- Do not confuse generated code reviews with executed software tests.

This MVP is not a production-hardened, multi-tenant system.

---

## ⚠️ Current Limitations

The project is under active development.

Important limitations include:

- Offline agents produce deterministic simulation outputs, not real model-generated research.
- Cloud LLM execution requires valid provider credentials and tested adapters.
- Simulated budgets and settlement entries are not real financial transactions.
- Input/output contract validation does not guarantee factual correctness.
- AI-generated code is not automatically proven correct or executable.
- Distributed orchestration, strong authentication and production-scale fault tolerance require further development.
- General automatic code repair and verified repair reuse are not guaranteed by the existing MVP.

Features should be described as implemented only after they have passed verification in the current repository version.

---

## 🔮 Future Scope

AgentBailout can evolve beyond recovery of LLM agents.

Potential applications:

- GitHub Actions and CI/CD failure recovery.
- Python application crash recovery.
- Data pipeline recovery.
- Automated deployment rollback.
- Cross-provider model failover.
- Intelligent timeout handling.
- Adaptive retry and hedged execution.
- Verified configuration repair.
- Persistent failure knowledge bases.
- Distributed workflow recovery.
- Enterprise observability and reliability analytics.

The long-term goal is to make AgentBailout a reusable **recovery control plane for automated systems**.

---

## 🏆 Project Highlights

**The core idea:** Do not waste an entire workflow because one agent fails.

AgentBailout brings together:

- Failure detection.
- Recovery feasibility analysis.
- Compatible replacement selection.
- Cost and deadline constraints.
- Preservation of completed work.
- Automatic workflow continuation.
- Transparent recovery history.
- Demonstrable with/without recovery comparison.

Our focus is not simply on finding an error, but on managing the complete recovery process.

---

## 👥 Team

Developed as a hackathon project exploring resilient AI orchestration, automated failure recovery, and cost-aware multi-agent execution.

---

## 📜 License

No license has been specified yet. Add a `LICENSE` file before declaring an open-source license or granting reuse permissions.

---

### AgentBailout 🛟

**Because one failed agent shouldn't mean a failed workflow.**
