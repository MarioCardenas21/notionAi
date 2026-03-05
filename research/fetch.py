from __future__ import annotations

import os
import requests
from bs4 import BeautifulSoup
import trafilatura

try:
    import certifi
except Exception:  # pragma: no cover
    certifi = None

DEFAULT_HEADERS = {
    "User-Agent": "AI-Tech-Research-System/1.0 (+local)"
}

def _session() -> requests.Session:
    """
    Session configurable por env:
    - REQUESTS_TRUST_ENV=0   -> ignora proxies/vars del entorno
    """
    s = requests.Session()
    trust_env = os.environ.get("REQUESTS_TRUST_ENV", "1").strip()
    if trust_env == "0":
        s.trust_env = False
    return s

def fetch_html(url: str, timeout: int = 30) -> str:
    """
    Descarga HTML.
    Env vars:
    - REQUESTS_INSECURE=1     -> verify=False (NO recomendado, solo si el sitio tiene SSL roto)
    - REQUESTS_CA_BUNDLE      -> requests usará ese CA bundle automáticamente
    - REQUESTS_TRUST_ENV=0    -> ignora proxies del entorno
    """
    insecure = os.environ.get("REQUESTS_INSECURE", "0").strip() == "1"

    # verify:
    # - si insecure -> False
    # - si hay certifi -> usa su bundle (mejor compatibilidad)
    # - si no -> True (sistema)
    if insecure:
        verify = False
    else:
        verify = certifi.where() if certifi else True

    s = _session()
    r = s.get(url, headers=DEFAULT_HEADERS, timeout=timeout, verify=verify)
    r.raise_for_status()
    return r.text

def extract_text(url: str, html: str) -> str:
    extracted = trafilatura.extract(
        html,
        url=url,
        include_comments=False,
        include_tables=True
    )
    if extracted and extracted.strip():
        return extracted.strip()

    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(["script", "style", "noscript", "header", "footer", "nav", "aside"]):
        tag.decompose()

    parts: list[str] = []
    for p in soup.find_all(["p", "li", "pre", "code"]):
        txt = p.get_text(" ", strip=True)
        if txt:
            parts.append(txt)

    return "\n".join(parts).strip()