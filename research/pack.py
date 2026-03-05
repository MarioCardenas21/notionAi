from __future__ import annotations
from pathlib import Path
import csv
import json
import zipfile
import re
from datetime import datetime


# -------------------------
# Helpers
# -------------------------

def safe_filename(s: str) -> str:
    s = re.sub(r"[^a-zA-Z0-9]+", "_", (s or "").strip()).strip("_")
    return (s[:120] if len(s) > 120 else s) or "item"


def _read_jsonl(path: Path):
    items = []

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


def _guess_title(obj: dict) -> str:
    for k in ("title", "page_title", "document_title", "name"):
        v = obj.get(k)

        if isinstance(v, str) and v.strip():
            return v.strip()

    url = obj.get("url") or "Sin_Titulo"
    return str(url)[:80]


def _pick_md_body(obj: dict) -> str:
    for k in ("result_md", "markdown", "output", "result", "analysis", "content", "text", "summary"):
        v = obj.get(k)

        if isinstance(v, str) and v.strip():
            return v.strip()

    return ""


def _build_md_page(title: str, url: str, md_body: str, *, created_at: str) -> str:

    if not md_body:
        md_body = "_Sin contenido generado por el modelo._"

    return f"""# {title}

**Fuente:** {url}  
**Generado:** {created_at}

---

{md_body}
"""


# -------------------------
# Main Builder
# -------------------------

def build_notion_import_zip(out_dir: Path, *, topic: str, results_jsonl: Path) -> Path:
    """
    Genera un ZIP importable por Notion (sin usar API)

    Contenido del ZIP:

    AI Research Notebook/
        00 - Índice.md
        01 - articulo.md
        02 - articulo.md
        sources.csv
    """

    out_dir = Path(out_dir)

    created_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    notebook_dir = out_dir / "AI Research Notebook"
    notebook_dir.mkdir(parents=True, exist_ok=True)

    items = _read_jsonl(results_jsonl)

    # -------------------------
    # Índice
    # -------------------------

    index_lines = [
        "# AI Research Notebook\n\n",
        f"**Topic:** {topic}\n\n",
        f"**Generado:** {created_at}\n\n",
        "---\n\n",
        "## Índice\n\n"
    ]

    # -------------------------
    # CSV de fuentes
    # -------------------------

    csv_path = notebook_dir / "sources.csv"

    with csv_path.open("w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)

        w.writerow(["n", "title", "url", "created_at"])

        for i, obj in enumerate(items, start=1):
            url = str(obj.get("url") or "N/A")
            title = _guess_title(obj)

            w.writerow([i, title, url, created_at])

    # -------------------------
    # Páginas Markdown
    # -------------------------

    for i, obj in enumerate(items, start=1):

        url = str(obj.get("url") or "N/A")

        title = _guess_title(obj)

        safe = safe_filename(title)

        md_body = _pick_md_body(obj)

        page_md = _build_md_page(title, url, md_body, created_at=created_at)

        page_name = f"{i:02d} - {safe}.md"

        (notebook_dir / page_name).write_text(page_md, encoding="utf-8")

        index_lines.append(f"- [{title}]({page_name})\n")

    (notebook_dir / "00 - Índice.md").write_text("".join(index_lines), encoding="utf-8")

    # -------------------------
    # Crear ZIP
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
# Compatibilidad con código antiguo
# -------------------------

def build_notion_upload_pack(out_dir: Path, *, topic: str, results_jsonl: Path) -> Path:
    """
    Alias para mantener compatibilidad con código viejo.
    """
    return build_notion_import_zip(out_dir, topic=topic, results_jsonl=results_jsonl)
