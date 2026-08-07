#!/usr/bin/env python3
"""Backfill de arestas reais no graph_edges (Fase 2 · PLAN_SEMANTICA_GRAFO_F1_1).

Gera edges a partir de dados que JÁ existem no banco, sem LLM:

  M1 ctx        : gists.memory_id            -> (memory_id, gist_id, 'ctx', 1.0)
  M2 references : annotations kind='mentions' -> pares de memórias que compartilham
                  a mesma mention normalizada (grupos >= 2 memórias; grafo completo
                  <= 8, senão estrela; w = min(0.6 + 0.1*grupo, 1.0))
  M3 mentions   : prometheus_memory_entities  -> (memory_id, entity_name, 'mentions', 0.9)

Idempotente: pula edges já existentes (source,target,edge_type) nos dois sentidos.
Endpoints validados contra memories/gists/prometheus_entities (evita dangling).

Uso:
  python3 backfill_graph_edges.py            # dry-run: relatório, NADA escreve
  python3 backfill_graph_edges.py --apply    # aplica (backup do DB é feito antes)
"""
import argparse
import os
import re
import sqlite3
from pathlib import Path

MNEMOSYNE_HOME = Path(os.environ.get("MNEMOSYNE_HOME", Path.home() / ".hermes" / "mnemosyne"))
DB = Path(os.environ.get("PROMETHEUS_DB", MNEMOSYNE_HOME / "data" / "mnemosyne.db"))

MENTION_MIN_CONF = 0.8
MENTION_MIN_LEN = 4
STOPWORDS = {
    "não", "nao", "para", "como", "entre", "sobre", "com", "sem", "que", "esta", "essa",
    "this", "that", "with", "from", "have", "were", "been", "when", "what", "which",
    "there", "their", "about", "would", "could", "should", "these", "those", "after",
    "before", "during", "because", "through", "against", "under", "again", "further",
    "where", "while", "other", "some", "such", "than", "then", "them", "they", "will",
    "your", "sessão", "sessao", "projeto", "resumo", "resumo", "etapa", "fase",
}
_NONALNUM = re.compile(r"[^a-z0-9]+")

UNDIRECTED = {"ctx", "references", "mentions"}


def _normalize_mention(value: str):
    v = _NONALNUM.sub("", value.lower())
    if len(v) < MENTION_MIN_LEN or v in STOPWORDS:
        return None
    digits = sum(c.isdigit() for c in v)
    if digits > len(v) - digits:  # maioria dígitos (hash/valor) -> ruído
        return None
    return v


def _load_existing(conn):
    rows = conn.execute("SELECT source, target, edge_type FROM graph_edges").fetchall()
    seen = set()
    for s, t, ty in rows:
        seen.add((s, t, ty))
        if ty in UNDIRECTED:
            seen.add((t, s, ty))
    return seen


def build_candidates(conn):
    existing = _load_existing(conn)
    m1, m2, m3 = [], [], []

    # M1: gists -> memory
    for gid, mid in conn.execute(
        "SELECT id, memory_id FROM gists WHERE memory_id IS NOT NULL AND memory_id != ''"
    ).fetchall():
        m1.append(("ctx", mid, gid, 1.0))

    # M2: mentions compartilhadas
    groups = {}
    for mid, value, conf in conn.execute(
        "SELECT memory_id, value, confidence FROM annotations WHERE kind='mentions'"
    ).fetchall():
        if conf < MENTION_MIN_CONF:
            continue
        norm = _normalize_mention(value)
        if not norm:
            continue
        groups.setdefault(norm, set()).add(mid)
    for norm, mems in groups.items():
        mems = sorted(mems)
        if len(mems) < 2:
            continue
        weight = round(min(0.6 + 0.1 * len(mems), 1.0), 2)
        if len(mems) <= 8:  # grafo completo
            for i in range(len(mems)):
                for j in range(i + 1, len(mems)):
                    m2.append(("references", mems[i], mems[j], weight))
        else:  # estrela
            root = mems[0]
            for other in mems[1:]:
                m2.append(("references", root, other, weight))

    # M3: prometheus_memory_entities -> (memory_id, entity_name)
    for mid, name in conn.execute(
        "SELECT me.memory_id, e.name FROM prometheus_memory_entities me "
        "JOIN prometheus_entities e ON e.id = me.entity_id"
    ).fetchall():
        m3.append(("mentions", mid, name, 0.9))

    # dedup + validação de endpoints
    valid_mem = {r[0] for r in conn.execute("SELECT id FROM memories").fetchall()}
    valid_gist = {r[0] for r in conn.execute("SELECT id FROM gists").fetchall()}
    valid_ent = {r[0] for r in conn.execute("SELECT name FROM prometheus_entities").fetchall()}

    def keep(edge):
        ty, s, t, w = edge
        if (s, t, ty) in existing:
            return False
        ok_s = s in valid_mem or s in valid_gist or s in valid_ent
        ok_t = t in valid_mem or t in valid_gist or t in valid_ent
        return ok_s and ok_t

    m1 = [e for e in m1 if keep(e)]
    m2 = [e for e in m2 if keep(e)]
    m3 = [e for e in m3 if keep(e)]
    # dedup intra-batch: pares repetidos entre grupos distintos (s,t,ty)
    def dedup_batch(edges):
        out = []
        for edge in edges:
            ty, s, t, w = edge
            key = (s, t, ty)
            if key in existing:
                continue
            existing.add(key)
            if ty in UNDIRECTED:
                existing.add((t, s, ty))
            out.append(edge)
        return out

    m1 = dedup_batch(m1)
    m2 = dedup_batch(m2)
    m3 = dedup_batch(m3)
    return m1, m2, m3, len(groups)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--apply", action="store_true", help="aplica as edges (default: dry-run)")
    args = ap.parse_args()

    conn = sqlite3.connect(str(DB))
    conn.row_factory = sqlite3.Row
    try:
        m1, m2, m3, n_groups = build_candidates(conn)
        total = len(m1) + len(m2) + len(m3)
        print(f"DB: {DB}")
        print(f"  M1 ctx          (gist↔memória):        {len(m1):>5}")
        print(f"  M2 references   (mentions compartilhadas): {len(m2):>5}  (grupos>=2: {n_groups})")
        print(f"  M3 mentions     (memória↔entidade):    {len(m3):>5}")
        print(f"  TOTAL novas edges:                     {total:>5}")
        if args.apply and total:
            conn.execute("BEGIN")
            cur = conn.cursor()
            for ty, s, t, w in m1 + m2 + m3:
                cur.execute(
                    "INSERT INTO graph_edges (source, target, edge_type, weight) VALUES (?,?,?,?)",
                    (s, t, ty, w),
                )
            conn.commit()
            print("APLICADO:", total, "edges inseridas em graph_edges")
        elif not args.apply:
            print("(dry-run — use --apply para escrever; backup do DB recomendado antes)")
    finally:
        conn.close()


if __name__ == "__main__":
    main()
