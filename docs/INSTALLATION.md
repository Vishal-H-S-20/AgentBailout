# Installation

Run commands from the repository root. Python 3.11+ is required. On this Windows workstation a local Python 3.12 was installed under `.python` because the system `python` command was an unusable Store alias.

```powershell
.\.python\python.exe -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m pytest -q --basetemp=.test-tmp
.\.venv\Scripts\python.exe -m uvicorn backend.main:app --host 127.0.0.1 --port 8000
```

On Ubuntu use `bash scripts/setup.sh`, `bash scripts/run_tests.sh` and `bash scripts/run_backend.sh`. Scripts can also be made executable with `chmod +x scripts/*.sh`. Ubuntu execution has not been verified on this Windows host.

If port 8000 is occupied, choose `--port 8001` and change the base URL in the demo script. A missing database is created at backend startup. For import errors confirm you are at the repository root and use `python -m uvicorn`. Dependencies require internet only during installation; the pipeline itself makes no network calls.
