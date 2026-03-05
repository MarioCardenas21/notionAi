from __future__ import annotations
import requests
from .config import settings

OLLAMA_URL = "http://127.0.0.1:11434/api/generate"

_session = requests.Session()
_session.trust_env = False

def run_research(prompt_system: str, user_input: str, *, temperature: float = 0.0) -> str:
    model = settings.openai_model or "llama3.1:8b"

    full_prompt = f"""[SYSTEM]
{prompt_system}

[USER]
{user_input}
"""

    payload = {
        "model": model,
        "prompt": full_prompt,
        "stream": False,
        "options": {"temperature": temperature},
    }

    r = _session.post(
        OLLAMA_URL,
        json=payload,
        timeout=1800,
        headers={"Content-Type": "application/json"},
    )
    r.raise_for_status()
    return r.json().get("response", "")