from __future__ import annotations
from .config import settings

def run_research(prompt_system: str, user_input: str, *, temperature: float = 0.0) -> str:
    """Enrutador de LLM:
    - Si LLM_PROVIDER=ollama -> usa Ollama local (gratis)
    - Si LLM_PROVIDER=openai -> usa OpenAI (paga)
    """
    provider = (settings.llm_provider or "ollama").lower()
    if provider == "openai":
        from .llm_openai import run_research as _run
        return _run(prompt_system, user_input, temperature=temperature)
    # default: ollama
    from .llm_ollama import run_research as _run
    return _run(prompt_system, user_input, temperature=temperature)
