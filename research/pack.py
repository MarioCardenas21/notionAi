from __future__ import annotations

from pathlib import Path
import csv
import json
import zipfile
import re
from datetime import datetime
from urllib.parse import urlparse


# -------------------------
# Helpers
# -------------------------

def safe_filename(s: str) -> str:
    s = re.sub(r"[^a-zA-Z0-9]+", "_", (s or "").strip()).strip("_")
    return (s[:120] if len(s) > 120 else s) or "item"


def _read_jsonl(path: Path) -> list[dict]:
    items: list[dict] = []
    if not path.exists():
        return items

    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            items.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return items


def _pick_md_body(obj: dict) -> str:
    # Ajusta según cómo tu pipeline guarde la salida del LLM
    for k in ("result_markdown", "result_md", "markdown", "output", "result", "analysis", "content", "text", "summary"):
        v = obj.get(k)
        if isinstance(v, str) and v.strip():
            return v.strip()
    return ""


def _md_first_h1(md: str) -> str:
    """
    Devuelve el primer encabezado H1 "# ..." si existe.
    """
    if not md:
        return ""
    for line in md.splitlines():
        line = line.strip()
        if line.startswith("# "):
            t = line[2:].strip()
            return t
    return ""


def _url_fallback_title(url: str) -> str:
    """
    Título fallback: dominio + path limpio.
    """
    try:
        p = urlparse(url)
        host = (p.netloc or "").replace("www.", "")
        path = (p.path or "").strip("/")
        if not path:
            return host or "Sin título"
        last = path.split("/")[-1]
        last = last.replace("-", " ").replace("_", " ").strip()
        # Capitaliza simple
        last = last[:1].upper() + last[1:] if last else last
        return f"{last} ({host})" if host else last
    except Exception:
        return str(url)[:80]


def _guess_title(obj: dict, md_body: str) -> str:
    """
    Prioridad:
    1) obj["title"] / similares
    2) primer "# " del markdown
    3) fallback desde URL
    """
    for k in ("title", "page_title", "document_title", "name"):
        v = obj.get(k)
        if isinstance(v, str) and v.strip():
            return v.strip()

    h1 = _md_first_h1(md_body)
    if h1:
        return h1

    url = str(obj.get("url") or "Sin_Titulo")
    return _url_fallback_title(url)


def _build_md_page(title: str, url: str, md_body: str, *, created_at: str) -> str:
    if not md_body:
        md_body = "_Sin contenido generado por el modelo._"

    # Si el markdown ya trae un H1, lo dejamos, pero evitamos duplicar:
    # (si md ya empieza con "# ", no ponemos otro)
    md_title = _md_first_h1(md_body)
    if md_title:
        header = ""
    else:
        header = f"# {title}\n\n"

    return f"""{header}**Fuente:** {url}  
**Generado:** {created_at}

---

{md_body}
"""


# -------------------------
# Main Builder
# -------------------------

def build_notion_import_zip(
    out_dir: Path,
    *,
    topic: str,
    results_jsonl: Path,
    notebook_name: str | None = None,
    include_sources_csv: bool = False,
) -> Path:
    """
    Genera un ZIP importable por Notion (SIN API).

    Crea solo una carpeta de notebook con .md:
      Notion Notebook - <topic>/
        00 - Índice.md
        01 - <titulo>.md
        02 - <titulo>.md
        (opcional) sources.csv
    """
    out_dir = Path(out_dir)
    created_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    folder = notebook_name or f"Notion Notebook - {topic}"
    notebook_dir = out_dir / folder
    notebook_dir.mkdir(parents=True, exist_ok=True)

    items = _read_jsonl(results_jsonl)

    # -------------------------
    # Generar páginas y construir índice
    # -------------------------
    index_lines: list[str] = [
        "# AI Research Notebook\n\n",
        f"**Tema:** {topic}\n\n",
        f"**Generado:** {created_at}\n\n",
        "---\n\n",
        "## Índice\n\n"
    ]

    rows_for_csv: list[tuple[int, str, str, str]] = []

    for i, obj in enumerate(items, start=1):
        url = str(obj.get("url") or "N/A")
        md_body = _pick_md_body(obj)

        title = _guess_title(obj, md_body)
        safe = safe_filename(title)

        page_name = f"{i:02d} - {safe}.md"
        page_md = _build_md_page(title, url, md_body, created_at=created_at)
        (notebook_dir / page_name).write_text(page_md, encoding="utf-8")

        # Índice: lista numerada (Notion la renderiza mejor, sin “List” raro)
        index_lines.append(f"{i}. {title}\n")
        index_lines.append(f"   - {url}\n")

        rows_for_csv.append((i, title, url, created_at))

    (notebook_dir / "00 - Índice.md").write_text("".join(index_lines), encoding="utf-8")

    # -------------------------
    # sources.csv (opcional)
    # -------------------------
    if include_sources_csv:
        csv_path = notebook_dir / "sources.csv"
        with csv_path.open("w", encoding="utf-8", newline="") as f:
            w = csv.writer(f)
            w.writerow(["n", "title", "url", "created_at"])
            for row in rows_for_csv:
                w.writerow(list(row))

    # -------------------------
    # ZIP
    # -------------------------
    zip_path = out_dir / f"notion_import_{safe_filename(topic)}.zip"
    if zip_path.exists():
        zip_path.unlink()

    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as z:
        for p in notebook_dir.rglob("*"):
            if p.is_file():
                z.write(p, arcname=str(p.relative_to(out_dir)))

    return zip_path


# -------------------------
# Backwards compat
# -------------------------

def build_notion_upload_pack(out_dir: Path, *, topic: str, results_jsonl: Path) -> Path:
    # Alias para compatibilidad con imports viejos
    return build_notion_import_zip(out_dir, topic=topic, results_jsonl=results_jsonl)