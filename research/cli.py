from __future__ import annotations

import argparse
from pathlib import Path
from tqdm import tqdm
import json

from .config import settings
from .pipeline import run_for_url
from .oneclick import run_oneclick

# ✅ NUEVO: ZIP para importar en Notion (sin API)
from .pack import build_notion_import_zip


def _find_results_jsonl(out_dir: Path) -> Path:
    """
    Encuentra el JSONL que produce tu pipeline.
    Ajusta aquí si tu archivo se llama distinto.
    """
    candidates = [
        out_dir / "oneclick_results.jsonl",
        out_dir / "results.jsonl",
    ]
    for c in candidates:
        if c.exists():
            return c
    raise FileNotFoundError(
        f"No encontré results JSONL en {out_dir}. Busqué: {', '.join(str(x.name) for x in candidates)}"
    )


def _build_zip(out_dir: Path, topic: str) -> Path:
    results_jsonl = _find_results_jsonl(out_dir)
    zip_path = build_notion_import_zip(out_dir, topic=topic, results_jsonl=results_jsonl)
    return zip_path


def main():
    p = argparse.ArgumentParser(prog="research")
    sub = p.add_subparsers(dest="cmd", required=True)

    p_one = sub.add_parser("oneclick", help="Descubre fuentes (RSS+HN), investiga y guarda 1-click")
    p_one.add_argument("--topic", default="AI")
    p_one.add_argument("--days", type=int, default=7)
    p_one.add_argument("--limit", type=int, default=10)
    p_one.add_argument("--out", default=settings.default_out_dir)
    p_one.add_argument("--prompt", default="prompts/prompt_mcp_definitivo.txt")
    p_one.add_argument("--no-zip", action="store_true", help="No generar ZIP para Notion")

    p_url = sub.add_parser("url", help="Analiza una URL")
    p_url.add_argument("url")
    p_url.add_argument("--out", default=settings.default_out_dir)
    p_url.add_argument("--prompt", default="prompts/prompt_mcp_definitivo.txt")
    p_url.add_argument("--topic", default="single_url")
    p_url.add_argument("--no-zip", action="store_true", help="No generar ZIP para Notion")

    p_batch = sub.add_parser("batch", help="Analiza URLs desde un archivo (una por línea)")
    p_batch.add_argument("file")
    p_batch.add_argument("--out", default=settings.default_out_dir)
    p_batch.add_argument("--prompt", default="prompts/prompt_mcp_definitivo.txt")
    p_batch.add_argument("--topic", default="batch_run")
    p_batch.add_argument("--no-zip", action="store_true", help="No generar ZIP para Notion")

    # (Opcional) lo dejo por compatibilidad, pero ya no lo necesitas si no usarás la API
    p_notion = sub.add_parser("notion-sync", help="(Opcional) Crea páginas en Notion desde results.jsonl")
    p_notion.add_argument("jsonl")
    p_notion.add_argument("--dry-run", action="store_true")

    args = p.parse_args()

    if args.cmd == "oneclick":
        out_dir = Path(args.out)
        prompt_file = Path(args.prompt)

        run_oneclick(topic=args.topic, days=args.days, limit=args.limit, out_dir=out_dir, prompt_file=prompt_file)

        print("\nOK oneclick. Guardado en:", out_dir.resolve())

        if not args.no_zip:
            zip_path = _build_zip(out_dir, topic=args.topic)
            print("✅ ZIP listo para importar en Notion:", zip_path.resolve())
            print("En Notion: Settings → Import → ZIP")

        return

    if args.cmd in ("url", "batch"):
        out_dir = Path(args.out)
        prompt_file = Path(args.prompt)

        if args.cmd == "url":
            obj = run_for_url(args.url, out_dir=out_dir, prompt_file=prompt_file)
            print("\nOK. Guardado en:", out_dir.resolve())
            print("URL:", obj["url"])

            if not args.no_zip:
                zip_path = _build_zip(out_dir, topic=args.topic)
                print("✅ ZIP listo para importar en Notion:", zip_path.resolve())

        else:
            urls = [
                ln.strip()
                for ln in Path(args.file).read_text(encoding="utf-8").splitlines()
                if ln.strip() and not ln.strip().startswith("#")
            ]
            for u in tqdm(urls, desc="Research"):
                try:
                    run_for_url(u, out_dir=out_dir, prompt_file=prompt_file)
                except Exception as e:
                    print(f"[ERROR] {u}: {e}")

            print("\nOK batch. Guardado en:", out_dir.resolve())

            if not args.no_zip:
                zip_path = _build_zip(out_dir, topic=args.topic)
                print("✅ ZIP listo para importar en Notion:", zip_path.resolve())

        return

    elif args.cmd == "notion-sync":
        # (Opcional) Tu versión original aquí si quieres conservarla,
        # pero si vas full-import ZIP, puedes borrar este comando completo.
        jsonl = Path(args.jsonl)
        rows = [json.loads(line) for line in jsonl.read_text(encoding="utf-8").splitlines() if line.strip()]
        print(f"Leí {len(rows)} filas desde {jsonl}. (notion-sync ya no es necesario si importas ZIP).")
        print("Dry-run OK." if args.dry_run else "Sync (API) no ejecutado en esta versión.")
        return


if __name__ == "__main__":
    main()