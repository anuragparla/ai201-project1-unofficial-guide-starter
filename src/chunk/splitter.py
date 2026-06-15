"""Structure-aware, token-budgeted text splitter.

Implements the Chunking Strategy from planning.md:
  - target ~240 tokens per chunk, ~40-token (15%) overlap
  - split on natural boundaries first (paragraph -> sentence -> word)
  - HARD guarantee: no chunk exceeds the model's limit, so nothing is
    silently truncated at embedding time.

Length is measured in *real* all-MiniLM-L6-v2 word-pieces (not characters),
because the 256-word-piece limit is the whole reason for the 240 target.
The model adds [CLS]+[SEP] (2 tokens) at embed time, so the usable content
budget is MAX_TOKENS = 254.
"""

import re

MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"
MODEL_MAX_SEQ = 256          # all-MiniLM-L6-v2 truncates beyond this
SPECIAL_TOKENS = 2           # [CLS] + [SEP]
MAX_TOKENS = MODEL_MAX_SEQ - SPECIAL_TOKENS  # 254 usable content tokens

TARGET_TOKENS = 240
OVERLAP_TOKENS = 40

_PARA_RE = re.compile(r"\n{2,}")
_SENT_RE = re.compile(r"(?<=[.!?])\s+")


# --------------------------------------------------------------------------- #
# Token counting (real model tokenizer, lazily loaded)
# --------------------------------------------------------------------------- #

_tokenizer = None


def get_tokenizer():
    global _tokenizer
    if _tokenizer is None:
        from transformers import AutoTokenizer
        _tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)
    return _tokenizer


def count_tokens(text: str) -> int:
    """Number of content word-pieces (excludes [CLS]/[SEP])."""
    return len(get_tokenizer().encode(text, add_special_tokens=False))


# --------------------------------------------------------------------------- #
# Splitting into atoms
# --------------------------------------------------------------------------- #

def _split_sentences(paragraph: str) -> list[str]:
    return [s.strip() for s in _SENT_RE.split(paragraph) if s.strip()]


def _split_paragraphs(text: str) -> list[str]:
    return [p.strip() for p in _PARA_RE.split(text) if p.strip()]


def _split_long_sentence(sentence: str, max_tokens: int) -> list[str]:
    """Last resort: break a sentence longer than max_tokens on word boundaries."""
    words = sentence.split()
    pieces, cur = [], []
    for w in words:
        cur.append(w)
        if count_tokens(" ".join(cur)) > max_tokens:
            cur.pop()
            if cur:
                pieces.append(" ".join(cur))
            cur = [w]
    if cur:
        pieces.append(" ".join(cur))
    return pieces


def _atoms(text: str, max_tokens: int) -> list[tuple[str, int]]:
    """Smallest semantic units (sentences), each guaranteed <= max_tokens."""
    out = []
    for para in _split_paragraphs(text):
        for sent in _split_sentences(para):
            n = count_tokens(sent)
            if n <= max_tokens:
                out.append((sent, n))
            else:
                for piece in _split_long_sentence(sent, max_tokens):
                    out.append((piece, count_tokens(piece)))
    return out


def _overlap_tail(units: list[tuple[str, int]], overlap: int) -> list[tuple[str, int]]:
    """Trailing sentences of a closed chunk totalling up to `overlap` tokens."""
    tail, total = [], 0
    for unit in reversed(units):
        if total + unit[1] > overlap and tail:
            break
        tail.insert(0, unit)
        total += unit[1]
    return tail


# --------------------------------------------------------------------------- #
# Public API
# --------------------------------------------------------------------------- #

def chunk_text(
    text: str,
    target: int = TARGET_TOKENS,
    overlap: int = OVERLAP_TOKENS,
    max_tokens: int = MAX_TOKENS,
) -> list[str]:
    """Split text into overlapping, token-budgeted chunks on natural boundaries.

    Greedily packs whole sentences up to `target` tokens, then carries a
    `overlap`-token sentence tail into the next chunk so facts split across a
    boundary stay recoverable. Every returned chunk is <= max_tokens.
    """
    atoms = _atoms(text, max_tokens)
    chunks: list[str] = []
    cur: list[tuple[str, int]] = []
    cur_tok = 0

    for atom, ntok in atoms:
        # Close the current chunk before it would exceed the target.
        if cur and cur_tok + ntok > target:
            chunks.append(" ".join(s for s, _ in cur))
            cur = _overlap_tail(cur, overlap)
            cur_tok = sum(t for _, t in cur)
        # Safety: never let overlap-tail + this atom breach the model limit.
        if cur and cur_tok + ntok > max_tokens:
            cur, cur_tok = [], 0
        cur.append((atom, ntok))
        cur_tok += ntok

    if cur:
        chunks.append(" ".join(s for s, _ in cur))
    return chunks
