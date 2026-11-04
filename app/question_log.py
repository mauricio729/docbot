"""Registro das perguntas, para descobrir o que falta nos documentos.

As perguntas que o bot não soube responder mostram exatamente qual
informação a empresa precisa acrescentar nas políticas.
"""
from __future__ import annotations

import sqlite3
import threading
from datetime import datetime

SCHEMA = """
CREATE TABLE IF NOT EXISTS questions (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    phone       TEXT NOT NULL,
    question    TEXT NOT NULL,
    answered    INTEGER NOT NULL,
    confidence  REAL,
    sources     TEXT,
    created_at  TEXT NOT NULL
);
"""


class QuestionLog:
    def __init__(self, path: str = ":memory:"):
        self.conn = sqlite3.connect(path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self.lock = threading.Lock()
        with self.lock:
            self.conn.executescript(SCHEMA)

    def add(self, phone: str, question: str, answer) -> None:
        with self.lock:
            self.conn.execute(
                "INSERT INTO questions (phone, question, answered, confidence, sources, created_at) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                (phone, question, int(not answer.handoff), answer.confidence, answer.citation(),
                 datetime.now().isoformat(timespec="seconds")))
            self.conn.commit()

    def unanswered(self, limit: int = 50) -> list[dict]:
        with self.lock:
            rows = self.conn.execute(
                "SELECT question, COUNT(*) AS vezes, MAX(created_at) AS ultima FROM questions "
                "WHERE answered = 0 GROUP BY lower(question) ORDER BY vezes DESC, ultima DESC LIMIT ?",
                (limit,)).fetchall()
        return [dict(r) for r in rows]

    def stats(self) -> dict:
        with self.lock:
            row = self.conn.execute("SELECT COUNT(*) AS total, SUM(answered) AS respondidas FROM questions").fetchone()
        total, ok = row["total"], row["respondidas"] or 0
        return {"perguntas": total, "respondidas": ok, "taxa_resposta": round(ok / total, 2) if total else None}
