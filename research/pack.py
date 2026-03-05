from __future__ import annotations
from pathlib import Path
import json, zipfile, re

def safe_filename(s: str) -> str:
    s = re.sub(r"[^a-zA-Z0-9]+", "_", s).strip("_")
    return (s[:120] if len(s) > 120 else s) or "item"

def build_notion_upload_pack(out_dir: Path, *, topic: str, results_jsonl: Path) -> Path:
    """Crea un ZIP local con todo lo necesario para Notion:
    - oneclick_index.json (metadata)
    - oneclick_results.jsonl (runs completos)
    - notion_payloads/*.json (payload sugerido por cada URL)
    """
    pack_dir = out_dir / "notion_upload_pack"
    pack_dir.mkdir(parents=True, exist_ok=True)

    # Copy index if exists
    index_path = out_dir / "oneclick_index.json"
    if index_path.exists():
        (pack_dir / "oneclick_index.json").write_text(index_path.read_text(encoding="utf-8"), encoding="utf-8")

    # Copy results
    (pack_dir / "oneclick_results.jsonl").write_text(results_jsonl.read_text(encoding="utf-8"), encoding="utf-8")

    # Copy payloads directory (if exists)
    payloads = out_dir / "notion_payloads"
    if payloads.exists():
        dst = pack_dir / "notion_payloads"
        dst.mkdir(exist_ok=True)
        for p in payloads.glob("*.json"):
            (dst / p.name).write_text(p.read_text(encoding="utf-8"), encoding="utf-8")

    # Create a simple README inside pack
    (pack_dir / "README.txt").write_text(
        "Este paquete contiene resultados de investigación (local) y payloads sugeridos para Notion.\n"
        "Si usas Notion API, puedes subir usando research.cli notion-sync <jsonl>.\n",
        encoding="utf-8"
    )

    zip_path = out_dir / f"notion_upload_pack_{safe_filename(topic)}.zip"
    if zip_path.exists():
        zip_path.unlink()

    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as z:
        for p in pack_dir.rglob("*"):
            if p.is_file():
                z.write(p, arcname=str(p.relative_to(out_dir)))

    return zip_path
