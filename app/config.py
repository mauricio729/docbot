"""Configurações lidas do arquivo .env (veja .env.example)."""
import os
from dataclasses import dataclass

from dotenv import load_dotenv

load_dotenv()


@dataclass(frozen=True)
class Settings:
    company_name: str = os.getenv("COMPANY_NAME", "Loja Exemplo")
    docs_dir: str = os.getenv("DOCS_DIR", "docs")
    # OpenAI: sem chave, o bot roda no modo offline (palavras-chave + respostas extraídas)
    openai_api_key: str = os.getenv("OPENAI_API_KEY", "")
    openai_chat_model: str = os.getenv("OPENAI_CHAT_MODEL", "gpt-4o-mini")
    openai_embedding_model: str = os.getenv("OPENAI_EMBEDDING_MODEL", "text-embedding-3-small")
    chroma_path: str = os.getenv("CHROMA_PATH", "chroma_db")
    # Relevância mínima (0 a 1). Vazio = padrão de cada modo
    min_score: str = os.getenv("MIN_SCORE", "")
    # WhatsApp Cloud API
    wa_token: str = os.getenv("WHATSAPP_TOKEN", "")
    wa_phone_number_id: str = os.getenv("WHATSAPP_PHONE_NUMBER_ID", "")
    wa_api_version: str = os.getenv("WHATSAPP_API_VERSION", "v21.0")
    verify_token: str = os.getenv("WHATSAPP_VERIFY_TOKEN", "docbot-dev")
    app_secret: str = os.getenv("WHATSAPP_APP_SECRET", "")
    agent_phone: str = os.getenv("AGENT_PHONE", "")
    admin_token: str = os.getenv("ADMIN_TOKEN", "troque-esta-chave")
    db_path: str = os.getenv("DB_PATH", "docbot.db")
    redis_url: str = os.getenv("REDIS_URL", "")


settings = Settings()
