"""Milestone 4a: embed chunks and load them into ChromaDB.

Reads documents/chunks.jsonl (produced by the chunking pipeline), embeds every
chunk's text with all-MiniLM-L6-v2, and stores the vectors in a persistent
ChromaDB collection together with the source metadata needed for attribution
(source document name + chunk position, plus doc_type/url/source_date).

Usage:
    python -m src.retrieval.embed            # (re)build the index
    python -m src.retrieval.embed --peek 3   # build, then show 3 stored records
"""

import argparse
import json
import sys

from . import config


def load_chunks(path=config.CHUNKS_FILE):
    if not path.exists():
        raise SystemExit(
            f"{path} not found — run `python -m src.chunk.chunk` first."
        )
    with path.open(encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def build_index(progress: bool = True):
    """Embed all chunks and (re)load them into a fresh Chroma collection."""
    chunks = load_chunks()
    texts = [c["text"] for c in chunks]
    ids = [c["chunk_id"] for c in chunks]

    # Metadata Chroma stores alongside each vector. Values must be
    # str/int/float/bool. `source` + `chunk_index` are the attribution minimum;
    # the rest support source-authority weighting and freshness signalling.
    metadatas = [{
        "source": c["source"],
        "source_id": c["source_id"],
        "chunk_index": c["chunk_index"],
        "doc_type": c["doc_type"],
        "url": c["url"],
        "source_date": c["source_date"],
        "n_tokens": c["n_tokens"],
    } for c in chunks]

    print(f"Embedding {len(texts)} chunks with {config.MODEL_NAME} ...")
    model = config.get_model()
    # Confirm the embedding limit the chunker was sized against (256).
    print(f"  model max_seq_length = {model.max_seq_length} word-pieces")
    embeddings = config.embed(texts, progress=progress)
    print(f"  embedded -> shape ({len(embeddings)}, {len(embeddings[0])})")

    collection = config.get_collection(create=True)
    # Add in batches to stay well under Chroma's per-call limits.
    B = 256
    for i in range(0, len(ids), B):
        collection.add(
            ids=ids[i:i + B],
            embeddings=[e.tolist() for e in embeddings[i:i + B]],
            documents=texts[i:i + B],
            metadatas=metadatas[i:i + B],
        )

    count = collection.count()
    print(f"Stored {count} vectors in collection "
          f"'{config.COLLECTION_NAME}' at {config.CHROMA_PATH}/")
    return collection


def main(argv=None):
    ap = argparse.ArgumentParser(description="Embed chunks into ChromaDB.")
    ap.add_argument("--peek", type=int, default=0,
                    help="show N stored records after building")
    args = ap.parse_args(argv)

    collection = build_index()

    if args.peek:
        got = collection.get(limit=args.peek, include=["metadatas", "documents"])
        print(f"\n--- {args.peek} stored records ---")
        for cid, meta, doc in zip(got["ids"], got["metadatas"], got["documents"]):
            print(f"\n[{cid}]  source='{meta['source']}'  "
                  f"chunk_index={meta['chunk_index']}  doc_type={meta['doc_type']}")
            print("   " + doc[:200].replace("\n", " ") + " …")
    return 0


if __name__ == "__main__":
    sys.exit(main())
