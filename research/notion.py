from __future__ import annotations
import requests
from .config import settings

NOTION_API = "https://api.notion.com/v1"

def notion_headers() -> dict:
    if not settings.notion_token:
        raise RuntimeError("Falta NOTION_TOKEN en .env")
    return {
        "Authorization": f"Bearer {settings.notion_token}",
        "Notion-Version": settings.notion_version,
        "Content-Type": "application/json",
    }

def create_page(payload: dict) -> dict:
    r = requests.post(f"{NOTION_API}/pages", headers=notion_headers(), json=payload, timeout=30)
    r.raise_for_status()
    return r.json()

def build_db_page_payload(*, title: str, properties: dict, blocks: list) -> dict:
    if not settings.notion_database_id:
        raise RuntimeError("Falta NOTION_DATABASE_ID en .env")
    return {
        "parent": {"database_id": settings.notion_database_id},
        "properties": {
            "Name": {"title": [{"text": {"content": title}}]},
            **properties,
        },
        "children": blocks,
    }

def md_as_blocks(md: str, max_chars: int = 1800) -> list:
    chunks = []
    buf = (md or "").strip()
    while buf:
        chunk = buf[:max_chars]
        buf = buf[max_chars:]
        chunks.append({
            "object": "block",
            "type": "paragraph",
            "paragraph": {"rich_text": [{"type": "text", "text": {"content": chunk}}]},
        })
    return chunks
