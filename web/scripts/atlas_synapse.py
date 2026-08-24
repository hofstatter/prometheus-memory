#!/usr/bin/env python3
"""Atlas — neurônios-espelho + sinapse (F7).

NEURÔNIOS-ESPELHO: o Atlas observa o comportamento dos agentes (eventos) e
"espelha" os padrões na memória — grava triples `(agent:<id>, costuma_fazer, <tipo>:
em:<projeto>)` para ANTECIPAR o próximo comportamento.

SINAPSE: conecta agentes ↔ entidades/projetos/memórias no grafo (graph_edges) —
`(agent:<id>, atuou_em, <entidade|projeto>)` — permitindo "quem sabe o quê".

Uso: from atlas_synapse import mirror_patterns, sync_synapse, query_synapse
"""
from __future__ import annotations

import os
from collections import Counter


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


def mirror_patterns(limit_events: int = 200, min_count: int = 2) -> dict:
    """NEURÔNIOS-ESPELHO: detecta padrões de comportamento por agente nos eventos
    recentes e grava triples `(agent:<id>, costuma_fazer, <tipo>:em:<projeto>)`
    respeitando o tenant de origem (sem hardcode)."""
    created = 0
    with _conn() as c:
        with c.cursor() as cur:
            cur.execute(
                """SELECT agent_id, event_type, project_slug, tenant_id, COUNT(*) AS n
                   FROM prometheus_project_events
                   WHERE agent_id IS NOT NULL AND agent_id <> ''
                   GROUP BY agent_id, event_type, project_slug, tenant_id
                   ORDER BY n DESC LIMIT %s""", (limit_events,))
            rows = cur.fetchall()
        # padrão dominante por (tenant, agente)
        by_key: dict[tuple, Counter] = {}
        for agent, etype, proj, tid, n in rows:
            if n >= min_count:
                by_key.setdefault((tid, agent), Counter())[(etype, proj)] = n
        with c.cursor() as cur:
            for (tid, agent), counter in by_key.items():
                for (etype, proj), n in counter.most_common(3):
                    obj = f"{etype}:em:{proj or '?'}"
                    cur.execute(
                        """INSERT INTO triples (tenant_id, subject, predicate, object)
                           VALUES (%s, %s, %s, %s)
                           ON CONFLICT DO NOTHING""",
                        (tid, f"agent:{agent}", "costuma_fazer", obj))
                    created += cur.rowcount
        c.commit()
    return {"ok": True, "padroes_espelhados": created,
            "agentes_modelados": len(by_key)}


def sync_synapse() -> dict:
    """SINAPSE: conecta agentes a projetos no grafo (graph_edges), tenant real."""
    created = 0
    with _conn() as c:
        with c.cursor() as cur:
            cur.execute(
                """SELECT DISTINCT agent_id, project_slug, tenant_id FROM prometheus_project_events
                   WHERE agent_id IS NOT NULL AND agent_id <> ''""")
            triples_rows = cur.fetchall()
        with c.cursor() as cur:
            for agent, proj, tid in triples_rows:
                cur.execute(
                    """INSERT INTO graph_edges (tenant_id, source_id, target_id, relationship)
                       VALUES (%s, %s, %s, %s) ON CONFLICT DO NOTHING""",
                    (tid, f"agent:{agent}", f"proj:{proj}", "atuou_em"))
                created += cur.rowcount
        c.commit()
    return {"ok": True, "sinapses_criadas": created}


def query_synapse(tema: str, limit: int = 5, tenant_id: int | None = None) -> list[dict]:
    """SINAPSE: quem atuou/está ligado a um tema/projeto (via triples + edges)."""
    out = []
    with _conn() as c:
        with c.cursor() as cur:
            if tenant_id is not None:
                cur.execute(
                    """SELECT subject, predicate, object FROM triples
                       WHERE tenant_id=%s AND (object ILIKE %s OR subject ILIKE %s)
                       ORDER BY id DESC LIMIT %s""",
                    (tenant_id, f"%{tema}%", f"%{tema}%", limit))
            else:
                cur.execute(
                    """SELECT subject, predicate, object FROM triples
                       WHERE object ILIKE %s OR subject ILIKE %s
                       ORDER BY id DESC LIMIT %s""",
                    (f"%{tema}%", f"%{tema}%", limit))
            for r in cur.fetchall():
                out.append({"subject": r[0], "predicate": r[1], "object": r[2]})
            if tenant_id is not None:
                cur.execute(
                    """SELECT source_id, relationship, target_id FROM graph_edges
                       WHERE tenant_id=%s AND (source_id ILIKE %s OR target_id ILIKE %s)
                       ORDER BY id DESC LIMIT %s""",
                    (tenant_id, f"%{tema}%", f"%{tema}%", limit))
            else:
                cur.execute(
                    """SELECT source_id, relationship, target_id FROM graph_edges
                       WHERE source_id ILIKE %s OR target_id ILIKE %s
                       ORDER BY id DESC LIMIT %s""",
                    (f"%{tema}%", f"%{tema}%", limit))
            for r in cur.fetchall():
                out.append({"subject": r[0], "predicate": r[1], "object": r[2]})
    return out
