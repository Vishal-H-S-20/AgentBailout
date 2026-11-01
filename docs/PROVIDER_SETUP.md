# Provider setup — AgentBailout 4.1

Credentials stay in the backend environment or root `.env`, never in browser fields, task records or Git. The backend loads `.env` from the repository root even when launched from a different directory. Existing process variables take precedence. UTF-8 BOM files, whitespace and paired quotation marks are handled. Placeholder values are not considered configured.

## Windows CMD startup

In **Command Prompt**, not PowerShell:

```bat
cd /d C:\Users\Vishal\Documents\ChatGPT\agentathon
.venv\Scripts\python.exe -m pip install -r requirements.txt
if not exist .env copy .env.example .env
notepad .env
```

Fill only the providers you authorize. Keep your existing database path:

```dotenv
AGENTBAILOUT_DATABASE_URL=sqlite:///./phase3-demo.db
OPENAI_API_KEY=<your OpenAI API key>
GEMINI_API_KEY=<your Gemini API key>
GROQ_API_KEY=<your Groq API key>
ANTHROPIC_API_KEY=<your Anthropic API key>
OLLAMA_BASE_URL=http://127.0.0.1:11434
```

Leave unused keys blank. Replace placeholders locally. GEMINI_API_KEY takes precedence over GOOGLE_API_KEY; the latter remains supported as an alias. OLLAMA_BASE_URL takes precedence over the legacy OLLAMA_URL. A ChatGPT subscription does not provide OpenAI API credentials or billing.

Start the backend from that CMD window:

```bat
.venv\Scripts\python.exe -m uvicorn backend.main:app --host 127.0.0.1 --port 8003
```

Or supply keys through process variables using CMD's quoting syntax:

```bat
set "GROQ_API_KEY=<your key>"
set "GROQ_MODEL=<an accessible model ID>"
```

Do not use `set KEY="value"` as the usual pattern; the recommended quoted form above avoids including quotation marks. Never post real credentials in chat or prompts. Restart the backend after editing `.env`; restarting only Streamlit cannot update the backend environment.

In a **second CMD window**:

```bat
cd /d C:\Users\Vishal\Documents\ChatGPT\agentathon
set "AGENTBAILOUT_BACKEND_URL=http://127.0.0.1:8003"
.venv\Scripts\python.exe -m streamlit run dashboard/app.py --server.port 8501 --server.address 127.0.0.1 --server.headless true
```

Open http://127.0.0.1:8501 → Settings & History → AI Providers. Confirm API key configured, Discover models, select an account-accessible model, Use selected model and Test Provider. The probe makes a real bounded plain-text generation request; it does not require structured-output support. It can incur charges. Discovery alone is not generation verification.

A successful check records its provider/model, timestamp and metadata server-side. Credential changes invalidate old verification. Availability is historical, not continuous monitoring. Wrong keys, denied models, rate limits and network failures produce sanitized errors; provider response bodies are not exposed. Keys accidentally supplied in saved prompts/configuration are rejected without echoing their values.

No cloud credentials were available in the development environment. Live OpenAI/Gemini/Groq/Claude checks are SKIPPED, not passed. Optional Ollama must be installed/running separately; no local generation was assumed.

```bat
.venv\Scripts\python.exe scripts/smoke_real_providers.py
```

For this script set the relevant OPENAI_MODEL, GEMINI_MODEL, GROQ_MODEL or ANTHROPIC_MODEL to an explicit accessible identifier. Missing keys/models are reported as SKIPPED. Do not commit `.env`; ignore rules cover `.env` and `.env.*` except the safe example.
