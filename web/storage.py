#!/usr/bin/env python3
"""
Prometheus Storage Layer — interface unica de acesso as tabelas do Prometheus.

Backend default: SQLite (zero-config, roda em qualquer lugar).
Backend PostgreSQL: stub documentado — implementar na v0.2 quando DATABASE_URL
estiver presente (ver docs/ROADMAP.md). O Mnemosyne core (pip) segue SQLite
nativo upstream e NAO passa por esta camada.
"""
import os
import sqlite3
from pathlib import Path

MNEMOSYNE_HOME = Path(os.environ.get("MNEMOSYNE_HOME", Path.home() / ".hermes" / "mnemosyne"))
DEFAULT_DB = Path(os.environ.get("PROMETHEUS_DB", MNEMOSYNE_HOME / "data" / "mnemosyne.db"))
DATABASE_URL = os.environ.get("DATABASE_URL", "")


class SQLiteStore:
    """Backend SQLite: WAL + busy_timeout + synchronous=NORMAL."""

    def __init__(self, path: str | None = None):
        self.path = str(path or DEFAULT_DB)

    def connect(self) -> sqlite3.Connection:
        con = sqlite3.connect(self.path, timeout=10)
        con.execute("PRAGMA journal_mode=WAL")
        con.execute("PRAGMA busy_timeout=5000")
        con.execute("PRAGMA synchronous=NORMAL")
        return con


class PostgresStore:
    """Backend PostgreSQL (v0.2 — stub).

    Ativacao planejada: DATABASE_URL=postgresql://user:pass@host:5432/prometheus
    - Tabelas rag_* migradas via SQLAlchemy
    - Embeddings via pgvector (HNSW)
    - Mnemosyne core permanece SQLite (upstream) ate suporte oficial
    """

    def __init__(self, dsn: str):
        self.dsn = dsn
        raise NotImplementedError(
            "Backend PostgreSQL chega na v0.2 — veja docs/ROADMAP.md. "
            "Remova DATABASE_URL para usar SQLite."
        )


def get_store():
    """Retorna o store ativo. Hoje: sempre SQLite. Com DATABASE_URL: Postgres (v0.2)."""
    if DATABASE_URL.startswith("postgres"):
        return PostgresStore(DATABASE_URL)
    return SQLiteStore()
