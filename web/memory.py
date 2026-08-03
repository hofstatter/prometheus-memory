#!/usr/bin/env python3
"""Prometheus Memory — camada multi-agente + lanes (Fase A0).

Multi-agente: channel isolado agent-<id> (backward compat). session_id por agente
(prom-agent-<id>) corrige a colisão de dedup exato entre agentes no Mnemosyne.

Lanes:
  sess:<harness>:<session_id> — sessão efêmera (scope=session)
  proj:<slug>                 — projeto canônico (scope=global)
  agent:<id>                  — agente (backward compat)
"""
import os
from pathlib import Path

MNEMOSYNE_HOME = Path(os.environ.get("MNEMOSYNE_HOME", Path.home() / ".hermes" / "mnemosyne"))
DB_PATH = Path(os.environ.get("PROMETHEUS_DB", MNEMOSYNE_HOME / "data" / "mnemosyne.db"))

_instances: dict = {}


def _lane(channel: str, session: str):
    if channel not in _instances:
        from mnemosyne.mcp_tools import Mnemosyne
        _instances[channel] = Mnemosyne(
            session_id=session, db_path=str(DB_PATH),
            bank="default", channel_id=channel,
        )
    return _instances[channel]


def _mem(agent_id: str = ""):
    """Mnemosyne por agent channel. session_id por agente."""
    channel = f"agent-{agent_id}" if agent_id else "default"
    session = f"prom-agent-{agent_id or 'default'}"
    return _lane(channel, session)


def remember(content: str, agent_id: str = "", source: str = "api", importance: float = 0.5) -> str:
    """Backward compat — mesma assinatura de sempre (channel agent-<id>)."""
    return _mem(agent_id).remember(content, source=source, importance=importance)


def recall(query: str, agent_id: str = "", top_k: int = 5) -> list:
    """Backward compat — filtra por channel agent-<id> quando agent_id presente."""
    if agent_id:
        return _mem(agent_id).recall(query, top_k=top_k, channel_id=f"agent-{agent_id}")
    return _mem("").recall(query, top_k=top_k)


def remember_lane(channel: str, session: str, content: str, source: str = "api",
                  importance: float = 0.5, scope: str = "global") -> str:
    """Grava em lane arbitrária (sess:* / proj:* / agent:*)."""
    return _lane(channel, session).remember(content, source=source, importance=importance, scope=scope)


def recall_lane(channel: str, query: str, top_k: int = 5) -> list:
    """Recall restrito a uma lane (filtro por channel_id no BEAM)."""
    return _lane(channel, "").recall(query, top_k=top_k, channel_id=channel)


def apply_threshold(results: list, threshold: float) -> list:
    """Filtra resultados abaixo do threshold de score (P0c — recall híbrido)."""
    if threshold is None or threshold <= 0:
        return results
    out = []
    for r in results:
        try:
            score = float(r.get("score") or 0)
        except (TypeError, ValueError):
            score = 0.0
        if score >= threshold:
            out.append(r)
    return out


def remember_inferred(content: str, *, agent_id: str = "", channel: str = None,
                      session: str = None, source: str = "api",
                      importance: float = 0.5) -> dict:
    """Mem0-style: extração LLM single-pass + dedup SHA-256 scoped por channel.

    channel/session explícitos → lane arbitrária (proj:<slug>); senão agent lane.
    Fallback: LLM indisponível → grava raw (degraded=True). Nunca quebra o write.
    """
    from datetime import date
    from dedup import content_hash, fetch_hashes, record_hashes
    from entity_store import extract_and_link
    from extractor import extract_facts, ground_temporal

    chan = channel or (f"agent-{agent_id}" if agent_id else "default")
    sess = session or f"prom-agent-{agent_id or 'default'}"
    today = date.today().isoformat()

    existing_hashes = fetch_hashes(chan)
    recent = []
    existing_texts = []
    try:
        recent = recall_lane(chan, "decisao implementacao", top_k=5)
        existing_texts = [x.get("content", "")[:300] for x in recall_lane(chan, content, top_k=10)]
    except Exception:
        pass
    recent_texts = [x.get("content", "")[:200] for x in recent]
    grounded = ground_temporal(content, today)

    facts = []
    try:
        facts = extract_facts(grounded, recent_texts, existing_texts, today)
    except Exception:
        facts = []
    # garantia pós-extração (N2): datas relativas que escaparem do prompt viram absolutas
    facts = [ground_temporal(f, today) for f in facts if f]

    if not facts:
        mid = remember_lane(chan, sess, content, source=source, importance=importance, scope="global")
        return {"ids": [mid], "stored": 1, "skipped_duplicates": 0, "degraded": True}

    ids, skipped = [], []
    for fact in facts:
        h = content_hash(fact)
        if h in existing_hashes:
            skipped.append(fact)
            continue
        existing_hashes.add(h)
        try:
            mid = remember_lane(chan, sess, fact, source=source, importance=importance, scope="global")
            ids.append((h, mid))
            try:
                extract_and_link(mid, fact)
            except Exception:
                pass
        except Exception:
            skipped.append(fact)
    record_hashes(chan, ids)
    return {"ids": [mid for _, mid in ids], "stored": len(ids),
            "skipped_duplicates": len(skipped), "degraded": False}


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
