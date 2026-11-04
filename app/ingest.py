"""Indexa os PDFs no banco vetorial.

    python -m app.ingest            # usa a pasta do .env (docs/)
    python -m app.ingest outra/pasta

Rode de novo sempre que adicionar ou alterar um documento. Arquivos já
indexados são substituídos, sem duplicar trechos.
"""
import logging
import sys
from pathlib import Path

from .config import settings
from .container import build_rag


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    folder = Path(sys.argv[1] if len(sys.argv) > 1 else settings.docs_dir)
    if not list(folder.glob("*.pdf")):
        sys.exit(f"Nenhum PDF encontrado em {folder.resolve()}")
    rag = build_rag()
    result = rag.ingest(folder)
    print(f"\n{sum(result.values())} trechos de {len(result)} arquivos. Total no banco: {rag.store.count()}")


if __name__ == "__main__":
    main()
