"""Banco vetorial: guarda os trechos e encontra os mais parecidos com a pergunta.

- `ChromaStore`: ChromaDB persistido em disco (produção).
- `MemoryStore`: em memória com NumPy (testes e modo offline).

Os dois devolvem `Hit` com `score` = similaridade de cosseno (1 = idêntico).
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from .documents import Chunk


@dataclass
class Hit:
    text: str
    source: str
    page: int
    score: float


class MemoryStore:
    def __init__(self):
        self.chunks: list[Chunk] = []
        self.vectors = np.zeros((0, 0), dtype=np.float32)

    def replace_source(self, source: str, chunks: list[Chunk], embeddings: list[list[float]]) -> None:
        keep = [i for i, c in enumerate(self.chunks) if c.source != source]
        old = self.vectors[keep] if len(keep) else np.zeros((0, len(embeddings[0]) if embeddings else 0))
        self.chunks = [self.chunks[i] for i in keep] + list(chunks)
        new = np.array(embeddings, dtype=np.float32)
        self.vectors = np.vstack([old, new]) if len(old) else new

    def query(self, embedding: list[float], k: int = 4) -> list[Hit]:
        if not self.chunks:
            return []
        q = np.array(embedding, dtype=np.float32)
        norms = np.linalg.norm(self.vectors, axis=1) * (np.linalg.norm(q) or 1.0)
        scores = (self.vectors @ q) / np.where(norms == 0, 1, norms)
        best = np.argsort(-scores)[:k]
        return [Hit(self.chunks[i].text, self.chunks[i].source, self.chunks[i].page, float(scores[i]))
                for i in best]

    def count(self) -> int:
        return len(self.chunks)


class ChromaStore:
    def __init__(self, path: str = "chroma_db", collection: str = "documentos"):
        import chromadb

        self.client = chromadb.PersistentClient(path=path)
        self.col = self.client.get_or_create_collection(collection, metadata={"hnsw:space": "cosine"})

    def replace_source(self, source: str, chunks: list[Chunk], embeddings: list[list[float]]) -> None:
        # apaga a versão antiga do arquivo antes de inserir a nova
        self.col.delete(where={"source": source})
        if not chunks:
            return
        self.col.upsert(
            ids=[c.id for c in chunks],
            documents=[c.text for c in chunks],
            embeddings=embeddings,
            metadatas=[{"source": c.source, "page": c.page} for c in chunks],
        )

    def query(self, embedding: list[float], k: int = 4) -> list[Hit]:
        if self.col.count() == 0:
            return []
        res = self.col.query(query_embeddings=[embedding], n_results=k,
                             include=["documents", "metadatas", "distances"])
        return [
            Hit(doc, meta["source"], int(meta["page"]), 1.0 - float(dist))  # distância de cosseno -> similaridade
            for doc, meta, dist in zip(res["documents"][0], res["metadatas"][0], res["distances"][0])
        ]

    def count(self) -> int:
        return self.col.count()
