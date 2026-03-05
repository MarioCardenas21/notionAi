from __future__ import annotations
import argparse
from pathlib import Path
from tqdm import tqdm
import json

from .config import settings
from .pipeline import run_for_url
from .oneclick import run_oneclick
from .notion import build_db_page_payload, md_as_blocks, create_page

def main():
    p = argparse.ArgumentParser(prog="research")
    sub = p.add_subparsers(dest="cmd", required=True)

    p_one = sub.add_parser("oneclick", help="Descubre fuentes (RSS+HN), investiga y guarda 1-click")
    p_one.add_argument("--topic", default="AI")
    p_one.add_argument("--days", type=int, default=7)
    p_one.add_argument("--limit", type=int, default=10)
    p_one.add_argument("--out", default=settings.default_out_dir)
    p_one.add_argument("--prompt", default="prompts/prompt_mcp_definitivo.txt")

    p_url = sub.add_parser("url", help="Analiza una URL")
    p_url.add_argument("url")
    p_url.add_argument("--out", default=settings.default_out_dir)
    p_url.add_argument("--prompt", default="prompts/prompt_mcp_definitivo.txt")

    p_batch = sub.add_parser("batch", help="Analiza URLs desde un archivo (una por línea)")
    p_batch.add_argument("file")
    p_batch.add_argument("--out", default=settings.default_out_dir)
    p_batch.add_argument("--prompt", default="prompts/prompt_mcp_definitivo.txt")

    p_notion = sub.add_parser("notion-sync", help="Crea páginas en Notion desde results.jsonl")
    p_notion.add_argument("jsonl")
    p_notion.add_argument("--dry-run", action="store_true")

    args = p.parse_args()

    if args.cmd == "oneclick":
        out_dir = Path(args.out)
        prompt_file = Path(args.prompt)
        results = run_oneclick(topic=args.topic, days=args.days, limit=args.limit, out_dir=out_dir, prompt_file=prompt_file)
        print("\nOK oneclick. Guardado en:", out_dir.resolve())
        print("Resultados:", results)

    if args.cmd in ("url", "batch"):
        out_dir = Path(args.out)
        prompt_file = Path(args.prompt)

        if args.cmd == "url":
            obj = run_for_url(args.url, out_dir=out_dir, prompt_file=prompt_file)
            print("\nOK. Guardado en:", out_dir.resolve())
            print("URL:", obj["url"])
        else:
            urls = [ln.strip() for ln in Path(args.file).read_text(encoding="utf-8").splitlines() if ln.strip() and not ln.strip().startswith("#")]
            for u in tqdm(urls, desc="Research"):
                try:
                    run_for_url(u, out_dir=out_dir, prompt_file=prompt_file)
                except Exception as e:
                    print(f"[ERROR] {u}: {e}")
            print("\nOK batch. Guardado en:", out_dir.resolve())

    elif args.cmd == "notion-sync":
        jsonl = Path(args.jsonl)
        rows = [json.loads(line) for line in jsonl.read_text(encoding="utf-8").splitlines() if line.strip()]
        for r in tqdm(rows, desc="Notion"):
            title = f"Research: {r['url']}"
            props = {
                "URL": {"url": r["url"]},
                "Model": {"rich_text": [{"text": {"content": r.get("model","")}}]},
            }
            blocks = md_as_blocks(r["result_markdown"])
            payload = build_db_page_payload(title=title, properties=props, blocks=blocks)
            if args.dry_run:
                continue
            try:
                create_page(payload)
            except Exception as e:
                print(f"[ERROR Notion] {r['url']}: {e}")

        print("Dry-run OK." if args.dry_run else "Sync a Notion finalizado.")

if __name__ == "__main__":
    main()
