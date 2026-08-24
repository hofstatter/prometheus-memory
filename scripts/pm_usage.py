#!/usr/bin/env python3
"""Prometheus-Memory — Observabilidade (F8): relatório de uso multi-tenant.

Resumo por tenant: agentes, projetos, memórias, eventos, sinapses, última atividade.
Uso: PROMETHEUS_PG_URL=... python3 pm_usage.py
"""
from __future__ import annotations

import json
import os


def _pg_url() -> str:
    url = os.environ.get("PROMETHEUS_PG_URL", "").strip()
    if url:
        return url
    env = "/opt/prometheus/.env"
    if os.path.exists(env):
        for line in open(env):
            if line.startswith("PROMETHEUS_PG_URL="):
                return line.strip().split("=", 1)[1]
    return "postgresql://prometheus@127.0.0.1:5432/prometheus_memory"


def usage_report() -> list[dict]:
    import psycopg2
    conn = psycopg2.connect(_pg_url())
    out = []
    with conn.cursor() as cur:
        cur.execute("SELECT id, name FROM tenants ORDER BY id")
        tenants = cur.fetchall()
        for tid, tname in tenants:
            cur.execute("SELECT COUNT(*) FROM agents WHERE tenant_id=%s", (tid,))
            agents = cur.fetchone()[0]
            cur.execute("SELECT COUNT(*) FROM agents WHERE tenant_id=%s AND revoked_at IS NULL", (tid,))
            agents_active = cur.fetchone()[0]
            cur.execute("SELECT COUNT(*) FROM prometheus_projects WHERE tenant_id=%s", (tid,))
            projects = cur.fetchone()[0]
            cur.execute("SELECT COUNT(*) FROM working_memory WHERE tenant_id=%s", (tid,))
            memories = cur.fetchone()[0]
            cur.execute("SELECT COUNT(*) FROM prometheus_project_events WHERE tenant_id=%s", (tid,))
            events = cur.fetchone()[0]
            cur.execute("SELECT COUNT(*) FROM graph_edges WHERE tenant_id=%s", (tid,))
            synapses = cur.fetchone()[0]
            cur.execute("SELECT MAX(created_at) FROM prometheus_project_events WHERE tenant_id=%s", (tid,))
            last = cur.fetchone()[0]
            out.append({
                "tenant_id": tid, "tenant": tname,
                "agentes": agents, "agentes_ativos": agents_active,
                "projetos": projects, "memorias": memories,
                "eventos": events, "sinapses": synapses,
                "ultima_atividade": str(last)[:19] if last else None,
            })
    conn.close()
    return out


if __name__ == "__main__":
    rep = usage_report()
    for t in rep:
        print(f"[{t['tenant_id']}] {t['tenant']}: {t['agentes_ativos']}/{t['agentes']} agentes ativos · "
              f"{t['projetos']} projetos · {t['memorias']} memórias · {t['eventos']} eventos · "
              f"{t['sinapses']} sinapses · última: {t['ultima_atividade'] or 'nunca'}")
    print(f"TOTAL: {len(rep)} tenants")
