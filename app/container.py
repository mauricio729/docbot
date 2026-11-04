"""Monta o RAG de acordo com o .env.

Com OPENAI_API_KEY:  embeddings OpenAI + ChromaDB em disco + gpt-4o-mini
Sem a chave:         palavras-chave + memória + respostas extraídas dos PDFs (modo offline)
"""
from __future__ import annotations

import logging
from pathlib import Path

from .config import Settings, settings
from .embeddings import KeywordEmbedder, OpenAIEmbedder
from .llm import ExtractiveAnswerer, OpenAIChat
from .rag import RagAnswerer
from .vectorstore import ChromaStore, MemoryStore

log = logging.getLogger("docbot")


def build_rag(s: Settings = settings) -> RagAnswerer:
    min_score = float(s.min_score) if s.min_score else None
    if s.openai_api_key:
        embedder = OpenAIEmbedder(s.openai_api_key, s.openai_embedding_model)
        store = ChromaStore(s.chroma_path, collection=f"docs_{s.openai_embedding_model.replace('-', '_')}")
        llm = OpenAIChat(s.openai_api_key, s.openai_chat_model, company=s.company_name)
        rag = RagAnswerer(embedder, store, llm, min_score=min_score)
        if store.count() == 0:
            log.warning("Banco vetorial vazio. Rode: python -m app.ingest")
        return rag

    log.warning("OPENAI_API_KEY não configurada: usando modo offline.")
    rag = RagAnswerer(KeywordEmbedder(), MemoryStore(), ExtractiveAnswerer(), min_score=min_score)
    indexed = rag.ingest(Path(s.docs_dir))  # em memória: indexa a cada inicialização
    log.info("Modo offline: %d trechos de %d arquivos", sum(indexed.values()), len(indexed))
    return rag
