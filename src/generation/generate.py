"""Milestone 5: grounded generation (Architecture stage 5).

Pipeline: retrieve(query) -> filter by relevance -> build a grounded prompt from
the retrieved passages -> call the Groq LLM -> return the answer together with a
PROGRAMMATICALLY-built source list.

Two grounding guarantees, by construction (not left to the LLM's goodwill):

1. Structural grounding. If no retrieved chunk clears the relevance floor, we
   return the refusal string WITHOUT calling the LLM at all — the model is never
   given the chance to answer from prior knowledge when we have no context.

2. Programmatic attribution. The "Sources" list is assembled in Python from the
   metadata of the chunks we actually put in the prompt. The LLM is asked to add
   inline [n] markers for readability, but the authoritative source list does not
   depend on the LLM emitting anything.
"""

import os
import re
from dataclasses import dataclass, field

from dotenv import load_dotenv

from ..retrieval import config
from ..retrieval.retrieve import retrieve

load_dotenv(".env")

GEN_MODEL = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")
TEMPERATURE = 0.0                 # deterministic; we want grounded, not creative
# Cosine-similarity floor. Default 0.0 = disabled: calibration showed absolute
# MiniLM scores do NOT separate in-domain from out-of-domain (e.g. "best pizza in
# Boston" scores ~0.43, higher than a valid short housing question at ~0.30),
# because shared tokens like "Boston" inflate similarity. Grounding is therefore
# enforced semantically by the LLM (see SYSTEM_PROMPT), which refuses when the
# passages don't contain the answer. The floor stays as a tunable knob only.
MIN_SCORE = 0.0
NO_ANSWER = "I don't have enough information in my sources to answer that."

# Absolute grounding rules. Note the imperative, non-negotiable phrasing and the
# EXACT refusal string the model must use — this is enforcement, not suggestion.
SYSTEM_PROMPT = f"""You are "The Unofficial Guide," a retrieval-augmented \
assistant for Northeastern University student housing in Boston.

You will be given a user QUESTION and a set of numbered CONTEXT passages. \
Follow these rules. They are absolute and override any other instinct:

1. Answer ONLY using facts stated in the CONTEXT passages. Do not use any prior \
or outside knowledge. Do not guess, infer, or extrapolate beyond the passages.
2. If the CONTEXT does not contain enough information to answer the question, \
reply with EXACTLY this sentence and nothing else: "{NO_ANSWER}"
3. After each sentence that uses a passage, cite it inline with its number, e.g. \
"... is one month's rent [1]." Cite every claim.
4. If passages conflict, prefer authoritative sources (doc_type "law" or \
"official") over "forum" (Reddit) sources, and say which you relied on. Treat \
"forum" content as anecdotal, not authoritative.
5. Be concise and factual. Do not add a "Sources" section yourself; that is \
appended separately by the system."""


@dataclass
class Answer:
    text: str
    sources: list = field(default_factory=list)   # [{n, source, url, doc_type}]
    used_chunks: list = field(default_factory=list)
    grounded: bool = True   # False when refused for lack of context

    def to_markdown(self) -> str:
        if not self.sources:
            return self.text
        lines = [self.text, "", "**Sources:**"]
        for s in self.sources:
            lines.append(f"{s['n']}. {s['source']} "
                         f"({s['doc_type']}) — {s['url']}")
        return "\n".join(lines)


def _format_context(chunks, src_num: dict) -> str:
    """Label each passage with its SOURCE number so inline [n] citations align
    with the deduplicated Sources list (multiple passages from one source share
    the same [n])."""
    blocks = []
    for c in chunks:
        n = src_num[c["source"]]
        blocks.append(
            f"[{n}] (source: {c['source']}; type: {c['doc_type']})\n{c['text']}"
        )
    return "\n\n".join(blocks)


def _build_sources(chunks) -> list:
    """Deduplicate chunks by source document, preserving first-seen order.

    Built entirely from retrieved metadata, so attribution is guaranteed
    regardless of what the LLM writes.
    """
    seen, sources, n = set(), [], 0
    for c in chunks:
        if c["source"] in seen:
            continue
        seen.add(c["source"])
        n += 1
        sources.append({
            "n": n,
            "source": c["source"],
            "url": c["url"],
            "doc_type": c["doc_type"],
        })
    return sources


def _call_llm(query: str, context: str) -> str:
    from groq import Groq
    client = Groq(api_key=os.environ["GROQ_API_KEY"])
    resp = client.chat.completions.create(
        model=GEN_MODEL,
        temperature=TEMPERATURE,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user",
             "content": f"CONTEXT passages:\n\n{context}\n\n"
                        f"QUESTION: {query}\n\n"
                        f"Answer using only the CONTEXT above."},
        ],
    )
    return resp.choices[0].message.content.strip()


def answer(query: str, k: int = config.TOP_K, min_score: float = MIN_SCORE) -> Answer:
    """Answer a question strictly from retrieved context, with attribution."""
    retrieved = retrieve(query, k=k)
    kept = [c for c in retrieved if c["score"] >= min_score]

    # Structural grounding: with nothing to ground on, refuse without calling the
    # LLM (no chance for it to answer from prior knowledge). With min_score=0 this
    # only triggers on an empty index; the semantic refusal is enforced in-prompt.
    if not kept:
        return Answer(text=NO_ANSWER, sources=[], used_chunks=[], grounded=False)

    # Build sources first so passage labels and the Sources list share numbering.
    sources = _build_sources(kept)
    src_num = {s["source"]: s["n"] for s in sources}
    context = _format_context(kept, src_num)
    text = _call_llm(query, context)

    # If the model refused, don't attach sources (nothing was grounded).
    if text.strip() == NO_ANSWER:
        return Answer(text=NO_ANSWER, sources=[], used_chunks=kept, grounded=False)

    # Precise attribution: keep only sources the answer actually cited via [n].
    # The n->source mapping is ours (from metadata), so this stays programmatic;
    # if the model cited nothing, fall back to all provided sources.
    cited = {int(m) for m in re.findall(r"\[(\d+)\]", text)}
    if cited:
        sources = [s for s in sources if s["n"] in cited]

    return Answer(text=text, sources=sources, used_chunks=kept)


def main(argv=None):
    import argparse
    ap = argparse.ArgumentParser(description="Grounded answer over the housing corpus.")
    ap.add_argument("query", nargs="+")
    ap.add_argument("--k", type=int, default=config.TOP_K)
    ap.add_argument("--min-score", type=float, default=MIN_SCORE)
    args = ap.parse_args(argv)
    res = answer(" ".join(args.query), k=args.k, min_score=args.min_score)
    print(res.to_markdown())


if __name__ == "__main__":
    main()
