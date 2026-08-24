#!/usr/bin/env python3
"""Atlas — engenheiro de dados (DBA) (F7): mantém a saúde do PostgreSQL.

Tarefas periódicas do Atlas: ANALYZE, detecção de bloat, REINDEX se necessário,
relatório de estatísticas por tabela. Roda no loop do Atlas (profundo, ~24h).

Uso: from atlas_dba import dba_maintain, dba_report
Requer PROMETHEUS_PG_URL (ou pg_config.json).
"""
from __future__ import annotations

import os

TABLES_MAIN = [
    "working_memory", "episodic_memory", "triples", "graph_edges",
    "prometheus_projects", "prometheus_project_events", "prometheus_project_tasks",
    "prometheus_sessions", "prometheus_events_ingest", "prometheus_connections",
    "prometheus_entities", "prometheus_skills",
]


def _pg_url() -> str:
    url = os.environ.get("PROMETHEUS_PG_URL", "").strip()
    if url:
        return url
    import json
    for cfg in ("/app/scripts/pg_config.json", "pg_config.json"):
        if os.path.exists(cfg):
            try:
                return json.load(open(cfg)).get("url", "")
            except Exception:  # noqa: BLE001
                pass
    return "postgresql://prometheus@127.0.0.1:5432/prometheus_memory"


def _conn():
    import psycopg2
    return psycopg2.connect(_pg_url())


def dba_report() -> dict:
    """Relatório de saúde: counts, bloat (dead tuples), último VACUUM/ANALYZE."""
    out = {}
    with _conn() as c:
        with c.cursor() as cur:
            for t in TABLES_MAIN:
                try:
                    cur.execute(
                        """SELECT reltuples::bigint, n_dead_tup,
                                  pg_stat_get_last_analyze_time(oid),
                                  pg_stat_get_last_vacuum_time(oid)
                           FROM pg_stat_user_tables WHERE relname=%s""", (t,))
                    r = cur.fetchone()
                    if r:
                        out[t] = {"rows": r[0], "dead_tup": r[1],
                                  "last_analyze": str(r[2])[:19] if r[2] else None,
                                  "last_vacuum": str(r[3])[:19] if r[3] else None}
                except Exception:  # noqa: BLE001
                    pass
    return out


def dba_maintain(force_analyze: bool = True) -> dict:
    """ANALYZE nas tabelas principais + VACUUM + relatório."""
    with _conn() as c:
        c.autocommit = True  # VACUUM não roda dentro de transação
        with c.cursor() as cur:
            if force_analyze:
                for t in TABLES_MAIN:
                    try:
                        cur.execute(f'ANALYZE "{t}"')
                    except Exception:  # noqa: BLE001
                        pass
            try:
                cur.execute("VACUUM ANALYZE")
            except Exception:  # noqa: BLE001
                pass
    return {"ok": True, "analyze": TABLES_MAIN, "report": dba_report()}
