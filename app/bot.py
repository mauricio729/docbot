"""Conversa do DocBot no WhatsApp.

- Saudação explica o que o bot sabe responder.
- Cada pergunta passa pelo RAG. Com resposta: texto + fonte (arquivo e página).
- Sem resposta nos documentos: oferece atendente em vez de inventar.
- Em atendimento humano o bot fica em silêncio até o cliente digitar "bot",
  o atendente encerrar, ou passar o tempo limite.
"""
from __future__ import annotations

import re
import time
import unicodedata
from typing import Callable

from .messages import Buttons, Incoming, Outgoing, Text

GREETINGS = {"oi", "ola", "bom dia", "boa tarde", "boa noite", "menu", "inicio", "e ai", "opa"}
BACK_TO_BOT = {"bot", "voltar ao bot", "voltar", "menu"}
# palavra inteira: "higiene pessoal" não pode acionar o atendente
HANDOFF_RE = re.compile(r"\b(atendente|atendimento humano|humano|falar com (alguem|uma pessoa))\b")


def normalize(text: str) -> str:
    text = unicodedata.normalize("NFD", text.lower().strip())
    return "".join(c for c in text if unicodedata.category(c) != "Mn").strip("!?. ")


class DocBot:
    def __init__(self, rag, sessions, question_log=None, company: str = "Loja Exemplo",
                 notify_agent: Callable[[str, str], None] | None = None,
                 handoff_minutes: int = 60, clock: Callable[[], float] = time.time):
        self.rag = rag
        self.sessions = sessions
        self.log = question_log
        self.company = company
        self.notify_agent = notify_agent
        self.handoff_seconds = handoff_minutes * 60
        self.clock = clock

    def handle(self, msg: Incoming) -> list[Outgoing]:
        s = self.sessions.get(msg.phone) or {"state": "INICIO"}
        low = normalize(msg.value)

        if s["state"] == "HUMANO":
            if low in BACK_TO_BOT or self.clock() > s.get("until", 0):
                s = {"state": "BOT"}
                if low in BACK_TO_BOT:
                    return self._save(msg.phone, s, [Text("De volta ao assistente virtual! 🤖 Pode perguntar.")])
            else:
                return []  # atendente está cuidando da conversa

        if s["state"] == "INICIO" or low in GREETINGS:
            return self._save(msg.phone, {"state": "BOT"}, [self._intro(msg.name)])

        if msg.value == "atendente" or HANDOFF_RE.search(low):
            return self._handoff(msg, s.get("last_question", ""))

        if msg.value == "nova":
            return self._save(msg.phone, {"state": "BOT"}, [Text("Claro! Pode mandar sua pergunta. 😊")])

        if msg.text.startswith("[") and msg.text.endswith("]"):  # áudio, imagem...
            return [Text("Por enquanto eu só entendo mensagens de texto. Pode digitar sua dúvida?")]

        question = msg.text.strip()
        if len(question) < 3:
            return [Text("Pode escrever sua dúvida com um pouco mais de detalhe?")]

        answer = self.rag.answer(question)
        if self.log:
            self.log.add(msg.phone, question, answer)

        if answer.handoff:
            out = Buttons("Não encontrei essa informação nos documentos da loja e prefiro não chutar. 🙏\n"
                          "Quer falar com um atendente?",
                          [("atendente", "Falar com atendente"), ("nova", "Outra pergunta")])
            return self._save(msg.phone, {"state": "BOT", "last_question": question}, [out])

        text = f"{answer.text}\n\n_Fonte: {answer.citation()}_\n\nSe precisar, digite *atendente*."
        return self._save(msg.phone, {"state": "BOT", "last_question": question}, [Text(text)])

    def end_handoff(self, phone: str) -> list[Outgoing]:
        self.sessions.save(phone, {"state": "BOT"})
        return [Text("Atendimento encerrado. Obrigado pelo contato! 💚\n"
                     "O assistente virtual continua aqui se precisar.")]

    def _intro(self, name: str) -> Text:
        first = name.split()[0] if name else ""
        return Text(f"Olá{', ' + first if first else ''}! 👋 Sou o assistente virtual da {self.company}.\n"
                    "Respondo dúvidas sobre *trocas e devoluções*, *entrega e frete*, *pagamentos* e *garantia*, "
                    "sempre com base nas políticas oficiais da loja.\n\nQual é a sua dúvida?")

    def _handoff(self, msg: Incoming, question: str) -> list[Outgoing]:
        if self.notify_agent:
            self.notify_agent(msg.phone, question or msg.text)
        self.sessions.save(msg.phone, {"state": "HUMANO", "until": self.clock() + self.handoff_seconds})
        return [Text("Certo! Chamei um atendente, ele vai continuar por aqui. 🙋\n"
                     "Horário humano: seg a sex, 8h às 18h · sáb, 8h às 12h.\n"
                     "Para voltar ao assistente virtual, digite *bot*.")]

    def _save(self, phone: str, session: dict, out: list[Outgoing]) -> list[Outgoing]:
        self.sessions.save(phone, session)
        return out
