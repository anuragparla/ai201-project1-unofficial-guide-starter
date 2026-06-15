"""Per-source-type cleaning.

Each function takes raw downloaded content and returns clean plain text:
boilerplate stripped, whitespace normalized, ready to chunk. Keeping the
cleaners separate (one per `kind`) is what lets a tabular source like the
MBTA be handled completely differently from a legal PDF.
"""

import json
import re

from bs4 import BeautifulSoup

# Tags whose contents are never useful body text.
_DROP_TAGS = [
    "script", "style", "noscript", "nav", "header", "footer", "aside",
    "form", "button", "svg", "iframe",
]

# Common nav/boilerplate lines we never want, matched case-insensitively.
_BOILERPLATE_RE = re.compile(
    r"^(skip to (main )?content|menu|search|share this|print this page|"
    r"back to top|cookie|subscribe|sign in|log ?in|©|copyright)\b",
    re.IGNORECASE,
)


def _collapse_whitespace(text: str) -> str:
    """Collapse runs of spaces and blank lines, trim each line."""
    # Form fill-in blanks (runs of underscores/dots/dashes) carry no meaning and
    # otherwise bloat chunks — e.g. "Name:______ Phone:______" -> "Name: Phone:".
    text = re.sub(r"_{2,}", " ", text)
    text = re.sub(r"(?<=\s)[.\-]{3,}(?=\s)", " ", text)
    lines = [re.sub(r"[ \t ]+", " ", ln).strip() for ln in text.splitlines()]
    # Drop boilerplate lines and very short noise lines (lone bullets, etc.).
    kept = []
    for ln in lines:
        if not ln:
            kept.append("")
            continue
        if _BOILERPLATE_RE.match(ln):
            continue
        kept.append(ln)
    text = "\n".join(kept)
    text = re.sub(r"\n{3,}", "\n\n", text)  # max one blank line between blocks
    return text.strip()


def clean_html(raw: str) -> str:
    """Strip an HTML page down to readable body text."""
    soup = BeautifulSoup(raw, "lxml")
    for tag in soup(_DROP_TAGS):
        tag.decompose()
    # Prefer a <main>/<article> region if the page marks one.
    root = soup.find("main") or soup.find("article") or soup.body or soup
    # Use newline separators so headings/paragraphs stay on their own lines.
    text = root.get_text(separator="\n")
    return _collapse_whitespace(text)


def clean_pdf_text(pages: list[str]) -> str:
    """Clean text already extracted page-by-page from a PDF.

    Removes lone page numbers and de-duplicates repeated running headers/footers
    (lines that appear on most pages), which otherwise pollute every chunk.
    """
    # Find repeated header/footer lines: short lines appearing on many pages.
    from collections import Counter

    line_counts = Counter()
    for page in pages:
        for ln in {l.strip() for l in page.splitlines() if l.strip()}:
            line_counts[ln] += 1
    n_pages = max(len(pages), 1)
    repeated = {
        ln for ln, c in line_counts.items()
        if c >= max(3, n_pages * 0.5) and len(ln) < 80
    }

    cleaned_pages = []
    for page in pages:
        out_lines = []
        for ln in page.splitlines():
            s = ln.strip()
            if not s:
                out_lines.append("")
                continue
            if s in repeated:
                continue
            if re.fullmatch(r"(page\s*)?\d{1,3}(\s*of\s*\d{1,3})?", s, re.IGNORECASE):
                continue  # lone page number
            if re.search(r"\.{4,}\s*\d*\s*$", s):
                continue  # table-of-contents dotted-leader line ("Pets ..... 17")
            out_lines.append(ln)
        cleaned_pages.append("\n".join(out_lines))

    text = "\n\n".join(cleaned_pages)
    # Rejoin words broken across line wraps with a hyphen.
    text = re.sub(r"(\w)-\n(\w)", r"\1\2", text)
    return _collapse_whitespace(text)


def clean_reddit(raw: str, url: str) -> str:
    """Parse Reddit JSON into plain text.

    Handles every shape Reddit returns:
      - wiki page:        {"kind":"wikipage","data":{"content_md": "..."}}
      - search / listing: {"data":{"children":[{"kind":"t3","data":{...}}]}}
      - post + comments:  [<post Listing>, <comments Listing>]  (thread permalink)
    Comment trees are walked recursively (nested `replies`).
    """
    data = json.loads(raw)
    blocks: list[str] = []
    _walk_reddit(data, blocks)
    return _collapse_whitespace("\n\n".join(b for b in blocks if b.strip()))


def _walk_reddit(node, blocks: list[str]) -> None:
    """Recursively collect post titles, selftext, and comment bodies."""
    if isinstance(node, list):
        for item in node:
            _walk_reddit(item, blocks)
        return
    if not isinstance(node, dict):
        return

    kind = node.get("kind")
    data = node.get("data", {}) or {}

    if kind == "wikipage":
        blocks.append(_strip_markdown(data.get("content_md", "")))
    elif kind == "Listing":
        _walk_reddit(data.get("children", []), blocks)
    elif kind == "t3":  # a post / submission
        title = (data.get("title") or "").strip()
        body = (data.get("selftext") or "").strip()
        block = "\n".join(p for p in (title, body) if p)
        if block:
            blocks.append(_strip_markdown(block))
    elif kind == "t1":  # a comment
        body = (data.get("body") or "").strip()
        if body and body not in ("[deleted]", "[removed]"):
            blocks.append(_strip_markdown(body))
        _walk_reddit(data.get("replies", ""), blocks)  # nested replies
    # kind == "more" (load-more stubs) and anything else: ignore


def _strip_markdown(md: str) -> str:
    """Light markdown -> text: drop links syntax, headers markers, etc."""
    md = re.sub(r"!?\[([^\]]*)\]\([^)]*\)", r"\1", md)   # [text](url) -> text
    md = re.sub(r"^>+\s?", "", md, flags=re.MULTILINE)    # blockquotes
    md = re.sub(r"[*_`#]+", "", md)                        # emphasis/heading marks
    md = re.sub(r"&amp;", "&", md)
    md = re.sub(r"&gt;", ">", md)
    md = re.sub(r"&lt;", "<", md)
    return _collapse_whitespace(md)


def build_mbta_facts(routes_json: str, stops_by_route: dict[str, str]) -> str:
    """Turn MBTA v3 API route+stop data into natural-language facts.

    The schedules page is JS-rendered tabular data; per the Chunking Strategy we
    normalize it into sentences so it embeds and retrieves like the prose sources.
    """
    routes = json.loads(routes_json).get("data", [])
    facts = ["MBTA Subway lines serving Boston and Northeastern University:", ""]

    name_by_id = {}
    for r in routes:
        rid = r.get("id", "")
        attr = r.get("attributes", {})
        long_name = attr.get("long_name") or rid
        name_by_id[rid] = long_name

    for rid, stops_json in stops_by_route.items():
        stops = json.loads(stops_json).get("data", [])
        stop_names = [s.get("attributes", {}).get("name", "") for s in stops]
        stop_names = [n for n in stop_names if n]
        line = name_by_id.get(rid, rid)
        if not stop_names:
            continue
        facts.append(
            f"The {line} stops at the following stations: "
            + ", ".join(stop_names) + "."
        )
        # Northeastern-relevant callouts.
        near = [n for n in stop_names if "northeastern" in n.lower()
                or "ruggles" in n.lower() or "symphony" in n.lower()
                or "mass" in n.lower() and "ave" in n.lower()]
        if near:
            facts.append(
                f"The {line} serves these stops near Northeastern University: "
                + ", ".join(near) + "."
            )
        facts.append("")

    return _collapse_whitespace("\n".join(facts))
