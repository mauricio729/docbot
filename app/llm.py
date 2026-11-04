"""Quem escreve a resposta a partir dos trechos encontrados.

- `OpenAIChat`: produção (gpt-4o-mini). Escreve uma resposta natural, presa aos trechos.
- `ExtractiveAnswerer`: modo offline. Devolve as frases dos trechos que mais
  combinam com a pergunta, sem reescrever nada.

Os dois respondem exatamente NAO_SEI quando os trechos não têm a resposta.
"""
from __future__ import annotations

from .documents import SENTENCE_RE
from .embeddings import tokens
from .vectorstore import Hit

NOT_FOUND = "NAO_SEI"

SYSTEM_PROMPT = """Você é o assistente de atendimento da {company} no WhatsApp.
Responda em português do Brasil, de forma simpática e direta, em no máximo 3 frases curtas.
Use SOMENTE as informações dos trechos de documentos fornecidos.
Se a resposta não estiver nos trechos, responda exatamente: {not_found}
Nunca invente prazos, valores, regras ou contatos."""


def build_context(hits: list[Hit]) -> str:
    return "\n\n".join(f"[{i}] ({h.source}, página {h.page})\n{h.text}" for i, h in enumerate(hits, 1))


class OpenAIChat:
    def __init__(self, api_key: str, model: str = "gpt-4o-mini", company: str = "empresa"):
        from openai import OpenAI

        self.client = OpenAI(api_key=api_key)
        self.model = model
        self.company = company

    def answer(self, question: str, hits: list[Hit]) -> str:
        resp = self.client.chat.completions.create(
            model=self.model,
            temperature=0,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT.format(company=self.company, not_found=NOT_FOUND)},
                {"role": "user", "content": f"Trechos:\n{build_context(hits)}\n\nPergunta do cliente: {question}"},
            ],
        )
        return (resp.choices[0].message.content or NOT_FOUND).strip()


class ExtractiveAnswerer:
    def __init__(self, max_sentences: int = 2):
        self.max_sentences = max_sentences

    def answer(self, question: str, hits: list[Hit]) -> str:
        q = set(tokens(question))
        if not q:
            return NOT_FOUND
        scored = []
        for rank, hit in enumerate(hits):
            heading = set()
            for sentence in SENTENCE_RE.split(hit.text):
                sentence = sentence.strip()
                if sentence.endswith(":"):  # título da seção: ajuda a pontuar as frases abaixo dele
                    heading = set(tokens(sentence))
                    continue
                if len(sentence.split()) < 4:
                    continue
                overlap = len(q & set(tokens(sentence)))
                if overlap:
                    # palavras em comum na frase + metade do peso das do título da seção
                    score = overlap + 0.5 * len(q & heading)
                    scored.append((score, -rank, sentence))
        if not scored:
            return NOT_FOUND
        scored.sort(reverse=True)
        top = scored[0][0]
        best = []
        for overlap, _, sentence in scored:
            # frases extras só entram se forem quase tão relevantes quanto a primeira
            if sentence not in best and (not best or overlap >= max(2, top - 1)):
                best.append(sentence)
            if len(best) == self.max_sentences:
                break
        return " ".join(best)
