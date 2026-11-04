"""Leitura dos PDFs e divisão em trechos (chunks).

O modelo não lê o PDF inteiro a cada pergunta: o texto é dividido em trechos
de ~600 caracteres e só os mais parecidos com a pergunta vão para a IA.
Cada trecho guarda o arquivo e a página de origem para citar a fonte.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from pypdf import PdfReader

CHUNK_SIZE = 600
# fim de frase: . ! ?  ou dois-pontos seguido de maiúscula (fim de um título)
SENTENCE_RE = re.compile(r"(?<=[.!?])\s+|(?<=:)\s+(?=[A-ZÁÉÍÓÚÂÊÔÃÕÇ])")


@dataclass
class Chunk:
    id: str
    text: str
    source: str   # nome do arquivo
    page: int     # página começando em 1


def read_pdf(path: Path) -> list[tuple[int, str]]:
    """Texto de cada página: [(1, '...'), (2, '...')]."""
    reader = PdfReader(str(path))
    pages = []
    for number, page in enumerate(reader.pages, start=1):
        text = page.extract_text() or ""
        text = re.sub(r"-\n(\w)", r"\1", text)      # junta palavras quebradas com hífen no fim da linha
        lines = []
        for line in text.splitlines():
            line = line.strip()
            # linha curta sem pontuação final = título; vira uma "frase" separada
            if line and len(line) < 60 and not re.search(r"[.!?:,;]$", line):
                line += ":"
            lines.append(line)
        text = re.sub(r"\s+", " ", " ".join(lines)).strip()
        if text:
            pages.append((number, text))
    return pages


def split_text(text: str, size: int = CHUNK_SIZE) -> list[str]:
    """Agrupa frases inteiras até ~`size` caracteres.

    A última frase de um trecho se repete no começo do próximo (sobreposição),
    para não perder o contexto de uma informação que fica entre dois trechos.
    """
    sentences = [s.strip() for s in SENTENCE_RE.split(text) if s.strip()]
    chunks, current = [], []
    for sentence in sentences:
        if current and len(" ".join(current + [sentence])) > size:
            chunks.append(" ".join(current))
            current = [current[-1]] if len(current) > 1 else []
        current.append(sentence)
    if current:
        chunks.append(" ".join(current))
    return chunks


def chunk_pdf(path: Path, size: int = CHUNK_SIZE) -> list[Chunk]:
    chunks = []
    for page, text in read_pdf(path):
        for i, piece in enumerate(split_text(text, size)):
            chunks.append(Chunk(f"{path.name}:p{page}:{i}", piece, path.name, page))
    return chunks


def chunk_folder(folder: Path, size: int = CHUNK_SIZE) -> dict[str, list[Chunk]]:
    """{arquivo: [trechos]} para todos os PDFs da pasta."""
    return {p.name: chunk_pdf(p, size) for p in sorted(folder.glob("*.pdf"))}
