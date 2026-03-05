from __future__ import annotations
from pathlib import Path
from .config import settings
from .fetch import fetch_html, extract_text
from .llm import run_research
from .store import ensure_sqlite, insert_run, append_jsonl, now_iso

def load_prompt(prompt_file: Path) -> str:
    return prompt_file.read_text(encoding="utf-8")

def build_user_input(url: str, extracted_text: str) -> str:
    return f"""DOCUMENTACIÓN A ANALIZAR

URL:
{url}

CONTENIDO EXTRAÍDO:
{extracted_text}
"""

def safe_filename(url: str) -> str:
    import re
    s = re.sub(r"[^a-zA-Z0-9]+", "_", url).strip("_")
    return (s[:120] if len(s) > 120 else s) or "result"

def build_notion_payload_stub(url: str, md: str) -> str:
    import json
    payload = {
        "Title": "TECH_RESEARCH_RESULT",
        "Properties": {
            "Madurez": "UNVERIFIED",
            "Dificultad": "UNVERIFIED",
            "Relevancia": "UNVERIFIED",
            "Fuentes": [url],
            "Tags": ["mcp", "research"],
        },
        "Contenido": {
            "Research Brief (md)": md
        }
    }
    return json.dumps(payload, ensure_ascii=False, indent=2)

def run_for_url(url: str, *, out_dir: Path, prompt_file: Path) -> dict:
    out_dir.mkdir(parents=True, exist_ok=True)

    html = fetch_html(url)
    text = extract_text(url, html)

    prompt_system = load_prompt(prompt_file)
    result_md = run_research(prompt_system, build_user_input(url, text), temperature=0.0)

    fetched_at = now_iso()

    jsonl_path = out_dir / "results.jsonl"
    db_path = out_dir / "results.sqlite"
    ensure_sqlite(db_path)
    insert_run(db_path, url=url, fetched_at=fetched_at, model=settings.openai_model, result_markdown=result_md)

    obj = {
        "url": url,
        "fetched_at": fetched_at,
        "model": settings.openai_model,
        "extracted_chars": len(text),
        "result_markdown": result_md,
    }
    append_jsonl(jsonl_path, obj)

    notion_dir = out_dir / "notion_payloads"
    notion_dir.mkdir(exist_ok=True)
    (notion_dir / (safe_filename(url) + ".json")).write_text(build_notion_payload_stub(url, result_md), encoding="utf-8")

    return obj
