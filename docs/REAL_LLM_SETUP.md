# Real provider setup — Phase B

From `C:\Users\Vishal\Documents\ChatGPT\agentathon`:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
$env:AGENTBAILOUT_DATABASE_URL='sqlite:///./phase3-demo.db'
# Set only keys for providers you authorize. Use your own accessible model IDs.
$env:OPENAI_API_KEY='<your API key>'
$env:OPENAI_MODEL='<your accessible model ID>'
$env:GEMINI_API_KEY='<your API key>'
$env:GEMINI_MODEL='<your accessible model ID>'
$env:ANTHROPIC_API_KEY='<your API key>'
$env:ANTHROPIC_MODEL='<your accessible model ID>'
.\.venv\Scripts\python.exe -m uvicorn backend.main:app --host 127.0.0.1 --port 8003
```

Set secrets using your server's secret injection mechanism; placeholders above are not working credentials. GOOGLE_API_KEY is also supported for Gemini and takes precedence. ChatGPT subscriptions do not supply OpenAI API credentials or API billing.

In another terminal:

```powershell
$env:AGENTBAILOUT_BACKEND_URL='http://127.0.0.1:8003'
.\.venv\Scripts\python.exe -m streamlit run dashboard/app.py --server.port 8501 --server.address 127.0.0.1 --server.headless true
```

Open http://127.0.0.1:8501. Settings & History → AI Providers → Discover models → select → Use selected model → Test Provider. Discovery is not a generation test. Provider tests submit small real requests and can incur charges. Keys never go in agent definitions or SQLite records. `.env.example` is documentation and is not auto-loaded.

Optional Ollama: install/run it separately, pull a desired model, set OLLAMA_URL (default http://127.0.0.1:11434), then discover/test it. No local model installation is assumed.

```powershell
.\.venv\Scripts\python.exe scripts/smoke_real_providers.py
```

Smoke tests require both a key and explicit PROVIDER_MODEL; absent settings yield SKIPPED. All three cloud tests were skipped at this checkpoint because credentials were absent. See [audit, test results and limitations](AGENTBAILOUT4_PHASE_AB.md).
