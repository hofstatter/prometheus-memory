#!/usr/bin/env python3
"""Prometheus Memory — Serviço de Grafo Real (F1 · PLAN_SEMANTICA_GRAFO_F1).

Lê graph_edges / triples / gists / facts / prometheus_entities do SQLite do
Mnemosyne (read-only) e computa analytics (degree centrality + PageRank) em
Python puro — sem dependências novas.

PageRank/degree adaptados de semantica-agi/semantica (MIT):
  kg/centrality_calculator.py — https://github.com/semantica-agi/semantica
"""
import os
import re
import sqlite3
from pathlib import Path

MNEMOSYNE_HOME = Path(os.environ.get("MNEMOSYNE_HOME", Path.home() / ".hermes" / "mnemosyne"))
MNEMOSYNE_DB = Path(os.environ.get("PROMETHEUS_DB", MNEMOSYNE_HOME / "data" / "mnemosyne.db"))

EDGE_TYPE_COLORS = {
    "ctx": "#22d3ee",
    "related_to": "#a78bfa",
    "references": "#34d399",
    "caused": "#f87171",
    "influenced": "#f97316",
    "supersedes": "#fbbf24",
    "precedent_for": "#60a5fa",
    "syn": "#fb7185",
}
DEFAULT_EDGE_COLOR = "#4a4f7a"
ENTITY_TYPE_COLORS = {"project": "#f472b6", "tech": "#38bdf8", "auto": "#a3e635", "person": "#fb923c"}

_EDGE_QUERY = """
    SELECT id, source, target, edge_type, weight, timestamp
    FROM graph_edges ORDER BY id DESC LIMIT ?
"""
_TRIPLE_QUERY = """
    SELECT id, subject, predicate, object, valid_from, valid_until, confidence
    FROM triples ORDER BY id DESC LIMIT ?
"""
_FACT_ID_RE = re.compile(r"^fact_([0-9a-fA-F]{12,})_\d+$")
_THINK_RE = re.compile(r"<think>.*?</think>|<think>.*$", flags=re.DOTALL)
_PROJECT_TAG_RE = re.compile(r"^\[([^\]]+)\]")

# Paleta de projetos (fallback quando prometheus_projects.color não está disponível)
PROJECT_COLORS = {
    "nb02": "#22d3ee", "evscar": "#f472b6", "pipesales": "#3562fc",
    "bytex": "#a78bfa", "provador-digital": "#34d399", "alook": "#fbbf24",
    "ods": "#fb7185", "global": "#94a3b8", "entidades": "#38bdf8",
}

# Aliases de slug aceitos mesmo sem registro em prometheus_projects
KNOWN_PROJECT_ALIASES = {
    "nb02", "evscar", "pipesales", "bytex", "bytex_agentos", "alook",
    "provador", "provador-digital", "prometheus-memory", "ods", "global",
    "entidades",
}


_slug_cache = {"mtime": None, "slugs": None}


def _load_valid_project_slugs() -> set:
    """Slugs reais de prometheus_projects (fonte da verdade) + aliases conhecidos.
    Cacheado por mtime do DB — evita N+1 conexões no _project_of por nó."""
    global _slug_cache
    mtime = None
    try:
        mtime = os.path.getmtime(MNEMOSYNE_DB)
        if _slug_cache["mtime"] == mtime and _slug_cache["slugs"]:
            return _slug_cache["slugs"]
    except OSError:
        pass
    slugs = set(KNOWN_PROJECT_ALIASES)
    try:
        conn = _connect()
        try:
            rows = conn.execute("SELECT slug FROM prometheus_projects").fetchall()
        finally:
            conn.close()
        slugs.update(r["slug"].strip().lower() for r in rows if r["slug"])
    except Exception:
        pass
    _slug_cache = {"mtime": mtime, "slugs": slugs}
    return slugs


def _project_of(content: str, metadata_json: str = "") -> str:
    """Extrai o projeto de uma memória.

    Prioridade: campo `project` do metadata_json → prefixo '[tag]' do conteúdo.
    Só aceita slugs de projetos REAIS (prometheus_projects + aliases conhecidos);
    tags-lixo (syntaxerror, graph_service, session_registry, checkpoint-cycle...)
    caem em 'global'. Ausência total → 'global'.
    """
    valid = _load_valid_project_slugs()
    # 1. metadata_json.project (fonte mais confiável quando presente)
    if metadata_json:
        try:
            import json as _json
            m = _json.loads(metadata_json)
            p = str(m.get("project") or "").strip().lower()
            if p and p in valid:
                return "bytex" if p == "bytex_agentos" else p
        except Exception:
            pass
    # 2. prefixo [tag] do conteúdo
    m = _PROJECT_TAG_RE.match((content or "").strip())
    if m:
        tag = m.group(1).strip().lower()
        if tag.startswith("checkpoint-cycle"):
            return "global"
        if tag in valid:
            # normaliza aliases → slug canônico
            if tag == "bytex_agentos":
                return "bytex"
            return tag
        return "global"
    # 3. ausência
    return "global"


def _load_project_colors() -> dict:
    """Lê slug → color de prometheus_projects (se a tabela existir)."""
    try:
        conn = _connect()
        try:
            rows = conn.execute(
                "SELECT slug, color FROM prometheus_projects WHERE color IS NOT NULL"
            ).fetchall()
        finally:
            conn.close()
        return {r["slug"]: r["color"] for r in rows}
    except Exception:
        return {}


def _connect() -> sqlite3.Connection:
    conn = sqlite3.connect(f"file:{MNEMOSYNE_DB}?mode=ro", uri=True, timeout=5)
    conn.row_factory = sqlite3.Row
    return conn


def _clean_text(t: str) -> str:
    if not t:
        return ""
    t = _THINK_RE.sub("", t)
    return t.strip()


def pagerank(adj: dict, damping: float = 0.85, max_iter: int = 100, tol: float = 1e-6) -> dict:
    """PageRank sobre dict de adjacência {node: [vizinhos]}.

    Adaptado de semantica/kg/centrality_calculator.py (MIT). Grafo tratado como
    não-direcionado (cada aresta entra nos dois sentidos) — estabiliza grafos
    pequenos com poucas conexões.
    """
    n = len(adj)
    if n == 0:
        return {}
    rank = {k: 1.0 / n for k in adj}
    for _ in range(max_iter):
        diff = 0.0
        new_rank = {}
        for node, neigh in adj.items():
            s = sum(rank[o] / len(adj[o]) for o in neigh if len(adj[o]) > 0)
            new_rank[node] = (1 - damping) / n + damping * s
            diff += abs(new_rank[node] - rank[node])
        rank = new_rank
        if diff < tol:
            break
    return rank


def fetch_graph(limit: int = 250, include_entities: bool = True) -> dict:
    """Grafo real: nós (gists/facts/entidades/conceitos) + arestas reais + analytics."""
    conn = _connect()
    try:
        edges = [dict(r) for r in conn.execute(_EDGE_QUERY, (limit,)).fetchall()]
        triples = [dict(r) for r in conn.execute(_TRIPLE_QUERY, (limit,)).fetchall()]

        gist_map = {r["id"]: r for r in conn.execute("SELECT id, text, memory_id FROM gists").fetchall()}
        fact_map = {r["fact_id"]: r for r in conn.execute("SELECT fact_id, subject, predicate, object FROM facts").fetchall()}
        try:
            # metadata_json pode não existir em DBs antigos → fallback p/ metadata vazio
            memory_map = {
                r["id"]: {"content": r["content"], "metadata": r["metadata_json"] or ""}
                for r in conn.execute("SELECT id, content, metadata_json FROM memories").fetchall()
            }
        except sqlite3.OperationalError:
            memory_map = {
                r["id"]: {"content": r["content"], "metadata": ""}
                for r in conn.execute("SELECT id, content FROM memories").fetchall()
            }
        entity_map = {
            r["name"]: r for r in conn.execute(
                "SELECT id, name, type, mention_count FROM prometheus_entities").fetchall()
        } if include_entities else {}
        # Mapa memory_id → projeto real (metadata.project → prefixo [tag] do conteúdo)
        project_of_memory = {
            mid: _project_of(v["content"], v["metadata"]) for mid, v in memory_map.items()
        }
        project_colors = _load_project_colors()
    finally:
        conn.close()

    # ── nós: endpoints das arestas + subjects/objects das triplas ──
    node_ids: set = set()
    for e in edges:
        node_ids.add(e["source"])
        node_ids.add(e["target"])
    for t in triples:
        node_ids.add(t["subject"])
        node_ids.add(t["object"])

    nodes = []
    for nid in node_ids:
        if nid.startswith("gist_") and nid in gist_map:
            g = gist_map[nid]
            proj = project_of_memory.get(g["memory_id"] or "", "global")
            nodes.append({
                "id": nid,
                "label": _clean_text(g["text"])[:48],
                "tier": "L2",
                "color": project_colors.get(proj, PROJECT_COLORS.get(proj, "#3b82f6")),
                "project": proj,
                "data": {
                    "type": "memory", "content": _clean_text(g["text"]),
                    "memory_id": g["memory_id"] or "", "degree": 0, "pagerank": 0.0,
                },
            })
        elif nid.startswith("fact_") and nid in fact_map:
            f = fact_map[nid]
            label = f"{f['subject']} → {f['object']}"[:48]
            fmid = _fact_memory_id(nid)
            proj = project_of_memory.get(fmid, "global")
            nodes.append({
                "id": nid,
                "label": label,
                "tier": "L1",
                "color": project_colors.get(proj, PROJECT_COLORS.get(proj, "#94a3b8")),
                "project": proj,
                "data": {
                    "type": "memory", "content": label,
                    "memory_id": fmid, "degree": 0, "pagerank": 0.0,
                },
            })
        elif nid in memory_map:
            text = memory_map[nid]["content"]
            proj = project_of_memory.get(nid, "global")
            nodes.append({
                "id": nid,
                "label": _clean_text(text)[:48],
                "tier": "L1",
                "color": project_colors.get(proj, PROJECT_COLORS.get(proj, "#94a3b8")),
                "project": proj,
                "data": {
                    "type": "memory", "content": _clean_text(text),
                    "memory_id": nid, "degree": 0, "pagerank": 0.0,
                },
            })
        elif nid in entity_map:
            ent = entity_map[nid]
            nodes.append({
                "id": nid,
                "label": nid,
                "tier": "L3",
                "color": ENTITY_TYPE_COLORS.get(ent["type"], "#a78bfa"),
                "project": "entidades",
                "data": {
                    "type": "entity", "content": f"Entidade {ent['type']} · {ent['mention_count']} menções",
                    "memory_id": "", "degree": 0, "pagerank": 0.0,
                },
            })
        else:
            nodes.append({
                "id": nid,
                "label": nid[:32],
                "tier": "L1",
                "color": "#7c83ff",
                "project": "conceito",
                "data": {
                    "type": "concept", "content": nid,
                    "memory_id": "", "degree": 0, "pagerank": 0.0,
                },
            })

    # ── arestas: graph_edges reais + triplas (predicate = tipo) ──
    result_edges = []
    seen_edges = set()
    UNDIRECTED_TYPES = {"ctx", "references", "mentions"}
    for e in edges:
        key = (e["source"], e["target"], e["edge_type"])
        if key in seen_edges:
            continue
        seen_edges.add(key)
        if e["edge_type"] in UNDIRECTED_TYPES:
            seen_edges.add((e["target"], e["source"], e["edge_type"]))
        result_edges.append({
            "source": e["source"], "target": e["target"],
            "type": e["edge_type"], "label": e["edge_type"],
            "weight": e["weight"] or 1.0,
            "color": EDGE_TYPE_COLORS.get(e["edge_type"], DEFAULT_EDGE_COLOR),
        })
    for t in triples:
        key = (t["subject"], t["object"], t["predicate"])
        if key in seen_edges:
            continue
        seen_edges.add(key)
        result_edges.append({
            "source": t["subject"], "target": t["object"],
            "type": t["predicate"], "label": t["predicate"],
            "weight": t["confidence"] or 1.0,
            "color": EDGE_TYPE_COLORS.get(t["predicate"], DEFAULT_EDGE_COLOR),
        })

    # ── analytics: degree (não-direcionado) + PageRank ──
    degree_map = {n["id"]: 0 for n in nodes}
    adj = {n["id"]: [] for n in nodes}
    for e in result_edges:
        if e["source"] in degree_map and e["target"] in degree_map:
            if e["target"] not in adj[e["source"]]:
                adj[e["source"]].append(e["target"])
                adj[e["target"]].append(e["source"])
                degree_map[e["source"]] += 1
                degree_map[e["target"]] += 1
    pr = pagerank(adj)
    for n in nodes:
        n["data"]["degree"] = degree_map.get(n["id"], 0)
        n["data"]["pagerank"] = round(pr.get(n["id"], 0.0), 6)

    edge_type_counts: dict = {}
    for e in result_edges:
        edge_type_counts[e["type"]] = edge_type_counts.get(e["type"], 0) + 1
    top_pr = sorted(((n["id"], n["data"]["pagerank"]) for n in nodes), key=lambda x: x[1], reverse=True)[:5]

    from datetime import datetime, timezone
    return {
        "nodes": nodes,
        "edges": result_edges,
        "project_colors": project_colors,
        "analytics": {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "node_count": len(nodes),
            "edge_count": len(result_edges),
            "edge_type_counts": edge_type_counts,
            "top_pagerank": [{"id": i, "pagerank": p} for i, p in top_pr],
        },
        "meta": {"source": "graph_edges+triples", "limit": limit},
    }


def _fact_memory_id(endpoint: str) -> str:
    m = _FACT_ID_RE.match(endpoint)
    return m.group(1) if m else ""


def degree_by_memory(limit: int = 2000) -> dict:
    """Mapa {memory_id: grau} — endpoints gist_*/fact_* resolvidos para id de memória.

    Usado para expor o grau no recall (`graph_degree`); o boost real de scoring
    já é aplicado upstream (beam.py MNEMOSYNE_GRAPH_BONUS) — aqui só leitura.
    """
    conn = _connect()
    try:
        rows = conn.execute(_EDGE_QUERY, (limit,)).fetchall()
        gist_map = {r["id"]: r["memory_id"] for r in conn.execute("SELECT id, memory_id FROM gists").fetchall()}
    finally:
        conn.close()
    deg: dict = {}
    for r in rows:
        for ep in (r["source"], r["target"]):
            mid = gist_map.get(ep) or _fact_memory_id(ep)
            if mid:
                deg[mid] = deg.get(mid, 0) + 1
    return deg
