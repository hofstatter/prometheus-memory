#!/usr/bin/env python3
"""Prometheus Memory — camada multi-agente (scoping por agent_id via channel_id).

Cada agente tem um channel isolado: agent-<id>. Memórias de um agente não vazam
para outro (verificado: recall com channel_id filtra corretamente).
"""
import os
from pathlib import Path

MNEMOSYNE_HOME = Path(os.environ.get("MNEMOSYNE_HOME", Path.home() / ".hermes" / "mnemosyne"))
DB_PATH = Path(os.environ.get("PROMETHEUS_DB", MNEMOSYNE_HOME / "data" / "mnemosyne.db"))

_instances: dict = {}


def _mem(agent_id: str = ""):
    """Mnemosyne por channel (isolamento). agent_id vazio = channel default (compartilhado)."""
    channel = f"agent-{agent_id}" if agent_id else "default"
    if channel not in _instances:
        from mnemosyne.mcp_tools import Mnemosyne
        _instances[channel] = Mnemosyne(
            session_id="prometheus", db_path=str(DB_PATH),
            bank="default", channel_id=channel,
        )
    return _instances[channel]


def remember(content: str, agent_id: str = "", source: str = "api", importance: float = 0.5) -> str:
    return _mem(agent_id).remember(content, source=source, importance=importance)


def recall(query: str, agent_id: str = "", top_k: int = 5) -> list:
    if agent_id:
        return _mem(agent_id).recall(query, top_k=top_k, channel_id=f"agent-{agent_id}")
    return _mem("").recall(query, top_k=top_k)


def list_agents() -> list:
    """Canais de agentes com memória (distinct agent-<id> no DB)."""
    import sqlite3
    try:
        con = sqlite3.connect(str(DB_PATH))
        rows = con.execute(
            "SELECT DISTINCT channel_id FROM working_memory WHERE channel_id LIKE 'agent-%' ORDER BY channel_id"
        ).fetchall()
        con.close()
        return [r[0].replace("agent-", "") for r in rows if r[0]]
    except Exception:
        return []


def stats(agent_id: str = "") -> dict:
    return _mem(agent_id).get_stats()
