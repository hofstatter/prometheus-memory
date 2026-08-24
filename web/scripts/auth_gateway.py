#!/usr/bin/env python3
"""Auth Gateway multi-tenant (F5): emite/valida/revoga API keys por agente.

Cada agente/sessão (Hermes, OpenClaw, OpenCode, Codex, Claude-Code...) recebe 1
API key única para conectar ao Prometheus-Memory (MCP/REST). A key é armazenada
como hash SHA-256; o agente é mapeado para (tenant_id, agent_id, channel_id).

Uso:
  from auth_gateway import issue_key, validate_key, revoke_agent, list_agents
"""
from __future__ import annotations

import hashlib
import os
import secrets

import psycopg2
from psycopg2.extras import RealDictCursor

PG_URL = os.environ.get(
    "PROMETHEUS_PG_URL",
    "postgresql://prometheus@127.0.0.1:5432/prometheus_memory",
)


def _pg_url() -> str:
    """URL do PG: env PROMETHEUS_PG_URL → arquivo de config → default."""
    url = os.environ.get("PROMETHEUS_PG_URL", "").strip()
    if url:
        return url
    import json
    for cfg in ("/app/scripts/pg_config.json", "/opt/prometheus/pg_config.json", "pg_config.json"):
        if os.path.exists(cfg):
            try:
                return json.load(open(cfg)).get("url", "")
            except Exception:  # noqa: BLE001
                pass
    return PG_URL


def _conn() -> psycopg2.extensions.connection:
    return psycopg2.connect(_pg_url(), cursor_factory=RealDictCursor)


def hash_key(key: str) -> str:
    return hashlib.sha256(key.encode()).hexdigest()


def issue_key(tenant_id: int = 1, agent_id: str = "", harness: str = "",
              channel_id: str | None = None) -> str:
    """Gera uma API key única para o agente (retorna a key — mostrar 1x)."""
    if not agent_id:
        raise ValueError("agent_id é obrigatório")
    key = f"pm_{tenant_id}_{secrets.token_urlsafe(32)}"
    with _conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """INSERT INTO agents (tenant_id, agent_id, api_key_hash, harness, channel_id)
                   VALUES (%s,%s,%s,%s,%s)
                   ON CONFLICT (tenant_id, agent_id) DO UPDATE SET
                     api_key_hash=EXCLUDED.api_key_hash, harness=EXCLUDED.harness,
                     channel_id=EXCLUDED.channel_id, revoked_at=NULL""",
                (tenant_id, agent_id, hash_key(key), harness, channel_id or agent_id),
            )
        conn.commit()
    return key


def validate_key(api_key: str) -> dict | None:
    """Valida a API key → retorna {tenant_id, agent_id, channel_id, harness} ou None."""
    with _conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """SELECT tenant_id, agent_id, channel_id, harness
                   FROM agents WHERE api_key_hash=%s AND revoked_at IS NULL""",
                (hash_key(api_key),),
            )
            row = cur.fetchone()
    return dict(row) if row else None


def revoke_agent(tenant_id: int, agent_id: str) -> bool:
    """Revoga imediatamente a chave do agente."""
    with _conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE agents SET revoked_at=now() WHERE tenant_id=%s AND agent_id=%s",
                (tenant_id, agent_id),
            )
            conn.commit()
    return True


def list_agents(tenant_id: int | None = None) -> list[dict]:
    q = "SELECT tenant_id, agent_id, harness, channel_id, created_at, revoked_at FROM agents"
    params: tuple = ()
    if tenant_id is not None:
        q += " WHERE tenant_id=%s"
        params = (tenant_id,)
    q += " ORDER BY created_at DESC LIMIT 50"
    with _conn() as conn:
        with conn.cursor() as cur:
            cur.execute(q, params)
            return [dict(r) for r in cur.fetchall()]
