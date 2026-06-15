"""Network fetching with on-disk caching and a manual-drop fallback.

Raw downloads are cached under documents/raw/ so re-running ingestion does not
re-hit the network (polite to the servers, and lets you inspect exactly what
was downloaded). Pass force=True to bypass the cache.

Some sources sit behind anti-bot CDNs (mass.gov/Akamai, freeforms/Cloudflare,
Reddit) that reject automated clients by IP reputation regardless of headers.
For those, download the file once in a real browser and drop it into
documents/raw/ — see manual_path(). The cleaning pipeline then treats it
identically to a fetched file.
"""

import time
from pathlib import Path

import requests

# Browser-like headers. Plain python-requests UA gets 403'd by many CDNs;
# this clears the simpler bot filters (it will NOT defeat JS challenges).
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept": (
        "text/html,application/xhtml+xml,application/xml;q=0.9,"
        "application/pdf,application/json,*/*;q=0.8"
    ),
    "Accept-Language": "en-US,en;q=0.9",
    "Sec-Fetch-Dest": "document",
    "Sec-Fetch-Mode": "navigate",
    "Sec-Fetch-Site": "none",
    "Upgrade-Insecure-Requests": "1",
}

RAW_DIR = Path("documents/raw")
TIMEOUT = 30
RETRIES = 3
BACKOFF = 2  # seconds, multiplied by attempt number


def _raw_path(slug: str, binary: bool) -> Path:
    return RAW_DIR / f"{slug}{'.pdf' if binary else '.raw'}"


def manual_path(slug: str):
    """Return a manually-downloaded file for this slug, if one exists.

    Looks for documents/raw/<slug>.<ext> for common extensions. Lets you
    bypass a CDN block: download in a browser, save as e.g.
    documents/raw/07_ma_ag_tenant_rights.pdf, and re-run ingestion.
    """
    for ext in (".pdf", ".json", ".html", ".htm", ".txt", ".raw"):
        p = RAW_DIR / f"{slug}{ext}"
        if p.exists() and p.stat().st_size > 0:
            return p
    return None


def fetch(url: str, slug: str, *, binary: bool = False, force: bool = False):
    """Fetch a URL, caching raw bytes/text to documents/raw/.

    Resolution order: cache -> network -> manually-dropped file.
    Returns (content, source_tag) where source_tag is "cache" | "fetched"
    | "manual". `content` is bytes if binary else str.
    Raises requests.RequestException only if network fails AND no usable
    cached or manual file exists.
    """
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    path = _raw_path(slug, binary)

    if path.exists() and not force:
        data = path.read_bytes() if binary else path.read_text(encoding="utf-8")
        return data, "cache"

    last_err = None
    for attempt in range(1, RETRIES + 1):
        try:
            resp = requests.get(url, headers=HEADERS, timeout=TIMEOUT)
            resp.raise_for_status()
            if binary:
                path.write_bytes(resp.content)
                return resp.content, "fetched"
            text = resp.text
            path.write_text(text, encoding="utf-8")
            return text, "fetched"
        except requests.RequestException as err:
            last_err = err
            if attempt < RETRIES:
                time.sleep(BACKOFF * attempt)

    # Network failed — try a manually-downloaded file before giving up.
    manual = manual_path(slug)
    if manual:
        data = manual.read_bytes() if binary else manual.read_text(
            encoding="utf-8", errors="ignore"
        )
        return data, "manual"

    raise last_err
