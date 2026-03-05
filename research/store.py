from __future__ import annotations
import json
import sqlite3
from pathlib import Path
from datetime import datetime, timezone

SCHEMA = '''
CREATE TABLE IF NOT EXISTS research_runs (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  url TEXT NOT NULL,
  fetched_at TEXT NOT NULL,
  model TEXT NOT NULL,
  result_markdown TEXT NOT NULL
);
'''

def ensure_sqlite(db_path: Path) -> None:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(db_path) as con:
        con.execute(SCHEMA)
        con.commit()

def insert_run(db_path: Path, *, url: str, fetched_at: str, model: str, result_markdown: str) -> None:
    with sqlite3.connect(db_path) as con:
        con.execute(
            "INSERT INTO research_runs(url,fetched_at,model,result_markdown) VALUES (?,?,?,?)",
            (url, fetched_at, model, result_markdown),
        )
        con.commit()

def append_jsonl(jsonl_path: Path, obj: dict) -> None:
    jsonl_path.parent.mkdir(parents=True, exist_ok=True)
    with jsonl_path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(obj, ensure_ascii=False) + "\n")

def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()
