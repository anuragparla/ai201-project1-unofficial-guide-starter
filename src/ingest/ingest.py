"""Milestone 3 entry point: fetch -> parse -> clean -> verify.

Runs every source in the registry through the parser for its `kind`, writes the
cleaned plain text to documents/clean/<slug>.txt, and prints a verification
report so you can eyeball that the output is clean and only the wanted content
was kept BEFORE moving on to chunking (Milestone 3b).

Usage:
    python -m src.ingest.ingest                 # all sources
    python -m src.ingest.ingest --only 7 9      # just sources #7 and #9
    python -m src.ingest.ingest --force         # ignore raw cache, re-download
    python -m src.ingest.ingest --preview 600   # longer text preview
"""

import argparse
import io
import sys
from dataclasses import dataclass
from pathlib import Path

import pdfplumber

from . import cleaners
from .fetch import fetch
from .sources import Source, get_sources

CLEAN_DIR = Path("documents/clean")


@dataclass
class Document:
    source: Source
    text: str
    note: str = ""          # how it was obtained (e.g. "cache", "12 pages")

    @property
    def n_chars(self) -> int:
        return len(self.text)

    @property
    def n_words(self) -> int:
        return len(self.text.split())

    @property
    def est_tokens(self) -> int:
        # Rough heuristic (~1.3 tokens/word) just for a sanity gut-check.
        return int(self.n_words * 1.3)


# --------------------------------------------------------------------------- #
# Per-kind parsers
# --------------------------------------------------------------------------- #

def parse_html(src: Source, force: bool) -> Document:
    raw, tag = fetch(src.url, src.slug, binary=False, force=force)
    text = cleaners.clean_html(raw)
    return Document(src, text, note=tag)


def _extract_page(page, columns: int) -> str:
    """Extract a page's text, reading column-by-column for multi-column layouts.

    Single-column (columns=1) uses plain extraction. For columns>1 we crop the
    page into equal vertical strips and extract each left-to-right, so text from
    different columns isn't interleaved line-by-line.
    """
    if columns <= 1:
        return page.extract_text() or ""
    width = page.width
    parts = []
    for i in range(columns):
        x0 = width * i / columns
        x1 = width * (i + 1) / columns
        strip = page.within_bbox((x0, 0, x1, page.height))
        parts.append(strip.extract_text() or "")
    return "\n".join(parts)


def parse_pdf(src: Source, force: bool) -> Document:
    raw, tag = fetch(src.url, src.slug, binary=True, force=force)
    pages = []
    with pdfplumber.open(io.BytesIO(raw)) as pdf:
        for page in pdf.pages:
            pages.append(_extract_page(page, src.columns))
    text = cleaners.clean_pdf_text(pages)
    return Document(src, text, note=f"{tag}, {len(pages)} pages")


def parse_reddit(src: Source, force: bool) -> Document:
    raw, tag = fetch(src.url, src.slug, binary=False, force=force)
    text = cleaners.clean_reddit(raw, src.url)
    return Document(src, text, note=tag)


def parse_mbta(src: Source, force: bool) -> Document:
    base = src.url  # https://api-v3.mbta.com
    # Subway = light rail (type 0, Green) + heavy rail (type 1, Red/Orange/Blue).
    routes_json, t1 = fetch(
        f"{base}/routes?filter[type]=0,1", "10_mbta_routes", force=force
    )
    import json
    route_ids = [r["id"] for r in json.loads(routes_json).get("data", [])]
    stops_by_route = {}
    tags = {t1}
    for rid in route_ids:
        stops_json, t = fetch(
            f"{base}/stops?filter[route]={rid}",
            f"10_mbta_stops_{rid}",
            force=force,
        )
        stops_by_route[rid] = stops_json
        tags.add(t)
    text = cleaners.build_mbta_facts(routes_json, stops_by_route)
    tag = "cache" if tags == {"cache"} else "fetched"
    return Document(src, text, note=f"{tag}, {len(route_ids)} routes")


PARSERS = {
    "html": parse_html,
    "pdf": parse_pdf,
    "reddit": parse_reddit,
    "mbta": parse_mbta,
}


# --------------------------------------------------------------------------- #
# Orchestration + verification report
# --------------------------------------------------------------------------- #

def ingest_one(src: Source, force: bool) -> Document:
    return PARSERS[src.kind](src, force)


def write_clean(doc: Document) -> Path:
    CLEAN_DIR.mkdir(parents=True, exist_ok=True)
    path = CLEAN_DIR / f"{doc.source.slug}.txt"
    path.write_text(doc.text, encoding="utf-8")
    return path


def preview(text: str, n: int) -> str:
    snippet = text[:n].replace("\n", " ⏎ ")
    return snippet + (" …" if len(text) > n else "")


def main(argv=None):
    ap = argparse.ArgumentParser(description="Ingest & clean Student Housing RAG sources.")
    ap.add_argument("--only", type=int, nargs="*", help="source ids to run (default: all)")
    ap.add_argument("--force", action="store_true", help="bypass raw cache, re-download")
    ap.add_argument("--preview", type=int, default=400, help="preview char length")
    args = ap.parse_args(argv)

    sources = get_sources(only_ids=args.only)
    docs, failures = [], []

    for src in sources:
        try:
            doc = ingest_one(src, args.force)
            path = write_clean(doc)
            docs.append((doc, path))
        except Exception as err:  # noqa: BLE001 - report and continue
            failures.append((src, repr(err)))

    # ---- Report ----------------------------------------------------------- #
    print("\n" + "=" * 78)
    print("MILESTONE 3 — INGESTION & CLEANING VERIFICATION REPORT")
    print("=" * 78)

    for doc, path in docs:
        s = doc.source
        print(f"\n[#{s.id}] {s.name}")
        print(f"     kind={s.kind}  doc_type={s.doc_type}  date={s.source_date}  ({doc.note})")
        print(f"     chars={doc.n_chars:,}  words={doc.n_words:,}  ~tokens={doc.est_tokens:,}")
        print(f"     saved -> {path}")
        print(f"     preview: {preview(doc.text, args.preview)}")

    if failures:
        print("\n" + "-" * 78)
        print("FAILED SOURCES (need attention before chunking):")
        for src, err in failures:
            ext = "pdf" if src.kind == "pdf" else "json"
            print(f"  [#{src.id}] {src.name}")
            print(f"       reason: {err}")
            print(f"       fix:    open this URL in a browser:")
            print(f"               {src.url}")
            print(f"               save the file as: documents/raw/{src.slug}.{ext}")
            print(f"               then re-run ingestion (it will pick it up automatically).")

    # ---- Summary ---------------------------------------------------------- #
    total_words = sum(d.n_words for d, _ in docs)
    print("\n" + "=" * 78)
    print(f"SUMMARY: {len(docs)}/{len(sources)} sources ingested, "
          f"{len(failures)} failed.  Total words: {total_words:,} "
          f"(~{int(total_words * 1.3):,} tokens)")
    print("=" * 78)

    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
