from __future__ import annotations

import hashlib
import os
import re
from typing import Iterable, List

import numpy as np

try:
    from langchain_google_genai import GoogleGenerativeAIEmbeddings  # type: ignore
except Exception:
    GoogleGenerativeAIEmbeddings = None  # type: ignore


DEFAULT_GEMINI_EMBED_MODEL = os.getenv("GEMINI_EMBED_MODEL", "text-embedding-004")


class _LocalHashingEmbeddings:
    """Very lightweight, dependency-free hashing embeddings.

    Not semantically strong, but provides deterministic vectors to keep
    the app functional when external embeddings are unavailable.
    """

    def __init__(self, dimension: int = 768) -> None:
        self._dimension = int(dimension)

    @property
    def dimension(self) -> int:
        return self._dimension

    def _tokenize(self, text: str) -> List[str]:
        return re.findall(r"[A-Za-z0-9_#+.-]+", text.lower())

    def _hash_to_index(self, token: str) -> int:
        # Use sha1 for stable hashing across processes
        h = hashlib.sha1(token.encode("utf-8")).digest()
        # take first 4 bytes as unsigned int
        idx = int.from_bytes(h[:4], byteorder="big", signed=False)
        return idx % self._dimension

    def embed_documents(self, texts: Iterable[str]) -> List[List[float]]:
        vectors: List[List[float]] = []
        for t in texts:
            tokens = self._tokenize(t or "")
            vec = np.zeros(self._dimension, dtype=np.float32)
            if tokens:
                for tok in tokens:
                    vec[self._hash_to_index(tok)] += 1.0
                # l2 normalize
                norm = float(np.linalg.norm(vec))
                if norm > 0:
                    vec /= norm
            vectors.append(vec.astype(float).tolist())
        return vectors


class EmbeddingService:
    def __init__(self) -> None:
        self._backend = None

        api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
        model_name = DEFAULT_GEMINI_EMBED_MODEL.strip()
        if not model_name.startswith("models/"):
            model_name = f"models/{model_name}"

        # Try remote embeddings first if possible
        if api_key and GoogleGenerativeAIEmbeddings is not None:
            try:
                self._backend = GoogleGenerativeAIEmbeddings(
                    model=model_name,
                    google_api_key=api_key,
                )
            except Exception:
                self._backend = None

        # Fallback to local hashing embeddings
        if self._backend is None:
            self._backend = _LocalHashingEmbeddings(dimension=768)

    @property
    def dimension(self) -> int:
        return 768

    def embed_texts(self, texts: Iterable[str]) -> List[List[float]]:
        clean_texts: List[str] = [t.strip() if t else "" for t in texts]
        if hasattr(self._backend, "embed_documents"):
            return [list(map(float, v)) for v in self._backend.embed_documents(clean_texts)]  # type: ignore[attr-defined]
        # Should not happen, but keep a safe default
        return _LocalHashingEmbeddings(768).embed_documents(clean_texts)

    def embed_query(self, text: str) -> List[float]:
        return self.embed_texts([text])[0]
