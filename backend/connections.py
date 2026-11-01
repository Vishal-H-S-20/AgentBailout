"""Connection fingerprints contain no credential values."""
import hashlib
from backend.environment import credential,ollama_url

def fingerprint(name):
    value=ollama_url() if name=='ollama' else credential(name) or ''
    return hashlib.sha256(value.encode()).hexdigest()
