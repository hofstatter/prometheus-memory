#!/usr/bin/env python3
"""Backend PostgreSQL do Prometheus-Memory (F2) — base para recall/store/grafo.

O Mnemosyne upstream (3.16) NÃO tem backend PG (sqlite3/vec0 entrelaçado — ver
DECISIONS.md). Este módulo é o storage PG do Prometheus-Memory (nosso produto),
usado pelas fases F3 (sidecar), F5 (multi-tenant) e pelo Atlas.

Uso: conn = pg_conn(); pg_store(conn, ...); pg_recall(conn, ...)
Requer: psycopg2-binary (instalar no ambiente que rodar o Prometheus-Memory).
"""
from __future__ import annotations
import os

# DATABASE_URL exemplo: postgresql://prometheus:<senha>@127.0.0.1:5432/prometheus_memory
# (ou via pgBouncer na 6432: postgresql://prometheus:<senha>@127.0.0.1:6432/prometheus_memory)
DATABASE_URL = os.environ.get(
    "PROMETHEUS_PG_URL",
    "postgresql://prometheus@127.0.0.1:5432/prometheus_memory",
)

try:
    import psycopg2
    from psycopg2.extras import Json as _Json
except ImportError:  # pragma: no cover
    psycopg2 = None
    _Json = None


def pg_conn():
    """Retorna conexão PG (com pool futuro via pgBouncer)."""
    if psycopg2 is None:
        raise RuntimeError("psycopg2-binary não instalado — pip install psycopg2-binary")
    return psycopg2.connect(DATABASE_URL)


# ---------- store ----------
def pg_store(conn, content: str, source: str = "prometheus", importance: float = 0.5,
             session_id: str = "", channel_id: str = "", tenant_id: int = 1,
             embedding: list | None = None, metadata: dict | None = None) -> str:
    """Insere (ou atualiza) uma memória em working_memory."""
    import hashlib
    mid = hashlib.sha256(content.encode()).hexdigest()[:16]
    with conn.cursor() as cur:
        cur.execute(
            """INSERT INTO working_memory
               (id, tenant_id, content, source, session_id, importance, channel_id, metadata_json, embedding, content_tsv)
               VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s, to_tsvector('portuguese', %s))
               ON CONFLICT (tenant_id, id) DO UPDATE SET content=EXCLUDED.content,
                 importance=EXCLUDED.importance, embedding=EXCLUDED.embedding,
                 content_tsv=EXCLUDED.content_tsv""",
            (mid, tenant_id, content, source, session_id or None, importance,
             channel_id or None, _Json(metadata) if metadata else None,
             embedding, content),
        )
    conn.commit()
    return mid


# ---------- recall ----------
def pg_recall(conn, query: str, top_k: int = 5, tenant_id: int = 1,
              channel_id: str = "", use_vector: bool = False,
              embedding: list | None = None) -> list[dict]:
    """Recall por full-text (tsvector) e/ou vetorial (pgvector)."""
    rows = []
    with conn.cursor() as cur:
        if use_vector and embedding:
            cur.execute(
                """SELECT id, content, importance, embedding <=> %s::vector AS dist
                   FROM working_memory
                   WHERE tenant_id=%s AND (%s='' OR channel_id=%s)
                   ORDER BY embedding <=> %s::vector LIMIT %s""",
                (embedding, tenant_id, channel_id, channel_id, embedding, top_k),
            )
        else:
            cur.execute(
                """SELECT id, content, importance, ts_rank(content_tsv, plainto_tsquery('portuguese', %s)) AS r
                   FROM working_memory
                   WHERE tenant_id=%s AND content_tsv @@ plainto_tsquery('portuguese', %s)
                     AND (%s='' OR channel_id=%s)
                   ORDER BY r DESC, importance DESC LIMIT %s""",
                (query, tenant_id, query, channel_id, channel_id, top_k),
            )
        for r in cur.fetchall():
            rows.append({"id": r[0], "content": r[1], "importance": r[2],
                         "score": float(r[3] or 0)})
    return rows


# ---------- grafo ----------
def pg_add_triple(conn, subject: str, predicate: str, obj: str, tenant_id: int = 1) -> int:
    with conn.cursor() as cur:
        cur.execute(
            "INSERT INTO triples (tenant_id, subject, predicate, object) VALUES (%s,%s,%s,%s) RETURNING id",
            (tenant_id, subject, predicate, obj),
        )
        tid = cur.fetchone()[0]
    conn.commit()
    return tid


def pg_add_edge(conn, source_id: str, target_id: str, relationship: str,
                weight: float = 0.5, tenant_id: int = 1) -> int:
    with conn.cursor() as cur:
        cur.execute(
            """INSERT INTO graph_edges (tenant_id, source_id, target_id, relationship, weight)
               VALUES (%s,%s,%s,%s,%s) RETURNING id""",
            (tenant_id, source_id, target_id, relationship, weight),
        )
        eid = cur.fetchone()[0]
    conn.commit()
    return eid


# ---------- stats ----------
def pg_stats(conn, tenant_id: int = 1) -> dict:
    with conn.cursor() as cur:
        cur.execute("SELECT COUNT(*) FROM working_memory WHERE tenant_id=%s", (tenant_id,))
        wm = cur.fetchone()[0]
        cur.execute("SELECT COUNT(*) FROM episodic_memory WHERE tenant_id=%s", (tenant_id,))
        ep = cur.fetchone()[0]
        cur.execute("SELECT COUNT(*) FROM triples WHERE tenant_id=%s", (tenant_id,))
        tr = cur.fetchone()[0]
    return {"working_memory": wm, "episodic_memory": ep, "triples": tr}


# ---------- sidecar prometheus_* (F3) ----------
def pg_project_upsert(conn, slug: str, name: str | None = None, repo_path: str | None = None,
                      tenant_id: int = 1) -> None:
    with conn.cursor() as cur:
        cur.execute(
            """INSERT INTO prometheus_projects (tenant_id, slug, name, repo_path, updated_at)
               VALUES (%s,%s,%s,%s, now())
               ON CONFLICT (tenant_id, slug) DO UPDATE SET name=EXCLUDED.name,
                 repo_path=EXCLUDED.repo_path, updated_at=now()""",
            (tenant_id, slug, name, repo_path),
        )
    conn.commit()


def pg_event_add(conn, project_slug: str, event_type: str, title: str,
                 agent_id: str | None = None, harness: str | None = None,
                 session_key: str | None = None, summary: str | None = None,
                 status_hint: str | None = None, memory_id: str | None = None,
                 tenant_id: int = 1) -> str:
    import hashlib
    eid = hashlib.sha256(f"{project_slug}:{title}:{agent_id}".encode()).hexdigest()[:16]
    with conn.cursor() as cur:
        cur.execute(
            """INSERT INTO prometheus_project_events
               (id, tenant_id, project_slug, session_key, harness, agent_id, event_type,
                title, summary, memory_id, status_hint)
               VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
               ON CONFLICT (id) DO NOTHING""",
            (eid, tenant_id, project_slug, session_key, harness, agent_id,
             event_type, title, summary, memory_id, status_hint),
        )
    conn.commit()
    return eid


def pg_sessions_recent(conn, tenant_id: int = 1, limit: int = 20) -> list[dict]:
    with conn.cursor() as cur:
        cur.execute(
            """SELECT project_slug, agent_id, session_id, harness, started_at, last_seen_at, status
               FROM prometheus_sessions WHERE tenant_id=%s
               ORDER BY last_seen_at DESC LIMIT %s""",
            (tenant_id, limit),
        )
        cols = [d[0] for d in cur.description]
        return [dict(zip(cols, r)) for r in cur.fetchall()]


def pg_projects_list(conn, tenant_id: int = 1) -> list[dict]:
    with conn.cursor() as cur:
        cur.execute(
            """SELECT slug, name, repo_path, created_at, updated_at
               FROM prometheus_projects WHERE tenant_id=%s ORDER BY slug""",
            (tenant_id,),
        )
        cols = [d[0] for d in cur.description]
        return [dict(zip(cols, r)) for r in cur.fetchall()]


if __name__ == "__main__":
    # smoke: teste rápido (requer psycopg2 e PG up)
    c = pg_conn()
    mid = pg_store(c, "Teste do backend PG do Prometheus-Memory (F2)", source="pg_backend")
    print("store:", mid)
    print("recall:", pg_recall(c, "backend postgres"))
    print("stats:", pg_stats(c))
    c.close()
