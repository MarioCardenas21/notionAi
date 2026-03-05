from __future__ import annotations
from openai import OpenAI
from .config import settings

def get_client() -> OpenAI:
    if not settings.openai_api_key:
        raise RuntimeError("Falta OPENAI_API_KEY en el entorno (.env).")
    return OpenAI(api_key=settings.openai_api_key)

def run_research(prompt_system: str, user_input: str, *, temperature: float = 0.0) -> str:
    client = get_client()
    try:
        resp = client.responses.create(
            model=settings.openai_model,
            instructions=prompt_system,
            input=user_input,
            temperature=temperature,
        )
        if getattr(resp, "output_text", None):
            return resp.output_text
        return str(resp)
    except Exception:
        cc = client.chat.completions.create(
            model=settings.openai_model,
            messages=[
                {"role": "system", "content": prompt_system},
                {"role": "user", "content": user_input},
            ],
            temperature=temperature,
        )
        return cc.choices[0].message.content
