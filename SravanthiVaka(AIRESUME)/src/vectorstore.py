from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

import os

import numpy as np

try:
    import chromadb  # type: ignore
except Exception as exc:  # pragma: no cover
    raise RuntimeError("chromadb is required. Please install dependencies from requirements.txt") from exc

class SimpleFAISS:
    pass


class ChromaVectorStore:
    def __init__(self, persist_dir: str, collection_name: str, dimension: int, metric: str = "cosine") -> None:
        if chromadb is None:  # pragma: no cover
            raise RuntimeError("chromadb is not installed. Please install dependencies from requirements.txt")
        self.dimension = dimension
        self.metric = (metric or "cosine").lower()
        # Create persistent client
        self.client = chromadb.PersistentClient(path=persist_dir)
        # Create or get collection; use metric metadata if supported
        try:
            self.collection = self.client.get_or_create_collection(
                name=collection_name,
                metadata={"hnsw:space": self.metric},
            )
        except TypeError:
            # Older chroma versions may not accept metadata
            self.collection = self.client.get_or_create_collection(name=collection_name)

    def add_texts(self, texts: List[str], vectors: np.ndarray, metadatas: Optional[List[Dict[str, Any]]] = None) -> None:
        if len(texts) == 0:
            return
        if vectors.shape[0] != len(texts):
            raise ValueError("vectors and texts length mismatch")
        metadatas = metadatas or [{} for _ in texts]
        if len(metadatas) != len(texts):
            raise ValueError("metadatas and texts length mismatch")
        ids = [f"doc-{i}" for i in range(self._current_count(), self._current_count() + len(texts))]
        embeds = vectors.astype(float).tolist()
        self.collection.add(documents=texts, embeddings=embeds, metadatas=metadatas, ids=ids)

    def _current_count(self) -> int:
        try:
            # count() available in newer versions
            return int(self.collection.count())  # type: ignore[attr-defined]
        except Exception:
            # Fallback: try peek() or default to 0
            try:
                peek = self.collection.peek()
                return len(peek.get("ids", []))
            except Exception:
                return 0

    def similarity_search(self, query_vector: np.ndarray, k: int = 5) -> List[Tuple[str, float, Dict[str, Any]]]:
        q = query_vector.reshape(1, -1).astype(float).tolist()
        res = self.collection.query(query_embeddings=q, n_results=max(1, k))
        docs = (res.get("documents") or [[]])[0]
        metas = (res.get("metadatas") or [[]])[0]
        dists = (res.get("distances") or [[]])[0]
        results: List[Tuple[str, float, Dict[str, Any]]] = []
        for doc, dist, meta in zip(docs, dists, metas):
            score: float
            try:
                if self.metric == "cosine":
                    # Chroma returns cosine distance; convert to similarity
                    score = 1.0 - float(dist)
                else:
                    score = float(-dist)
            except Exception:
                score = 0.0
            results.append((str(doc), score, dict(meta or {})))
        return results


def create_vector_store(dimension: int):
    persist_dir = os.getenv("CHROMA_DIR", os.path.join(os.getcwd(), ".chroma"))
    collection = os.getenv("CHROMA_COLLECTION", "resume_snippets")
    metric = os.getenv("CHROMA_METRIC", "cosine")
    return ChromaVectorStore(persist_dir=persist_dir, collection_name=collection, dimension=dimension, metric=metric)


def create_vector_store_for(collection_name: str, dimension: int):
    persist_dir = os.getenv("CHROMA_DIR", os.path.join(os.getcwd(), ".chroma"))
    metric = os.getenv("CHROMA_METRIC", "cosine")
    return ChromaVectorStore(persist_dir=persist_dir, collection_name=collection_name, dimension=dimension, metric=metric)
