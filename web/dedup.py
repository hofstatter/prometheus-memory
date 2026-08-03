#!/usr/bin/env python3
"""Dedup (Fase C — Mem0 parity) — hash SHA-256 normalizado, scoped por channel.

Sidecar prometheus_dedup_hashes (PRIMARY KEY channel+content_hash) — nunca ALTER
no upstream. SHA-256 no lugar do MD5 do Mem0 (mesmo custo, sem discussão cripto).
"""
import hashlib

from prometheus_db import get_conn, init_schema


def content_hash(text: str) -> str:
    norm = " ".join(text.lower().split())
    # Truncado para 128 bits (espaço de colisão equivalente ao MD5; suficiente p/ dedup, não cripto)
    return hashlib.sha256(norm.encode("utf-8")).hexdigest()[:32]


def fetch_hashes(channel: str) -> set:
    init_schema()
    con = get_conn()
    try:
        rows = con.execute(
            "SELECT content_hash FROM prometheus_dedup_hashes WHERE channel = ?", (channel,)
        ).fetchall()
        return {r["content_hash"] for r in rows}
    finally:
        con.close()


def record_hash(channel: str, content_hash_: str, memory_id: str) -> None:
    record_hashes(channel, [(content_hash_, memory_id)])


def record_hashes(channel: str, pairs: list) -> None:
    """Insere em batch (1 conexão) — evita N conexões no loop de remember_inferred."""
    if not pairs:
        return
    init_schema()
    con = get_conn()
    try:
        con.executemany(
            "INSERT OR IGNORE INTO prometheus_dedup_hashes (channel, content_hash, memory_id) "
            "VALUES (?,?,?)",
            [(channel, h, mid) for h, mid in pairs],
        )
        con.commit()
    finally:
        con.close()
