from pathlib import Path

import pytest

from app.bot import DocBot
from app.documents import Chunk, chunk_folder, split_text
from app.embeddings import KeywordEmbedder
from app.llm import NOT_FOUND, ExtractiveAnswerer
from app.messages import Buttons, Incoming, Text
from app.question_log import QuestionLog
from app.rag import RagAnswerer
from app.sessions import MemorySessionStore
from app.vectorstore import MemoryStore

DOCS = Path(__file__).resolve().parent.parent / "docs"
PHONE = "5534999999999"


@pytest.fixture(scope="module")
def rag():
    r = RagAnswerer(KeywordEmbedder(), MemoryStore(), ExtractiveAnswerer())
    r.ingest(DOCS)
    return r


def make_bot(rag, clock=None):
    log = QuestionLog(":memory:")
    calls = []
    kwargs = {"clock": clock} if clock else {}
    bot = DocBot(rag, MemorySessionStore(), log, notify_agent=lambda p, q: calls.append((p, q)), **kwargs)
    return bot, log, calls


def say(bot, text="", rid=""):
    return bot.handle(Incoming(PHONE, text=text, reply_id=rid, name="Ana"))


# ------------------------------------------------------------ documentos
def test_divide_em_frases_inteiras_com_sobreposicao():
    text = "Primeira frase aqui. Segunda frase um pouco maior. Terceira frase. Quarta frase final."
    chunks = split_text(text, size=50)
    assert all(c.endswith(".") for c in chunks)
    assert len(chunks) > 1
    assert chunks[1].startswith(chunks[0].split(". ")[-1].rstrip("."))  # repete a última frase


def test_le_pdfs_com_pagina():
    files = chunk_folder(DOCS)
    assert set(files) == {"politica-trocas.pdf", "entrega-e-frete.pdf", "pagamentos-e-garantia.pdf"}
    pages = {c.page for c in files["politica-trocas.pdf"]}
    assert pages == {1, 2}
    assert any("90 dias" in c.text and c.page == 2 for c in files["politica-trocas.pdf"])


def test_reindexar_nao_duplica():
    store = MemoryStore()
    emb = KeywordEmbedder()
    chunks = [Chunk("a:p1:0", "texto um", "a.pdf", 1), Chunk("a:p1:1", "texto dois", "a.pdf", 1)]
    store.replace_source("a.pdf", chunks, emb.embed([c.text for c in chunks]))
    store.replace_source("b.pdf", [Chunk("b:p1:0", "outro texto", "b.pdf", 1)], emb.embed(["outro texto"]))
    store.replace_source("a.pdf", chunks[:1], emb.embed(["texto um"]))  # a.pdf foi editado: só 1 trecho agora
    assert store.count() == 2
    assert sorted(c.source for c in store.chunks) == ["a.pdf", "b.pdf"]


# ------------------------------------------------------------ RAG
@pytest.mark.parametrize("question,expected,source,page", [
    ("Qual o prazo para trocar um produto?", "30 dias", "politica-trocas.pdf", 1),
    ("E se o produto veio com defeito?", "90 dias", "politica-trocas.pdf", 2),
    ("O frete é grátis?", "R$ 199,00", "entrega-e-frete.pdf", 1),
    ("Vocês parcelam no cartão?", "6 vezes sem juros", "pagamentos-e-garantia.pdf", 1),
    ("Tem desconto no pix?", "5% de desconto", "pagamentos-e-garantia.pdf", 1),
])
def test_responde_com_fonte_certa(rag, question, expected, source, page):
    answer = rag.answer(question)
    assert not answer.handoff
    assert expected in answer.text
    assert answer.sources[0] == (source, page)


@pytest.mark.parametrize("question", ["Vocês vendem carro usado?", "Qual a capital da França?"])
def test_pergunta_fora_dos_documentos_vai_para_humano(rag, question):
    answer = rag.answer(question)
    assert answer.handoff and answer.text == ""


def test_extrativo_responde_nao_sei_sem_palavras_em_comum():
    from app.vectorstore import Hit
    assert ExtractiveAnswerer().answer("cachorro", [Hit("O frete é grátis acima de R$ 199.", "a", 1, 0.9)]) == NOT_FOUND


# ------------------------------------------------------------ bot
def test_conversa_com_resposta_e_fonte(rag):
    bot, log, _ = make_bot(rag)
    intro = say(bot, "oi")[0]
    assert "trocas e devoluções" in intro.body
    out = say(bot, "Qual o prazo para trocar um produto?")[0]
    assert isinstance(out, Text) and "30 dias" in out.body and "📄 politica-trocas.pdf p.1" in out.body
    assert log.stats() == {"perguntas": 1, "respondidas": 1, "taxa_resposta": 1.0}


def test_sem_resposta_oferece_atendente_e_registra(rag):
    bot, log, calls = make_bot(rag)
    say(bot, "oi")
    out = say(bot, "Vocês vendem carro usado?")[0]
    assert isinstance(out, Buttons) and ("atendente", "Falar com atendente") in out.buttons
    assert log.unanswered()[0]["question"] == "Vocês vendem carro usado?"
    say(bot, rid="atendente")
    assert calls == [(PHONE, "Vocês vendem carro usado?")]


def test_atendimento_humano_silencia_e_volta(rag):
    now = [1000.0]
    bot, _, _ = make_bot(rag, clock=lambda: now[0])
    say(bot, "oi")
    assert "Chamei um atendente" in say(bot, "quero falar com um atendente")[0].body
    assert say(bot, "O frete é grátis?") == []        # atendente está cuidando
    assert "De volta" in say(bot, "bot")[0].body
    assert "R$ 199,00" in say(bot, "O frete é grátis?")[0].body

    say(bot, rid="atendente")
    now[0] += 61 * 60                                  # passou o tempo limite
    assert "R$ 199,00" in say(bot, "O frete é grátis?")[0].body


def test_higiene_pessoal_nao_aciona_atendente(rag):
    bot, _, calls = make_bot(rag)
    say(bot, "oi")
    out = say(bot, "Posso trocar item de higiene pessoal?")[0]
    assert calls == [] and "Chamei" not in out.body


def test_audio_pede_texto(rag):
    bot, _, _ = make_bot(rag)
    say(bot, "oi")
    assert "só entendo mensagens de texto" in say(bot, "[audio]")[0].body
