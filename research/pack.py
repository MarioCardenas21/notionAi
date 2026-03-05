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
    # ✅ tu pipeline guarda "result_markdown" (según pipeline.py que pegaste)
    for k in ("result_markdown", "result_md", "markdown", "output", "result", "analysis", "content", "text", "summary"):
        v = obj.get(k)
        if isinstance(v, str) and v.strip():
            return v.strip()
    return ""


def _guess_title_from_md(md_body: str) -> str | None:
    """
    Intenta sacar el título desde el contenido:
    - primer encabezado H1 '# ...'
    - o 'Title:' / 'Título:' en las primeras líneas
    """
    if not md_body:
        return None

    lines = [ln.strip() for ln in md_body.splitlines() if ln.strip()]
    if not lines:
        return None

    # 1) Primer H1
    for ln in lines[:60]:
        if ln.startswith("# "):
            t = ln[2:].strip()
            if t:
                return t

    # 2) Formato "Title: X" o "Título: X"
    for ln in lines[:60]:
        m = re.match(r"^(Title|Título)\s*:\s*(.+)$", ln, flags=re.IGNORECASE)
        if m:
            t = m.group(2).strip()
            if t:
                return t

    return None


def _guess_title(obj: dict, md_body: str) -> str:
    """
    Prioridad:
    1) Título desde el markdown (lo más confiable para Notion)
    2) Campos del JSONL (si existen)
    3) URL como fallback
    """
    t = _guess_title_from_md(md_body)
    if t:
        return t

    for k in ("title", "page_title", "document_title", "name"):
        v = obj.get(k)
        if isinstance(v, str) and v.strip():
            return v.strip()

    url = obj.get("url") or "Sin_Titulo"
    return str(url)[:80]


def _build_md_page(title: str, url: str, md_body: str, *, created_at: str) -> str:
    if not md_body:
        md_body = "_Sin contenido generado por el modelo._"

    # Nota: Evitamos links complicados; Notion lo importará como texto normal.
    return f"""# {title}

**Fuente:** {url}  
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
    include_sources_csv: bool = True,
    notebook_name: str | None = None,
) -> Path:
    """
    Genera un ZIP importable por Notion (sin API), aislado por ejecución.

    Crea:
      <out_dir>/<notebook_dir>/
        00 - Indice.md
        01 - ...
        sources.csv (opcional)

    Devuelve:
      <out_dir>/notion_import_<topic>_<timestamp>.zip
    """
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    created_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    ts_zip = datetime.now().strftime("%Y%m%d_%H%M%S")

    items = _read_jsonl(results_jsonl)

    # ✅ Nombre de carpeta único y bonito
    if notebook_name is None:
        notebook_name = f"AI Research Notebook - {topic} - {ts_zip}"
    notebook_dir = out_dir / notebook_name
    notebook_dir.mkdir(parents=True, exist_ok=True)

    # -------------------------
    # Construcción de páginas + índice (con títulos reales)
    # -------------------------
    index_lines = [
        "# AI Research Notebook\n\n",
        f"**Topic:** {topic}\n\n",
        f"**Generado:** {created_at}\n\n",
        "---\n\n",
        "## Índice\n\n",
        "_Nota: Notion a veces no resuelve links relativos entre .md importados. Por eso este índice lista Título + Archivo._\n\n",
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

        # ✅ índice SIN link (para evitar que Notion lo rompa)
        index_lines.append(f"- {title}  _(archivo: {page_name})_\n")

        rows_for_csv.append((i, title, url, created_at))

    (notebook_dir / "00 - Indice.md").write_text("".join(index_lines), encoding="utf-8")

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
    # ZIP FINAL (solo el cuaderno)
    # -------------------------
    zip_path = out_dir / f"notion_import_{safe_filename(topic)}_{ts_zip}.zip"
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