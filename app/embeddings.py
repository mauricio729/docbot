"""Embeddings: transformam texto em vetores para comparar significado.

- `OpenAIEmbedder`: produção (text-embedding-3-small). Entende sinônimos e
  frases diferentes com o mesmo sentido.
- `KeywordEmbedder`: modo offline, sem custo. Compara por palavras em comum
  (sem acento, sem palavras vazias, com radical). Bom para testar o fluxo.
"""
from __future__ import annotations

import hashlib
import re
import unicodedata

import numpy as np

STOPWORDS = set("""
a o as os um uma uns umas de da do das dos em na no nas nos por para pra com sem e ou que se ao aos
eu voce voces ele ela eles elas meu minha seu sua nos vos isso esse essa este esta qual quais quanto
quando como onde porque pois mas mais menos muito pouco ja nao sim ser estar ter tem sao foi vai pode
posso preciso quero gostaria saber the is
""".split())


def tokens(text: str) -> list[str]:
    text = unicodedata.normalize("NFD", text.lower())
    text = "".join(c for c in text if unicodedata.category(c) != "Mn")
    words = re.findall(r"[a-z0-9]+", text)
    # radical simples: os 5 primeiros caracteres ("trocar", "trocas" -> "troca")
    return [w[:5] for w in words if w not in STOPWORDS and len(w) > 1]


class KeywordEmbedder:
    name = "palavras-chave"
    min_score = 0.18     # abaixo disso a pergunta não tem relação com os documentos
    strong_score = 0.45

    def __init__(self, dim: int = 1024):
        self.dim = dim

    def _vector(self, text: str) -> np.ndarray:
        v = np.zeros(self.dim, dtype=np.float32)
        for t in tokens(text):
            # hashlib (e não hash()) para o vetor ser igual em toda execução
            idx = int(hashlib.md5(t.encode()).hexdigest()[:8], 16) % self.dim
            v[idx] += 1.0
        norm = np.linalg.norm(v)
        return v / norm if norm else v

    def embed(self, texts: list[str]) -> list[list[float]]:
        return [self._vector(t).tolist() for t in texts]


class OpenAIEmbedder:
    name = "openai"
    min_score = 0.30
    strong_score = 0.60

    def __init__(self, api_key: str, model: str = "text-embedding-3-small"):
        from openai import OpenAI

        self.client = OpenAI(api_key=api_key)
        self.model = model

    def embed(self, texts: list[str]) -> list[list[float]]:
        result = []
        for start in range(0, len(texts), 100):  # envia em lotes de 100
            resp = self.client.embeddings.create(model=self.model, input=texts[start:start + 100])
            result.extend(item.embedding for item in resp.data)
        return result
