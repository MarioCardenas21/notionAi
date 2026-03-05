from __future__ import annotations
import requests
from bs4 import BeautifulSoup
import trafilatura

DEFAULT_HEADERS = {
    "User-Agent": "AI-Tech-Research-System/1.0 (+local)"
}

def fetch_html(url: str, timeout: int = 30) -> str:
    r = requests.get(url, headers=DEFAULT_HEADERS, timeout=timeout)
    r.raise_for_status()
    return r.text

def extract_text(url: str, html: str) -> str:
    extracted = trafilatura.extract(html, url=url, include_comments=False, include_tables=True)
    if extracted and extracted.strip():
        return extracted.strip()

    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(["script", "style", "noscript", "header", "footer", "nav", "aside"]):
        tag.decompose()

    parts = []
    for p in soup.find_all(["p", "li", "pre", "code"]):
        txt = p.get_text(" ", strip=True)
        if txt:
            parts.append(txt)

    return "\n".join(parts).strip()
