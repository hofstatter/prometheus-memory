#!/usr/bin/env python3
"""Entity Store (Fase C — Mem0 parity, v1) — extração heurística + linking.

NER completo (LLM) fica para v1.1; aqui: entidades capitalizadas com linkage
memória↔entidade (prometheus_entities + prometheus_memory_entities).
"""
import re
import uuid

from prometheus_db import get_conn, init_schema

_STOP = {"Para", "Uma", "Um", "O", "A", "Os", "As", "Com", "De", "Da", "Do", "Em",
         "E", "Que", "Na", "No", "Por", "Ao", "Se", "Não", "Nao", "Como", "Mais",
         "Muito", "Tem", "Foi", "Ser", "Hoje", "Ontem", "Agora", "Amanhã"}


def extract_entities(text: str) -> set:
    """Nomes próprios heurísticos: palavras capitalizadas (1-2 tokens)."""
    cands = re.findall(r"\b[A-ZÀ-Ý][a-zà-ÿ0-9.-]{2,}(?: [A-ZÀ-Ý][a-zà-ÿ0-9.-]{2,})?", text or "")
    out = set()
    for c in cands:
        if c.split()[0] in _STOP:
            continue
        out.add(c.strip())
    return out


def extract_and_link(memory_id: str, text: str) -> int:
    init_schema()
    con = get_conn()
    linked = 0
    try:
        for name in extract_entities(text):
            row = con.execute(
                "SELECT id FROM prometheus_entities WHERE name = ? AND type = 'auto'", (name,)
            ).fetchone()
            if row:
                eid = row["id"]
                con.execute(
                    "UPDATE prometheus_entities SET last_seen = CURRENT_TIMESTAMP, "
                    "mention_count = mention_count + 1 WHERE id = ?", (eid,)
                )
            else:
                eid = uuid.uuid4().hex[:12]
                con.execute(
                    "INSERT INTO prometheus_entities (id, name, type) VALUES (?,?, 'auto')", (eid, name)
                )
            con.execute(
                "INSERT OR IGNORE INTO prometheus_memory_entities (memory_id, entity_id) VALUES (?,?)",
                (memory_id, eid),
            )
            linked += 1
        con.commit()
    finally:
        con.close()
    return linked


def memories_for(entity_name: str) -> list:
    init_schema()
    con = get_conn()
    try:
        rows = con.execute(
            """SELECT me.memory_id FROM prometheus_memory_entities me
               JOIN prometheus_entities e ON e.id = me.entity_id
               WHERE e.name = ?""",
            (entity_name,),
        ).fetchall()
        return [r["memory_id"] for r in rows]
    finally:
        con.close()


def list_entities(limit: int = 100) -> list:
    init_schema()
    con = get_conn()
    try:
        rows = con.execute(
            "SELECT name, type, mention_count, last_seen FROM prometheus_entities "
            "ORDER BY mention_count DESC LIMIT ?",
            (int(limit),),
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        con.close()
