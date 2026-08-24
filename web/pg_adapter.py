#!/usr/bin/env python3
"""Adapter: interface sqlite3-compatível sobre PostgreSQL (F4 — espelho/migração).

Permite que o `prometheus_db.py` (escrito para sqlite3: placeholders `?`,
`row_factory=Row`, `PRAGMA table_info`, `executescript`) rode sobre o PG sem
reescrever as queries. Uso: get_conn() retorna este adapter quando
`PROMETHEUS_PG_URL` está definida.

Limitações conhecidas (cosméticas): PRAGMA de journal/sync são ignoradas;
executescript tolera erros (tabelas já existentes / sintaxe SQLite).
"""
from __future__ import annotations

import os
import re

import psycopg2
from psycopg2.extras import RealDictCursor

PG_URL = os.environ.get(
    "PROMETHEUS_PG_URL",
    "postgresql://prometheus@127.0.0.1:5432/prometheus_memory",
)


def _conv(sql: str) -> str:
    """Converte placeholders `?` (sqlite) para `%s` (psycopg2), ignorando strings."""
    out: list[str] = []
    instr = False
    for ch in sql:
        if ch == "'":
            instr = not instr
            out.append(ch)
        elif ch == "?" and not instr:
            out.append("%s")
        else:
            out.append(ch)
    return "".join(out)


class PGSQLiteCompat:
    """Emula a interface sqlite3.Connection suficiente para o prometheus_db.py."""

    def __init__(self, url: str = PG_URL):
        self._conn = psycopg2.connect(url)
        self._conn.autocommit = False
        self.row_factory = None  # RealDictCursor já entrega dicts

    # ---------- execução ----------
    def cursor(self) -> psycopg2.extensions.cursor:
        return self._conn.cursor(cursor_factory=RealDictCursor)

    def execute(self, sql: str, params=()):
        sql = sql.strip()
        # PRAGMA table_info(X) -> information_schema (formato sqlite: cid,name,type,notnull,dflt,pk)
        m = re.match(r"PRAGMA\s+table_info\(\s*([A-Za-z_0-9]+)\s*\)", sql, re.I)
        if m:
            return self._pragma_table_info(m.group(1))
        # PRAGMAs de configuração -> no-op (PG não precisa)
        if re.match(r"PRAGMA\s+(journal_mode|busy_timeout|synchronous|wal)", sql, re.I):
            return self._noop_cursor()
        cur = self.cursor()
        if params is None:
            params = ()
        cur.execute(_conv(sql), list(params) if not isinstance(params, dict) else params)
        return cur

    def executescript(self, script: str) -> None:
        """Executa statements separados por ';', tolerando erros (tabelas existentes)."""
        for stmt in script.split(";"):
            stmt = stmt.strip()
            if not stmt:
                continue
            try:
                self.execute(stmt)
                self.commit()
            except Exception:  # noqa: BLE001 — CREATE IF NOT EXISTS/SQLite syntax
                self.rollback()

    def executemany(self, sql: str, seq_of_params):
        cur = self.cursor()
        for params in seq_of_params:
            cur.execute(_conv(sql), list(params))
        return cur

    # ---------- transação ----------
    def commit(self) -> None:
        self._conn.commit()

    def rollback(self) -> None:
        self._conn.rollback()

    def close(self) -> None:
        self._conn.close()

    # ---------- helpers ----------
    def _pragma_table_info(self, table: str):
        cur = self.cursor()
        cur.execute(
            """SELECT ordinal_position-1 AS cid, column_name AS name,
                      data_type AS type, 0 AS notnull, NULL AS dflt_value, 0 AS pk
               FROM information_schema.columns
               WHERE table_schema='public' AND table_name=%s ORDER BY ordinal_position""",
            (table,),
        )
        # retorna tuplas como o sqlite (o código usa r[1] = nome)
        rows = [(r["cid"], r["name"], r["type"], r["notnull"], r["dflt_value"], r["pk"])
                for r in cur.fetchall()]
        return _Rows(rows)

    def _noop_cursor(self):
        return _Rows([])


class _Rows:
    """Cursor emulado para os casos sem resultado real (tuplas/dicts)."""

    def __init__(self, rows):
        self._rows = rows
        self._i = 0

    def fetchall(self):
        return self._rows

    def fetchone(self):
        return self._rows[0] if self._rows else None

    def __iter__(self):
        return iter(self._rows)
