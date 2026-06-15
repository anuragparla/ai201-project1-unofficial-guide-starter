"""Shared configuration and lazily-cached resources for embedding + retrieval.

Implements stages 3-4 of the Architecture diagram:
    chunks.jsonl -> all-MiniLM-L6-v2 (384-dim) -> ChromaDB (cosine) -> retrieve(k=6)

The embedding model and Chroma client are module-level singletons so the embed
step and the retrieve step share one loaded model rather than reloading it.
"""

from pathlib import Path

CHUNKS_FILE = Path("documents/chunks.jsonl")
CHROMA_PATH = "chroma_db"                       # gitignored persistent store
COLLECTION_NAME = "student_housing"

# Matches planning.md Retrieval Approach. SentenceTransformer accepts the short
# or fully-qualified name; we use the qualified one for clarity.
MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"
EMBED_DIM = 384
TOP_K = 6

_model = None
_client = None


def get_model():
    """Return the cached SentenceTransformer, loading it on first use."""
    global _model
    if _model is None:
        from sentence_transformers import SentenceTransformer
        _model = SentenceTransformer(MODEL_NAME)
    return _model


def embed(texts, *, batch_size: int = 64, progress: bool = False):
    """Embed a list of texts into L2-normalized vectors (for cosine similarity)."""
    return get_model().encode(
        texts,
        batch_size=batch_size,
        normalize_embeddings=True,
        show_progress_bar=progress,
    )


def get_client():
    """Return the cached persistent Chroma client."""
    global _client
    if _client is None:
        import chromadb
        _client = chromadb.PersistentClient(path=CHROMA_PATH)
    return _client


def get_collection(create: bool = False):
    """Get the Chroma collection. If create=True, (re)create it empty.

    Uses cosine space because our embeddings are normalized and the Retrieval
    Approach specifies cosine similarity.
    """
    client = get_client()
    if create:
        try:
            client.delete_collection(COLLECTION_NAME)
        except Exception:
            pass  # didn't exist yet
        return client.create_collection(
            COLLECTION_NAME, metadata={"hnsw:space": "cosine"}
        )
    return client.get_collection(COLLECTION_NAME)
