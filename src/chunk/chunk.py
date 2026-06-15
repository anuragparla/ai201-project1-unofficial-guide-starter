"""Milestone 3b entry point: clean text -> metadata-tagged chunks.

Reads each cleaned document from documents/clean/<slug>.txt, splits it with the
token-budgeted structure-aware splitter, attaches the source metadata that
travels with every chunk downstream, writes all chunks to documents/chunks.jsonl,
and prints a verification report (per-source counts, token distribution, and the
overall chunk count to record in the README's Chunking Strategy).

Usage:
    python -m src.chunk.chunk                 # chunk all cleaned docs
    python -m src.chunk.chunk --only 7 9      # just sources #7 and #9
    python -m src.chunk.chunk --target 240 --overlap 40
    python -m src.chunk.chunk --show 3        # print 3 sample chunks
"""

import argparse
import json
import sys
from pathlib import Path

from ..ingest.sources import get_sources
from . import splitter

CLEAN_DIR = Path("documents/clean")
CHUNKS_FILE = Path("documents/chunks.jsonl")


def build_chunks(target: int, overlap: int, only_ids=None):
    """Return (chunks, skipped) for every source with a cleaned text file."""
    chunks, skipped = [], []
    for src in get_sources(only_ids=only_ids):
        path = CLEAN_DIR / f"{src.slug}.txt"
        if not path.exists():
            skipped.append(src)
            continue
        text = path.read_text(encoding="utf-8")
        pieces = splitter.chunk_text(text, target=target, overlap=overlap)
        for i, piece in enumerate(pieces):
            chunks.append({
                "chunk_id": f"{src.slug}#{i:04d}",
                "source_id": src.id,
                "source": src.name,
                "doc_type": src.doc_type,
                "url": src.url,
                "source_date": src.source_date,
                "chunk_index": i,
                "n_chars": len(piece),
                "n_tokens": splitter.count_tokens(piece),
                "text": piece,
            })
    return chunks, skipped


def write_jsonl(chunks, path: Path = CHUNKS_FILE):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for c in chunks:
            f.write(json.dumps(c, ensure_ascii=False) + "\n")


def _summary_stats(tokens):
    if not tokens:
        return (0, 0, 0)
    return (min(tokens), sum(tokens) // len(tokens), max(tokens))


def report(chunks, skipped, target, overlap, n_show):
    print("\n" + "=" * 78)
    print("MILESTONE 3b — CHUNKING VERIFICATION REPORT")
    print(f"target={target} tok  overlap={overlap} tok  "
          f"model_limit={splitter.MAX_TOKENS} content tok")
    print("=" * 78)

    by_source = {}
    for c in chunks:
        by_source.setdefault(c["source_id"], []).append(c)

    print(f"\n{'#':>2}  {'source':40} {'chunks':>6} {'tok min/avg/max':>16}")
    print("-" * 70)
    for sid in sorted(by_source):
        cs = by_source[sid]
        lo, avg, hi = _summary_stats([c["n_tokens"] for c in cs])
        name = cs[0]["source"][:38]
        print(f"{sid:>2}  {name:40} {len(cs):>6}   {lo:>3}/{avg:>3}/{hi:>3}")

    all_tok = [c["n_tokens"] for c in chunks]
    lo, avg, hi = _summary_stats(all_tok)
    over = [c for c in chunks if c["n_tokens"] > splitter.MODEL_MAX_SEQ - splitter.SPECIAL_TOKENS]

    print("\n" + "-" * 78)
    print(f"TOTAL CHUNKS: {len(chunks)}   tokens min/avg/max: {lo}/{avg}/{hi}")
    print(f"Chunks exceeding model limit ({splitter.MAX_TOKENS} content tok): "
          f"{len(over)}  ({'PASS' if not over else 'FAIL — would truncate!'})")
    if skipped:
        print("Skipped (no cleaned file yet): "
              + ", ".join(f"#{s.id}" for s in skipped))
    print(f"Written -> {CHUNKS_FILE}")

    if n_show and chunks:
        print("\n" + "-" * 78)
        print(f"SAMPLE CHUNKS (first {n_show}):")
        for c in chunks[:n_show]:
            print(f"\n  [{c['chunk_id']}]  doc_type={c['doc_type']}  "
                  f"tokens={c['n_tokens']}  chars={c['n_chars']}")
            preview = c["text"][:320].replace("\n", " ")
            print(f"    {preview}{' …' if len(c['text']) > 320 else ''}")
    print("=" * 78)


def main(argv=None):
    ap = argparse.ArgumentParser(description="Chunk cleaned documents.")
    ap.add_argument("--only", type=int, nargs="*", help="source ids (default: all)")
    ap.add_argument("--target", type=int, default=splitter.TARGET_TOKENS)
    ap.add_argument("--overlap", type=int, default=splitter.OVERLAP_TOKENS)
    ap.add_argument("--show", type=int, default=2, help="sample chunks to print")
    args = ap.parse_args(argv)

    chunks, skipped = build_chunks(args.target, args.overlap, only_ids=args.only)
    write_jsonl(chunks)
    report(chunks, skipped, args.target, args.overlap, args.show)
    return 0


if __name__ == "__main__":
    sys.exit(main())
