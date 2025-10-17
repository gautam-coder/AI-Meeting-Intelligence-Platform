from __future__ import annotations
from typing import List, Sequence
import chromadb
from chromadb.config import Settings as ChromaSettings
from chromadb.utils.embedding_functions import EmbeddingFunction
from ..config import settings
from .llm import ollama_embed


class OllamaEmbeddingFunction(EmbeddingFunction):
    def __call__(self, texts: Sequence[str]) -> List[List[float]]:  # type: ignore[override]
        return ollama_embed(list(texts), model=settings.ollama_embedding_model)


def get_chroma_client():
    return chromadb.PersistentClient(
        path=settings.chroma_persist_dir,
        settings=ChromaSettings(allow_reset=False),
    )


def get_collection():
    client = get_chroma_client()
    coll = client.get_or_create_collection(
        name=settings.chroma_collection_name,
        embedding_function=OllamaEmbeddingFunction(),
        metadata={"hnsw:space": "cosine"},
    )
    return coll

