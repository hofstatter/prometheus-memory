#!/usr/bin/env python3
"""Migra as tabelas sidecar prometheus_* do SQLite -> PG (tenant_id=1).
Uso: PROMETHEUS_PG_URL=postgresql://prometheus:<senha>@127.0.0.1:5432/prometheus_memory python3 migrate_sidecar.py
"""
import json
import os
import re
import sqlite3
from datetime import datetime

import psycopg2

SQLITE_DB = "/var/lib/docker/volumes/prometheus-data/_data/data/mnemosyne.db"
PG_URL = os.environ.get("PROMETHEUS_PG_URL")

DATE_SUFFIXES = ("_at", "_seen", "_date", "_time", "_processed")  # sufixos EXATOS (evita "status")


def norm_value(col: str, v):
    """Normaliza valores: datas com timezone não-ISO ('T-0300') -> ISO; JSON -> str; resto igual."""
    if v is None:
        return v
    if isinstance(v, (dict, list)):
        return json.dumps(v)
    if isinstance(v, str) and col.lower().endswith(DATE_SUFFIXES):
        s = v.strip()
        s = re.sub(r"T([+-]\d{2})(\d{2})$", r"T\1:\2", s)  # T-0300 -> T-03:00
        try:
            return datetime.fromisoformat(s.replace("Z", "+00:00"))
        except ValueError:
            return None
    return v

TABLES = [
    "prometheus_projects", "prometheus_project_events", "prometheus_project_tasks",
    "prometheus_sessions", "prometheus_events_ingest", "prometheus_connections",
    "prometheus_skills", "prometheus_dedup_hashes", "prometheus_entities",
    "prometheus_memory_entities", "prometheus_meta", "prometheus_project_reports",
    "prometheus_tech_profile",
]


def main() -> None:
    if not PG_URL:
        raise SystemExit("PROMETHEUS_PG_URL não definida")
    src = sqlite3.connect(SQLITE_DB)
    src.row_factory = sqlite3.Row
    pg = psycopg2.connect(PG_URL)
    total = 0
    for t in TABLES:
        try:
            rows = src.execute(f'SELECT * FROM "{t}"').fetchall()
        except Exception as e:  # noqa: BLE001
            print(f"{t}: erro ler: {e}")
            continue
        if not rows:
            print(f"{t}: 0 linhas")
            continue
        with pg.cursor() as cur:
            cur.execute(
                "SELECT column_name FROM information_schema.columns WHERE table_name=%s", (t,))
            pg_cols = [r[0] for r in cur.fetchall()]
        cols = [c for c in rows[0].keys() if c in pg_cols]
        if not cols:
            print(f"{t}: sem colunas comuns")
            continue
        colnames = ",".join(["tenant_id"] + cols)
        ph = ",".join(["%s"] * (len(cols) + 1))
        ins = f'INSERT INTO "{t}" ({colnames}) VALUES ({ph}) ON CONFLICT DO NOTHING'
        n = 0
        with pg.cursor() as cur:
            for r in rows:
                vals = [1] + [norm_value(c, r[c]) for c in cols]
                try:
                    cur.execute(ins, vals)
                    n += 1
                except Exception:  # noqa: BLE001
                    pass
        pg.commit()
        total += n
        print(f"{t}: {n} migradas")
    print(f"TOTAL: {total}")


if __name__ == "__main__":
    main()
