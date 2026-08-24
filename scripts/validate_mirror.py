#!/usr/bin/env python3
"""Espelho de validação (F4): compara contagens SQLite vs PG das tabelas sidecar.
Roda via cron diário por ~1 semana. Log em /var/log/pg-mirror.log.
Uso: PROMETHEUS_PG_URL=... python3 validate_mirror.py
"""
import os
import sqlite3

import psycopg2

SQLITE_DB = "/var/lib/docker/volumes/prometheus-data/_data/data/mnemosyne.db"
PG_URL = os.environ.get("PROMETHEUS_PG_URL")
LOG = "/var/log/pg-mirror.log"

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
    # copia do DB (root-only) — roda via sudo
    import shutil
    shutil.copy(SQLITE_DB, "/tmp/mirror_src.db")
    src = sqlite3.connect("/tmp/mirror_src.db")
    pg = psycopg2.connect(PG_URL)
    diverg = []
    lines = [f"=== MIRROR {os.popen('date').read().strip()} ==="]
    for t in TABLES:
        try:
            s = src.execute(f'SELECT COUNT(*) FROM "{t}"').fetchone()[0]
        except Exception as e:  # noqa: BLE001
            s = f"erro:{e}"
        with pg.cursor() as cur:
            cur.execute(f'SELECT COUNT(*) FROM "{t}"')
            p = cur.fetchone()[0]
        ok = "OK" if s == p else "DIVERGE"
        if s != p:
            diverg.append(t)
        lines.append(f"{ok} {t}: sqlite={s} pg={p}")
    total = f"RESULTADO: {'DIVERGENCIAS: ' + ','.join(diverg) if diverg else 'ESPELHO OK (todas iguais)'}"
    lines.append(total)
    os.makedirs("/var/log", exist_ok=True)
    with open(LOG, "a") as f:
        f.write("\n".join(lines) + "\n")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
