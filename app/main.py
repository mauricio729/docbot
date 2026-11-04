"""API do DocBot (FastAPI).

Rotas:
    GET  /webhook                         verificação do webhook pela Meta
    POST /webhook                         mensagens do WhatsApp
    POST /perguntar                       testa uma pergunta e vê a resposta completa
    GET  /perguntas-sem-resposta          o que falta nos documentos
    POST /reindexar                       relê os PDFs da pasta docs/
    POST /atendimentos/{telefone}/encerrar  devolve o cliente ao bot
    GET  /health

Rode com:  uvicorn app.main:app --reload
"""
from __future__ import annotations

import json
import logging
from pathlib import Path

from fastapi import Depends, FastAPI, Header, HTTPException, Query, Request
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel
from starlette.concurrency import run_in_threadpool

from .bot import DocBot
from .config import settings
from .container import build_rag
from .messages import Text
from .question_log import QuestionLog
from .sessions import make_session_store
from .whatsapp import ConsoleSender, WhatsAppClient, parse_webhook, verify_signature

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
log = logging.getLogger("docbot")

if settings.wa_token and settings.wa_phone_number_id:
    sender = WhatsAppClient(settings.wa_token, settings.wa_phone_number_id, settings.wa_api_version)
else:
    log.warning("WHATSAPP_TOKEN não configurado: mensagens serão só exibidas no log.")
    sender = ConsoleSender()


def notify_agent(phone: str, question: str) -> None:
    if settings.agent_phone:
        sender.send(settings.agent_phone, Text(f"🔔 Cliente +{phone} pediu atendente.\nÚltima pergunta: {question}"))


rag = build_rag()
questions = QuestionLog(settings.db_path)
bot = DocBot(rag, make_session_store(settings.redis_url), questions, settings.company_name, notify_agent)
app = FastAPI(title="DocBot", description="Assistente que responde com base nos documentos da empresa")


@app.get("/webhook", response_class=PlainTextResponse)
def verify_webhook(
    mode: str = Query("", alias="hub.mode"),
    token: str = Query("", alias="hub.verify_token"),
    challenge: str = Query("", alias="hub.challenge"),
):
    if mode == "subscribe" and token == settings.verify_token:
        return challenge
    raise HTTPException(status_code=403, detail="Token de verificação inválido")


def process(payload: dict) -> None:
    for msg in parse_webhook(payload):
        log.info("← %s: %s", msg.phone, msg.value)
        for out in bot.handle(msg):
            try:
                sender.send(msg.phone, out)
            except Exception:
                log.exception("Falha ao enviar mensagem para %s", msg.phone)


@app.post("/webhook")
async def receive_webhook(request: Request):
    body = await request.body()
    if not verify_signature(settings.app_secret, body, request.headers.get("X-Hub-Signature-256")):
        raise HTTPException(status_code=401, detail="Assinatura inválida")
    await run_in_threadpool(process, json.loads(body or b"{}"))
    return {"ok": True}


def require_admin(x_api_key: str = Header("")):
    if x_api_key != settings.admin_token:
        raise HTTPException(status_code=401, detail="Envie o cabeçalho X-Api-Key")


class QuestionIn(BaseModel):
    pergunta: str


@app.post("/perguntar", dependencies=[Depends(require_admin)])
def ask(data: QuestionIn):
    answer = rag.answer(data.pergunta)
    return {
        "resposta": answer.text or None,
        "encaminhar_para_atendente": answer.handoff,
        "confianca": answer.confidence,
        "fontes": [{"arquivo": s, "pagina": p} for s, p in answer.sources],
        "motivo": answer.reason or None,
    }


@app.get("/perguntas-sem-resposta", dependencies=[Depends(require_admin)])
def unanswered():
    return {"resumo": questions.stats(), "perguntas": questions.unanswered()}


@app.post("/reindexar", dependencies=[Depends(require_admin)])
def reindex():
    return {"indexados": rag.ingest(Path(settings.docs_dir)), "total_trechos": rag.store.count()}


@app.post("/atendimentos/{phone}/encerrar", dependencies=[Depends(require_admin)])
def close_handoff(phone: str):
    for out in bot.end_handoff(phone):
        sender.send(phone, out)
    return {"ok": True}


@app.get("/health")
def health():
    return {"status": "ok", "modo": rag.embedder.name, "trechos": rag.store.count(),
            "whatsapp": not isinstance(sender, ConsoleSender)}
