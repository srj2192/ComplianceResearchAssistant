"""
Ingestion pipeline: PDF documents → chunked text → embeddings → FAISS index

Run once before starting the agent:
    python ingestion/ingest_docs.py

Documents to place in /docs:
    - gdpr.pdf         (GDPR full text — download from EUR-Lex)
    - iso27001.pdf     (ISO 27001 summary/annex — free overview docs)
    - edpb_guidelines.pdf  (optional — EDPB guidance docs from edpb.europa.eu)
"""

import os
import json
import pickle
import numpy as np
import faiss
from pathlib import Path
from pypdf import PdfReader
from sentence_transformers import SentenceTransformer

DOCS_DIR = Path(__file__).parent.parent / "docs"
INDEX_DIR = Path(__file__).parent.parent / "data" / "faiss_index"
CHUNK_SIZE = 500        # words per chunk
CHUNK_OVERLAP = 50      # words overlap between chunks
EMBEDDING_MODEL = "all-MiniLM-L6-v2"  # fast, good quality, free


def _extract_text_from_pdf(pdf_path: Path) -> str:
    reader = PdfReader(str(pdf_path))
    text = ""
    for page in reader.pages:
        page_text = page.extract_text()
        if page_text:
            text += page_text + "\n"
    return text


def _chunk_text(text: str, source: str, chunk_size: int = CHUNK_SIZE, overlap: int = CHUNK_OVERLAP) -> list[dict]:
    words = text.split()
    chunks = []
    start = 0
    chunk_id = 0

    while start < len(words):
        end = min(start + chunk_size, len(words))
        chunk_text = " ".join(words[start:end])
        chunks.append({
            "id": f"{source}_{chunk_id}",
            "source": source,
            "text": chunk_text,
        })
        chunk_id += 1
        start += chunk_size - overlap

    return chunks


def build_index():
    INDEX_DIR.mkdir(parents=True, exist_ok=True)

    pdf_files = list(DOCS_DIR.glob("*.pdf"))
    if not pdf_files:
        print(f"[!] No PDF files found in {DOCS_DIR}")
        print("    Please add regulatory PDFs (gdpr.pdf, iso27001.pdf) to the /docs folder")
        print("    See README.md for download links")
        return

    print(f"[+] Found {len(pdf_files)} document(s): {[f.name for f in pdf_files]}")

    all_chunks = []
    for pdf_path in pdf_files:
        print(f"[+] Processing: {pdf_path.name}")
        text = _extract_text_from_pdf(pdf_path)
        source_name = pdf_path.stem  # e.g. "gdpr", "iso27001"
        chunks = _chunk_text(text, source=source_name)
        all_chunks.extend(chunks)
        print(f"    → {len(chunks)} chunks extracted")

    print(f"\n[+] Total chunks: {len(all_chunks)}")
    print(f"[+] Loading embedding model: {EMBEDDING_MODEL}")

    model = SentenceTransformer(EMBEDDING_MODEL)
    texts = [c["text"] for c in all_chunks]

    print("[+] Generating embeddings (this may take a minute)...")
    embeddings = model.encode(texts, show_progress_bar=True, batch_size=64)
    embeddings = np.array(embeddings, dtype="float32")

    dimension = embeddings.shape[1]
    index = faiss.IndexFlatL2(dimension)
    index.add(embeddings)

    faiss.write_index(index, str(INDEX_DIR / "index.faiss"))
    with open(INDEX_DIR / "chunks.pkl", "wb") as f:
        pickle.dump(all_chunks, f)
    with open(INDEX_DIR / "metadata.json", "w") as f:
        json.dump({
            "num_chunks": len(all_chunks),
            "dimension": dimension,
            "model": EMBEDDING_MODEL,
            "sources": [f.name for f in pdf_files],
        }, f, indent=2)

    print(f"\n[✓] FAISS index built successfully")
    print(f"    Chunks: {len(all_chunks)}")
    print(f"    Dimension: {dimension}")
    print(f"    Saved to: {INDEX_DIR}")


if __name__ == "__main__":
    build_index()
