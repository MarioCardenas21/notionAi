from __future__ import annotations
from dataclasses import dataclass
from datetime import datetime, timezone, timedelta
import requests
import feedparser

@dataclass
class SourceItem:
    title: str
    url: str
    published_at: str | None = None
    source: str | None = None

def _now_utc() -> datetime:
    return datetime.now(timezone.utc)

def _within_days(published: datetime, days: int) -> bool:
    return published >= _now_utc() - timedelta(days=days)

def discover_rss(topic: str, days: int = 7, limit: int = 10) -> list[SourceItem]:
    # RSS feeds (técnicos) – ajustables
    feeds = [
        ("arXiv cs.AI", "https://export.arxiv.org/rss/cs.AI"),
        ("arXiv cs.LG", "https://export.arxiv.org/rss/cs.LG"),
        ("OpenAI Blog", "https://openai.com/blog/rss.xml"),
        ("Google AI Blog", "https://blog.google/technology/ai/rss/"),
    ]

    items: list[SourceItem] = []
    t = topic.lower()

    for name, url in feeds:
        d = feedparser.parse(url)
        for e in d.entries:
            title = getattr(e, "title", "") or ""
            link = getattr(e, "link", "") or ""
            if not link:
                continue
            # keyword filter
            if t and t not in title.lower() and t not in (getattr(e, "summary", "") or "").lower():
                continue

            published_at = None
            # try published_parsed
            if getattr(e, "published_parsed", None):
                dt = datetime(*e.published_parsed[:6], tzinfo=timezone.utc)
                if not _within_days(dt, days):
                    continue
                published_at = dt.isoformat()
            items.append(SourceItem(title=title.strip(), url=link.strip(), published_at=published_at, source=name))

    # de-dup by url
    seen = set()
    out = []
    for it in items:
        if it.url in seen:
            continue
        seen.add(it.url)
        out.append(it)
        if len(out) >= limit:
            break
    return out

def discover_hn(topic: str, days: int = 7, limit: int = 10) -> list[SourceItem]:
    # HN Algolia Search API (gratis)
    # Nota: HN puede incluir artículos no oficiales; tu prompt filtrará marketing/no-técnico.
    q = topic or "AI"
    url = "https://hn.algolia.com/api/v1/search_by_date"
    params = {"query": q, "tags": "story", "hitsPerPage": str(max(limit, 20))}
    r = requests.get(url, params=params, timeout=30)
    r.raise_for_status()
    data = r.json()
    items: list[SourceItem] = []
    cutoff = _now_utc() - timedelta(days=days)
    for hit in data.get("hits", []):
        link = hit.get("url") or ""
        title = hit.get("title") or ""
        created = hit.get("created_at")  # ISO string
        if not link or not title or not created:
            continue
        try:
            dt = datetime.fromisoformat(created.replace("Z","+00:00"))
        except Exception:
            continue
        if dt < cutoff:
            continue
        items.append(SourceItem(title=title, url=link, published_at=dt.isoformat(), source="HackerNews"))
        if len(items) >= limit:
            break
    return items

def discover(topic: str, days: int = 7, limit: int = 10) -> list[SourceItem]:
    # Mezcla: RSS primero (más técnico), luego HN
    rss = discover_rss(topic, days=days, limit=limit)
    remaining = max(0, limit - len(rss))
    hn = discover_hn(topic, days=days, limit=remaining) if remaining else []
    return rss + hn
