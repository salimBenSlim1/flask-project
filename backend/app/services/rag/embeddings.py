"""Embedding providers behind LangChain's `Embeddings` interface (swap with EMBEDDINGS_PROVIDER)."""
import hashlib
import math
import os
import re
from functools import lru_cache

from flask import current_app
from langchain_core.embeddings import Embeddings


class HashingEmbeddings(Embeddings):
    """Bag-of-words feature hashing. Deterministic, no model, no network.

    Keyword-level similarity only; meant for tests and offline demos, not production quality.
    """

    def __init__(self, dim: int):
        self.dim = dim

    def _embed(self, text: str) -> list[float]:
        vec = [0.0] * self.dim
        for token in re.findall(r"\w+", text.lower()):
            h = int.from_bytes(hashlib.blake2b(token.encode(), digest_size=8).digest(), "big")
            vec[h % self.dim] += 1.0
        norm = math.sqrt(sum(v * v for v in vec)) or 1.0
        return [v / norm for v in vec]

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return [self._embed(t) for t in texts]

    def embed_query(self, text: str) -> list[float]:
        return self._embed(text)


class FastEmbedEmbeddings(Embeddings):
    """Local ONNX model via fastembed: no API key, no torch."""

    def __init__(self, model_name: str, cache_dir: str | None = None):
        from fastembed import TextEmbedding

        self._model = TextEmbedding(model_name=model_name, cache_dir=cache_dir)

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return [v.tolist() for v in self._model.embed(texts)]

    def embed_query(self, text: str) -> list[float]:
        return next(iter(self._model.query_embed(text))).tolist()


@lru_cache(maxsize=4)  # models are heavy: build once per process
def _build(provider: str, model: str, dim: int) -> Embeddings:
    if provider == "hashing":
        return HashingEmbeddings(dim)
    if provider == "fastembed":
        return FastEmbedEmbeddings(model, cache_dir=os.environ.get("FASTEMBED_CACHE_PATH"))
    if provider == "voyage":
        from langchain_voyageai import VoyageAIEmbeddings  # pip install langchain-voyageai

        return VoyageAIEmbeddings(model=model)
    if provider == "openai":
        from langchain_openai import OpenAIEmbeddings  # pip install langchain-openai

        return OpenAIEmbeddings(model=model)
    raise RuntimeError(f"Unknown EMBEDDINGS_PROVIDER '{provider}'")


def get_embeddings() -> Embeddings:
    cfg = current_app.config
    return _build(cfg["EMBEDDINGS_PROVIDER"], cfg["EMBEDDING_MODEL"], cfg["EMBEDDING_DIM"])
