"""Milestone 4b: semantic retrieval over the ChromaDB index.

Embeds a query with the same all-MiniLM-L6-v2 model and returns the top-k most
similar chunks (cosine), each with its source metadata for later attribution.

Usage:
    python -m src.retrieval.retrieve "what is the no more than four rule?"
    python -m src.retrieval.retrieve --k 4 "who pays for heat in Massachusetts?"
    python -m src.retrieval.retrieve --eval   # run the 5 planning.md questions
"""

import argparse
import sys

from . import config

# The 5 evaluation questions from planning.md, paired with the source id whose
# document should supply the answer — used by --eval to sanity-check retrieval.
EVAL_QUESTIONS = [
    ("What is Boston's \"No More Than Four\" rule for student renters?", 8),
    ("In Massachusetts, what is the maximum security deposit a landlord can "
     "charge, and what other up-front payments are allowed?", 7),
    ("As an international student with no U.S. credit history, what document "
     "can I use to help secure an off-campus apartment?", 4),
    ("In a Massachusetts rental, who is responsible for paying for heat, hot "
     "water, and electricity?", 7),
    ("Which MBTA subway line directly connects to Northeastern's main campus, "
     "and what station serves it?", 10),
]


def retrieve(query: str, k: int = config.TOP_K):
    """Return the top-k chunks for a query as a list of dicts.

    Each result: {chunk_id, text, score, source, source_id, chunk_index,
    doc_type, url, source_date}. `score` is cosine similarity in [0, 1].
    """
    collection = config.get_collection()
    q_emb = config.embed([query])[0].tolist()
    res = collection.query(
        query_embeddings=[q_emb],
        n_results=k,
        include=["documents", "metadatas", "distances"],
    )
    out = []
    for cid, doc, meta, dist in zip(
        res["ids"][0], res["documents"][0],
        res["metadatas"][0], res["distances"][0],
    ):
        out.append({
            "chunk_id": cid,
            "text": doc,
            "score": 1.0 - dist,          # cosine distance -> similarity
            **meta,
        })
    return out


def _print_results(query, results):
    print(f"\nQuery: {query}")
    print("-" * 78)
    for i, r in enumerate(results, 1):
        print(f"{i}. [{r['score']:.3f}] {r['source']} "
              f"(chunk {r['chunk_index']}, {r['doc_type']})")
        print(f"   {r['text'][:200].replace(chr(10), ' ')} …")


def run_eval(k: int):
    print("=" * 78)
    print(f"RETRIEVAL EVAL — do the right sources surface in top-{k}?")
    print("=" * 78)
    passed = 0
    for q, expected_id in EVAL_QUESTIONS:
        results = retrieve(q, k=k)
        ranks = [i for i, r in enumerate(results, 1)
                 if r["source_id"] == expected_id]
        hit = bool(ranks)
        passed += hit
        status = f"PASS (rank {ranks[0]})" if hit else "MISS"
        print(f"\n[{status}] expected source #{expected_id}")
        print(f"   Q: {q}")
        top = results[0]
        print(f"   top hit: [{top['score']:.3f}] {top['source']} "
              f"(chunk {top['chunk_index']})")
    print("\n" + "=" * 78)
    print(f"RESULT: {passed}/{len(EVAL_QUESTIONS)} questions retrieved their "
          f"expected source within top-{k}")
    print("=" * 78)
    return passed


def main(argv=None):
    ap = argparse.ArgumentParser(description="Retrieve chunks for a query.")
    ap.add_argument("query", nargs="*", help="the search query")
    ap.add_argument("--k", type=int, default=config.TOP_K)
    ap.add_argument("--eval", action="store_true",
                    help="run the 5 planning.md evaluation questions")
    args = ap.parse_args(argv)

    if args.eval:
        run_eval(args.k)
        return 0
    if not args.query:
        ap.error("provide a query, or use --eval")
    query = " ".join(args.query)
    _print_results(query, retrieve(query, k=args.k))
    return 0


if __name__ == "__main__":
    sys.exit(main())
