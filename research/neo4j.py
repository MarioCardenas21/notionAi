from __future__ import annotations
from pathlib import Path

def export_cypher(out_path: Path, *, tech_name: str, url: str) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    cypher = f'''
MERGE (t:Technology {{name: "{tech_name}"}})
MERGE (s:Source {{url: "{url}"}})
MERGE (t)-[:DOCUMENTED_BY]->(s);
'''.strip() + "\n"
    out_path.write_text(cypher, encoding="utf-8")
