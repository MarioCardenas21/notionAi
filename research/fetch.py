from __future__ import annotations

import os
import requests
from bs4 import BeautifulSoup

try:
    import certifi
except Exception:  # pragma: no cover
    certifi = None

# trafilatura debe ser opcional (porque puede romper por lxml_html_clean)
try:
    import trafilatura  # type: ignore
except Exception:  # pragma: no cover
    trafilatura = None

DEFAULT_HEADERS = {
    "User-Agent": "AI-Tech-Research-System/1.0 (+local)"
}


def _session() -> requests.Session:
    """
    Session configurable por env:
    - REQUESTS_TRUST_ENV=0   -> ignora proxies/vars del entorno (útil si hay proxy raro)
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
    - REQUESTS_INSECURE=1     -> verify=False (NO recomendado; solo si el sitio tiene SSL roto)
    - REQUESTS_CA_BUNDLE      -> requests lo usa automáticamente (si lo exportas)
    - REQUESTS_TRUST_ENV=0    -> ignora proxies del entorno
    """
    insecure = os.environ.get("REQUESTS_INSECURE", "0").strip() == "1"

    # verify:
    # - insecure -> False
    # - certifi disponible -> usa su bundle (mejor compatibilidad)
    # - si no -> True (certs del sistema)
    if insecure:
        verify = False
    else:
        verify = certifi.where() if certifi else True

    s = _session()
    r = s.get(url, headers=DEFAULT_HEADERS, timeout=timeout, verify=verify)
    r.raise_for_status()
    return r.text


def extract_text(url: str, html: str) -> str:
    """
    Intenta extraer texto principal:
    1) trafilatura (si está disponible y no falla)
    2) fallback BeautifulSoup limpiando el DOM
    """
    # 1) Trafi (si existe)
    if trafilatura is not None:
        try:
            extracted = trafilatura.extract(
                html,
                url=url,
                include_comments=False,
                include_tables=True,
            )
            if extracted and extracted.strip():
                return extracted.strip()
        except Exception:
            # si falla (p.ej. lxml_html_clean), seguimos con fallback
            pass

    # 2) Fallback BeautifulSoup
    soup = BeautifulSoup(html, "html.parser")

    # elimina ruido
    for tag in soup(["script", "style", "noscript", "header", "footer", "nav", "aside", "form"]):
        tag.decompose()

    parts: list[str] = []

    # incluye headings para mantener estructura básica
    for el in soup.find_all(["h1", "h2", "h3", "p", "li", "pre", "code"]):
        txt = el.get_text(" ", strip=True)
        if txt:
            parts.append(txt)

    return "\n".join(parts).strip()