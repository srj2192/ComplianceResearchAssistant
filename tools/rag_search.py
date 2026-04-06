"""
RAG tool: semantic search over FAISS index built from regulatory PDFs.
Returns top-k most relevant chunks for a given query.
"""

import pickle
import numpy as np
import faiss
from pathlib import Path
from sentence_transformers import SentenceTransformer

INDEX_DIR = Path(__file__).parent.parent / "data" / "faiss_index"
EMBEDDING_MODEL = "all-MiniLM-L6-v2"
TOP_K = 5

_model = None
_index = None
_chunks = None


def _load():
    global _model, _index, _chunks

    if _index is not None:
        return  # already loaded

    index_path = INDEX_DIR / "index.faiss"
    chunks_path = INDEX_DIR / "chunks.pkl"

    if not index_path.exists() or not chunks_path.exists():
        raise FileNotFoundError(
            "FAISS index not found. Run: python ingestion/ingest_docs.py"
        )

    _model = SentenceTransformer(EMBEDDING_MODEL)
    _index = faiss.read_index(str(index_path))
    with open(chunks_path, "rb") as f:
        _chunks = pickle.load(f)


def search(query: str, top_k: int = TOP_K) -> list[dict]:
    """
    Search the FAISS index for chunks relevant to the query.
    Returns list of {"source": str, "text": str, "score": float}
    """
    _load()

    query_embedding = _model.encode([query], convert_to_numpy=True).astype("float32")
    distances, indices = _index.search(query_embedding, top_k)

    results = []
    for dist, idx in zip(distances[0], indices[0]):
        if idx == -1:
            continue
        chunk = _chunks[idx]
        results.append({
            "source": chunk["source"],
            "text": chunk["text"],
            "score": float(dist),
        })

    return results


def format_results(results: list[dict]) -> str:
    """Format search results into a readable string for the LLM."""
    if not results:
        return "No relevant documents found."

    formatted = []
    for i, r in enumerate(results, 1):
        formatted.append(
            f"[Source {i}: {r['source'].upper()}]\n{r['text']}"
        )
    return "\n\n---\n\n".join(formatted)
