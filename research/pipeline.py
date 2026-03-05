from __future__ import annotations

from pathlib import Path
from bs4 import BeautifulSoup

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


# -------------------------
# ✅ NEW: Title extraction
# -------------------------

def _clean_title(s: str) -> str:
    s = (s or "").strip()
    s = " ".join(s.split())
    return s[:180]


def extract_title_from_html(url: str, html: str) -> str:
    """
    Título humano para archivos/índice:
    Prioridad:
      1) og:title
      2) twitter:title
      3) h1
      4) <title>
    """
    if not html:
        return ""

    soup = BeautifulSoup(html, "html.parser")

    def meta_prop(prop: str) -> str:
        tag = soup.find("meta", attrs={"property": prop})
        if tag and tag.get("content"):
            return _clean_title(tag["content"])
        return ""

    def meta_name(name: str) -> str:
        tag = soup.find("meta", attrs={"name": name})
        if tag and tag.get("content"):
            return _clean_title(tag["content"])
        return ""

    # 1) OG
    t = meta_prop("og:title")
    if t:
        return t

    # 2) Twitter
    t = meta_name("twitter:title")
    if t:
        return t

    # 3) H1
    h1 = soup.find("h1")
    if h1:
        t = _clean_title(h1.get_text(" ", strip=True))
        if t:
            return t

    # 4) <title>
    if soup.title and soup.title.string:
        t = _clean_title(soup.title.string)
        if t:
            return t

    return ""


def build_notion_payload_stub(url: str, md: str, *, title: str = "") -> str:
    import json
    payload = {
        "Title": title or "TECH_RESEARCH_RESULT",
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
    title = extract_title_from_html(url, html)  # ✅ NEW

    text = extract_text(url, html)

    prompt_system = load_prompt(prompt_file)
    result_md = run_research(prompt_system, build_user_input(url, text), temperature=0.0)

    fetched_at = now_iso()

    jsonl_path = out_dir / "results.jsonl"
    db_path = out_dir / "results.sqlite"
    ensure_sqlite(db_path)
    insert_run(
        db_path,
        url=url,
        fetched_at=fetched_at,
        model=settings.openai_model,
        result_markdown=result_md
    )

    # ✅ NEW: guardar title en results.jsonl
    obj = {
        "url": url,
        "title": title,  # <--- clave para que pack.py ponga nombres humanos
        "fetched_at": fetched_at,
        "model": settings.openai_model,
        "extracted_chars": len(text),
        "result_markdown": result_md,
    }
    append_jsonl(jsonl_path, obj)

    notion_dir = out_dir / "notion_payloads"
    notion_dir.mkdir(exist_ok=True)
    (notion_dir / (safe_filename(url) + ".json")).write_text(
        build_notion_payload_stub(url, result_md, title=title),
        encoding="utf-8"
    )

    return obj