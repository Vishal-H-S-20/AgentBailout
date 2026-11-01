"""Backend-only environment loading. Explicit process variables take precedence."""
import os
from pathlib import Path
from dotenv import load_dotenv

ROOT=Path(__file__).resolve().parents[1]

def load_environment(path=None):
    load_dotenv(dotenv_path=Path(path) if path else ROOT/'.env',override=False,encoding="utf-8-sig")

load_environment()

def credential(name):
    names={'openai':['OPENAI_API_KEY'],'gemini':['GEMINI_API_KEY','GOOGLE_API_KEY'],
           'groq':['GROQ_API_KEY'],'anthropic':['ANTHROPIC_API_KEY']}.get(name,[])
    for variable in names:
        value=os.getenv(variable,'').strip()
        if len(value)>1 and value[0]==value[-1] and value[0] in {'\"',"'"}: value=value[1:-1].strip()
        if value and not value.startswith('<') and value.lower() not in {'your-api-key','your_api_key','changeme'}:
            return value
    return None

def ollama_url():
    return (os.getenv('OLLAMA_BASE_URL') or os.getenv('OLLAMA_URL') or 'http://127.0.0.1:11434').strip().rstrip('/')
