#!/usr/bin/env python3
"""Atlas — L3 Persona por tenant (F8): sintetiza o perfil de cada usuário/cliente.

Coleta do PG (eventos, projetos, agentes, memórias) → sintetiza a persona L3
(estatísticas + DeepSeek se disponível) → salva como memória de alta importância
no working_memory (source='persona_l3', importance 0.95).

Uso: from persona_l3 import synthesize_all, synthesize_tenant
"""
from __future__ import annotations

import json
import os
import urllib.request

PERSONA_IMPORTANCE = 0.95


def _pg_url() -> str:
    url = os.environ.get("PROMETHEUS_PG_URL", "").strip()
    if url:
        return url
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


def _tenant_data(conn, tenant_id: int) -> dict:
    """Dados do tenant para a síntese: projetos, agentes, eventos, memórias."""
    with conn.cursor() as cur:
        cur.execute("SELECT name FROM tenants WHERE id=%s", (tenant_id,))
        row = cur.fetchone()
        name = row[0] if row else f"tenant-{tenant_id}"
        cur.execute("SELECT agent_id, harness FROM agents WHERE tenant_id=%s AND revoked_at IS NULL", (tenant_id,))
        agents = [{"agent": r[0], "harness": r[1]} for r in cur.fetchall()]
        cur.execute("SELECT slug FROM prometheus_projects WHERE tenant_id=%s", (tenant_id,))
        projects = [r[0] for r in cur.fetchall()]
        cur.execute(
            """SELECT event_type, COUNT(*) FROM prometheus_project_events
               WHERE tenant_id=%s GROUP BY event_type ORDER BY 2 DESC LIMIT 6""", (tenant_id,))
        events = [{"tipo": r[0], "n": r[1]} for r in cur.fetchall()]
        cur.execute("SELECT COUNT(*) FROM working_memory WHERE tenant_id=%s", (tenant_id,))
        memories = cur.fetchone()[0]
        cur.execute(
            """SELECT MAX(created_at) FROM prometheus_project_events WHERE tenant_id=%s""", (tenant_id,))
        last_activity = cur.fetchone()[0]
    return {"tenant_id": tenant_id, "name": name, "agents": agents,
            "projects": projects, "event_types": events,
            "memories": memories, "last_activity": str(last_activity)[:19] if last_activity else None}


def _llm_persona(data: dict) -> str:
    """Tenta DeepSeek; fallback: síntese estatística (sem LLM)."""
    key = os.environ.get("DEEPSEEK_API_KEY", "").strip()
    if not key:
        return _stat_persona(data)
    prompt = (
        "Sintetize a persona L3 (perfil) deste cliente/tenant em 3-4 linhas, em português:\n"
        + json.dumps(data, ensure_ascii=False)
        + "\nFormato: 'Tenant X: stack/projetos, agentes, padrões de trabalho, interesses.'"
    )
    try:
        body = json.dumps({"model": "deepseek-chat",
                           "messages": [{"role": "user", "content": prompt}],
                           "max_tokens": 300}).encode()
        req = urllib.request.Request(
            "https://api.deepseek.com/chat/completions", data=body,
            headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=60) as r:
            return json.loads(r.read())["choices"][0]["message"]["content"][:500]
    except Exception:  # noqa: BLE001
        return _stat_persona(data)


def _stat_persona(data: dict) -> str:
    """Persona estatística (fallback sem LLM)."""
    projs = ", ".join(data["projects"][:5]) or "nenhum"
    ags = ", ".join(f"{a['agent']}({a['harness'] or '?'})" for a in data["agents"][:5]) or "nenhum"
    evs = ", ".join(f"{e['tipo']}x{e['n']}" for e in data["event_types"][:4]) or "sem eventos"
    return (f"Tenant {data['name']}: projetos [{projs}]; agentes [{ags}]; "
            f"{data['memories']} memórias; atividade recente: {evs}.")


def synthesize_tenant(conn, tenant_id: int) -> str:
    """Sintetiza e grava a persona L3 do tenant (upsert por source)."""
    data = _tenant_data(conn, tenant_id)
    persona = _llm_persona(data)
    content = f"[persona] tenant:{data['name']} | {persona}"
    import hashlib
    mid = hashlib.sha256(f"persona:{tenant_id}".encode()).hexdigest()[:16]
    with conn.cursor() as cur:
        cur.execute(
            """INSERT INTO working_memory (id, tenant_id, content, source, importance, content_tsv)
               VALUES (%s,%s,%s,'persona_l3',%s, to_tsvector('portuguese', %s))
               ON CONFLICT (tenant_id, id) DO UPDATE SET content=EXCLUDED.content,
                 importance=EXCLUDED.importance, content_tsv=EXCLUDED.content_tsv""",
            (mid, tenant_id, content, PERSONA_IMPORTANCE, content))
    conn.commit()
    return content


def synthesize_all() -> dict:
    """Sintetiza persona de TODOS os tenants."""
    with _conn() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT id FROM tenants ORDER BY id")
            tids = [r[0] for r in cur.fetchall()]
        out = {}
        for tid in tids:
            try:
                out[tid] = synthesize_tenant(conn, tid)
            except Exception as e:  # noqa: BLE001
                out[tid] = f"erro: {e}"
    return {"ok": True, "personas": {k: v[:80] for k, v in out.items()}}


if __name__ == "__main__":
    print(json.dumps(synthesize_all(), ensure_ascii=False, indent=2))
