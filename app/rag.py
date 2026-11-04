"""RAG (Retrieval-Augmented Generation): buscar nos documentos, depois responder.

    pergunta ─> embedding ─> trechos mais parecidos ─┬─ relevância baixa? ─> atendente humano
                                                     └─> IA responde só com os trechos ─> resposta + fonte

O bot prefere passar para um humano a inventar uma resposta.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path

from .documents import SENTENCE_RE, chunk_folder
from .llm import NOT_FOUND
from .vectorstore import Hit

log = logging.getLogger("docbot.rag")


@dataclass
class Answer:
    text: str
    handoff: bool                       # True = encaminhar para atendente
    confidence: float = 0.0             # 0 a 1
    sources: list[tuple[str, int]] = field(default_factory=list)  # [(arquivo, página)]
    reason: str = ""

    def citation(self) -> str:
        return " · ".join(f"📄 {src} p.{page}" for src, page in self.sources)


class RagAnswerer:
    def __init__(self, embedder, store, llm, k: int = 4, min_score: float | None = None):
        self.embedder = embedder
        self.store = store
        self.llm = llm
        self.k = k
        self.min_score = min_score if min_score is not None else embedder.min_score
        self.strong_score = getattr(embedder, "strong_score", 0.6)

    def ingest(self, folder: Path) -> dict[str, int]:
        """Lê todos os PDFs da pasta e atualiza o banco vetorial. Retorna {arquivo: nº de trechos}."""
        result = {}
        for source, chunks in chunk_folder(folder).items():
            embeddings = self.embedder.embed([c.text for c in chunks]) if chunks else []
            self.store.replace_source(source, chunks, embeddings)
            result[source] = len(chunks)
            log.info("Indexado %s: %d trechos", source, len(chunks))
        return result

    def answer(self, question: str) -> Answer:
        [q_vec] = self.embedder.embed([question])
        hits: list[Hit] = self.store.query(q_vec, self.k)
        relevant = [h for h in hits if h.score >= self.min_score]
        best = hits[0].score if hits else 0.0
        confidence = round(max(0.0, min(1.0, best / self.strong_score)), 2)

        if not relevant:
            log.info("Sem trecho relevante (melhor %.2f): %s", best, question)
            return Answer("", handoff=True, confidence=confidence, reason="nenhum trecho relevante")

        text = self.llm.answer(question, relevant)
        if NOT_FOUND in text:
            return Answer("", handoff=True, confidence=confidence, reason="resposta não está nos documentos")

        # Cita os trechos de onde a resposta saiu. Se a IA reescreveu o texto,
        # cita os dois trechos mais relevantes.
        sentences = [s for s in SENTENCE_RE.split(text) if len(s) > 15]
        used = [h for h in relevant if any(s.strip() in h.text for s in sentences)] or relevant[:2]
        sources = []
        for h in used[:2]:
            if (h.source, h.page) not in sources:
                sources.append((h.source, h.page))
        return Answer(text, handoff=False, confidence=confidence, sources=sources)
