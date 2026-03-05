from __future__ import annotations
from pathlib import Path
from datetime import datetime, timezone
import json

from .sources import discover
from .pipeline import run_for_url
from .pack import build_notion_upload_pack

def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()

def run_oneclick(*, topic: str, days: int, limit: int, out_dir: Path, prompt_file: Path) -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)
    items = discover(topic, days=days, limit=limit)

    results_path = out_dir / "oneclick_results.jsonl"
    # clear old
    if results_path.exists():
        results_path.unlink()

    for it in items:
        obj = run_for_url(it.url, out_dir=out_dir, prompt_file=prompt_file)
        # attach discovery metadata
        obj["discovered_title"] = it.title
        obj["discovered_published_at"] = it.published_at
        obj["discovered_source"] = it.source
        with results_path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(obj, ensure_ascii=False) + "\n")

    # Build a simple index file
    index = {
        "topic": topic,
        "days": days,
        "limit": limit,
        "generated_at": now_iso(),
        "count": len(items),
        "results_jsonl": str(results_path),
    }
    (out_dir / "oneclick_index.json").write_text(json.dumps(index, ensure_ascii=False, indent=2), encoding="utf-8")
    # build local Notion upload pack
    build_notion_upload_pack(out_dir, topic=topic, results_jsonl=results_path)
    return results_path
