"""Converse com o DocBot pelo terminal.

    python -m app.chat

Sem OPENAI_API_KEY no .env, funciona no modo offline com os PDFs de docs/.
Digite 'sair' para fechar.
"""
import logging

from .bot import DocBot
from .config import settings
from .container import build_rag
from .messages import Buttons, Incoming
from .sessions import MemorySessionStore
from .whatsapp import match_option, render

PHONE = "5534999999999"


def main() -> None:
    logging.basicConfig(level=logging.WARNING, format="%(message)s")
    bot = DocBot(build_rag(), MemorySessionStore(), company=settings.company_name)
    last: list[tuple] = []
    print("DocBot · digite sua pergunta ('sair' para fechar)\n")
    print("Exemplos: Qual o prazo para trocar? · O frete é grátis? · Vocês parcelam?\n")
    while True:
        try:
            text = input("você › ").strip()
        except (EOFError, KeyboardInterrupt):
            break
        if text.lower() == "sair":
            break
        reply_id = match_option(text, last) if last and text.isdigit() else None
        replies = bot.handle(Incoming(PHONE, text=text, reply_id=reply_id or "", name="Cliente"))
        if not replies:
            print("(em atendimento humano · digite 'bot' para voltar)\n")
        for out in replies:
            print(f"\nbot ›  {render(out)}\n")
            last = out.buttons if isinstance(out, Buttons) else []


if __name__ == "__main__":
    main()
