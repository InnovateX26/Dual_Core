"""
RAG Engine — FAISS-based Retrieval-Augmented Generation pipeline.
Uses sentence-transformers for multilingual embeddings and FAISS for vector search.
"""

import os
import json
import pickle
import numpy as np
from typing import Optional

# Lazy imports for heavy libraries
_model = None
_index = None
_documents = []
_embeddings_cache = {}

MODEL_NAME = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
INDEX_PATH = os.path.join(os.path.dirname(__file__), "faiss_index")
DOCS_PATH = os.path.join(os.path.dirname(__file__), "faiss_docs.pkl")


def _get_model():
    """Lazy-load the sentence transformer model."""
    global _model
    if _model is None:
        print("[RAG] Loading sentence-transformer model (this may take a moment on first run)...")
        from sentence_transformers import SentenceTransformer
        _model = SentenceTransformer(MODEL_NAME)
        print("[RAG] Model loaded successfully!")
    return _model


def _get_or_create_index():
    """Get existing FAISS index or create a new one."""
    global _index, _documents
    import faiss

    if _index is not None:
        return _index

    # Try loading from disk
    if os.path.exists(INDEX_PATH) and os.path.exists(DOCS_PATH):
        try:
            print("[RAG] Loading existing FAISS index from disk...")
            _index = faiss.read_index(INDEX_PATH)
            with open(DOCS_PATH, "rb") as f:
                _documents = pickle.load(f)
            print(f"[RAG] Loaded index with {_index.ntotal} vectors and {len(_documents)} documents")
            return _index
        except Exception as e:
            print(f"[RAG] Failed to load index: {e}. Will rebuild.")

    # Create new empty index
    model = _get_model()
    dimension = model.get_sentence_embedding_dimension()
    _index = faiss.IndexFlatIP(dimension)  # Inner Product (cosine similarity with normalized vectors)
    _documents = []
    print(f"[RAG] Created new FAISS index with dimension {dimension}")
    return _index


def _normalize_vectors(vectors: np.ndarray) -> np.ndarray:
    """L2-normalize vectors for cosine similarity with IndexFlatIP."""
    norms = np.linalg.norm(vectors, axis=1, keepdims=True)
    norms[norms == 0] = 1  # Avoid division by zero
    return vectors / norms


def _chunk_text(text: str, chunk_size: int = 300, overlap: int = 50) -> list[str]:
    """Split text into overlapping word chunks."""
    words = text.split()
    if len(words) <= chunk_size:
        return [text]

    chunks = []
    start = 0
    while start < len(words):
        end = start + chunk_size
        chunk = " ".join(words[start:end])
        chunks.append(chunk)
        start += chunk_size - overlap

    return chunks


def add_documents(documents: list[dict]) -> int:
    """
    Add documents to the FAISS index.

    Args:
        documents: List of dicts with 'id', 'title', 'content', 'category'

    Returns:
        Number of vectors added
    """
    global _index, _documents

    index = _get_or_create_index()
    model = _get_model()

    texts_to_embed = []
    doc_metadata = []

    for doc in documents:
        doc_id = doc.get("id", "unknown")
        title = doc.get("title", "")
        content = doc.get("content", "")
        category = doc.get("category", "general")

        # Create searchable text combining title and content
        full_text = f"{title}. {content}"

        # Chunk long documents
        chunks = _chunk_text(full_text)

        for i, chunk in enumerate(chunks):
            texts_to_embed.append(chunk)
            doc_metadata.append({
                "id": f"{doc_id}_chunk{i}",
                "doc_id": doc_id,
                "title": title,
                "content": chunk,
                "category": category,
                "chunk_index": i,
                "total_chunks": len(chunks),
            })

    if not texts_to_embed:
        return 0

    # Generate embeddings
    print(f"[RAG] Generating embeddings for {len(texts_to_embed)} chunks...")
    embeddings = model.encode(texts_to_embed, show_progress_bar=True, convert_to_numpy=True)
    embeddings = _normalize_vectors(embeddings.astype(np.float32))

    # Add to FAISS index
    index.add(embeddings)
    _documents.extend(doc_metadata)

    # Save to disk
    _save_index()

    print(f"[RAG] Added {len(texts_to_embed)} vectors. Total: {index.ntotal}")
    return len(texts_to_embed)


def search(query: str, top_k: int = 5, score_threshold: float = 0.25) -> list[dict]:
    """
    Search the FAISS index for relevant documents.

    Args:
        query: Search query text
        top_k: Number of results to return
        score_threshold: Minimum similarity score (0-1)

    Returns:
        List of matching documents with scores
    """
    index = _get_or_create_index()

    if index.ntotal == 0:
        print("[RAG] Index is empty — no documents to search.")
        return []

    model = _get_model()

    # Encode query
    query_embedding = model.encode([query], convert_to_numpy=True)
    query_embedding = _normalize_vectors(query_embedding.astype(np.float32))

    # Search
    scores, indices = index.search(query_embedding, min(top_k, index.ntotal))

    results = []
    for score, idx in zip(scores[0], indices[0]):
        if idx < 0 or idx >= len(_documents):
            continue
        if float(score) < score_threshold:
            continue

        doc = _documents[idx].copy()
        doc["score"] = float(score)
        results.append(doc)

    return results


def _save_index():
    """Save the FAISS index and documents to disk."""
    import faiss

    if _index is not None:
        faiss.write_index(_index, INDEX_PATH)
        with open(DOCS_PATH, "wb") as f:
            pickle.dump(_documents, f)
        print(f"[RAG] Index saved to disk ({_index.ntotal} vectors)")


def get_index_stats() -> dict:
    """Get statistics about the current index."""
    index = _get_or_create_index()

    categories = {}
    for doc in _documents:
        cat = doc.get("category", "unknown")
        categories[cat] = categories.get(cat, 0) + 1

    return {
        "total_vectors": index.ntotal,
        "total_documents": len(_documents),
        "categories": categories,
        "index_path": INDEX_PATH,
        "model": MODEL_NAME,
    }


def clear_index():
    """Clear the entire FAISS index (for rebuilding)."""
    global _index, _documents
    import faiss

    if _index is not None:
        model = _get_model()
        dimension = model.get_sentence_embedding_dimension()
        _index = faiss.IndexFlatIP(dimension)
        _documents = []
        _save_index()
        print("[RAG] Index cleared.")


def rebuild_from_data_dir():
    """Rebuild the FAISS index from all JSON files in the data directory."""
    data_dir = os.path.join(os.path.dirname(__file__), "data")

    if not os.path.exists(data_dir):
        print(f"[RAG] Data directory not found: {data_dir}")
        return 0

    clear_index()

    all_documents = []
    for filename in os.listdir(data_dir):
        if filename.endswith(".json"):
            filepath = os.path.join(data_dir, filename)
            try:
                with open(filepath, "r", encoding="utf-8") as f:
                    docs = json.load(f)
                    if isinstance(docs, list):
                        all_documents.extend(docs)
                        print(f"[RAG] Loaded {len(docs)} documents from {filename}")
            except Exception as e:
                print(f"[RAG] Error loading {filename}: {e}")

    if all_documents:
        return add_documents(all_documents)
    return 0
