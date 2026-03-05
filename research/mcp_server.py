from __future__ import annotations
import json
import sys
from pathlib import Path

from .oneclick import run_oneclick

PROMPT_FILE = Path("prompts/prompt_mcp_definitivo.txt")
OUT_DIR = Path("out")

TOOLS = [
    {
        "name": "research.one_click",
        "description": "Descubre fuentes (RSS+HN) sobre un tema, investiga N links y devuelve la ruta del ZIP listo para Notion.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "topic": {"type": "string"},
                "days": {"type": "integer"},
                "limit": {"type": "integer"},
                "out_dir": {"type": "string"}
            },
            "required": ["topic"]
        }
    }
]

def send(obj: dict):
    sys.stdout.write(json.dumps(obj, ensure_ascii=False) + "\n")
    sys.stdout.flush()

def main():
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            req = json.loads(line)
        except Exception:
            continue

        method = req.get("method")
        if method == "tools/list":
            send({"jsonrpc": "2.0", "id": req.get("id"), "result": {"tools": TOOLS}})
            continue

        if method == "tools/call":
            params = req.get("params") or {}
            name = params.get("name")
            args = params.get("arguments") or {}

            if name != "research.one_click":
                send({"jsonrpc": "2.0", "id": req.get("id"), "error": {"code": -32601, "message": "Tool not found"}})
                continue

            topic = args.get("topic")
            days = int(args.get("days") or 7)
            limit = int(args.get("limit") or 10)
            out_dir = Path(args.get("out_dir") or OUT_DIR)

            try:
                results_path = run_oneclick(topic=topic, days=days, limit=limit, out_dir=out_dir, prompt_file=PROMPT_FILE)
                packs = sorted(out_dir.glob("notion_upload_pack_*.zip"), key=lambda p: p.stat().st_mtime, reverse=True)
                pack_path = packs[0] if packs else results_path
                send({"jsonrpc": "2.0", "id": req.get("id"), "result": {"content": [{"type": "text", "text": str(pack_path)}]}})
            except Exception as e:
                send({"jsonrpc": "2.0", "id": req.get("id"), "error": {"code": -32000, "message": str(e)}})
            continue

        send({"jsonrpc": "2.0", "id": req.get("id"), "error": {"code": -32601, "message": "Method not found"}})

if __name__ == "__main__":
    main()