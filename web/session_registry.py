#!/usr/bin/env python3
"""Session Registry — sessões ativas + lanes de memória (Fase A0).

Lanes: sess:<harness>:<session_id> (efêmera) · proj:<slug> (canônica) · agent:<id> (backward).
Presença: active < 30s · idle 30s-5min · stale > 5min · closed explícito.
"""
import hashlib
from datetime import datetime

from prometheus_db import get_conn, init_schema

ACTIVE_MAX_S = 30
IDLE_MAX_S = 300


def now_iso() -> str:
    # Formato consistente p/ ordenação lexicográfica (space + microssegundos)
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")


def session_key(harness: str, harness_session_id: str) -> str:
    return f"{harness}:{harness_session_id}"


def _hash8(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()[:8]


# ─── Lanes (usam web/memory.py, import lazy p/ evitar ciclo) ───────────────

def remember_session(harness: str, session_id: str, content: str, source: str = "session",
                     importance: float = 0.5) -> str:
    sk = session_key(harness, session_id)
    from memory import remember_lane
    return remember_lane(channel=f"sess:{harness}:{session_id}", session=f"prom-sess-{_hash8(sk)}",
                         content=content, source=source, importance=importance, scope="session")


def remember_project(slug: str, content: str, source: str = "project",
                     importance: float = 0.5, agent_id: str = "") -> str:
    from memory import remember_lane
    return remember_lane(channel=f"proj:{slug}", session=f"prom-proj-{slug}",
                         content=content, source=source, importance=importance, scope="global")


def recall_lane(channel: str, query: str, top_k: int = 5) -> list:
    from memory import recall_lane as _recall
    return _recall(channel, query, top_k)


# ─── Sessões ───────────────────────────────────────────────────────────────

def start_session(envelope: dict) -> dict:
    init_schema()
    harness = (envelope.get("harness") or "").strip()
    hs_id = (envelope.get("harness_session_id") or "").strip()
    sk = session_key(harness, hs_id)

    from projects_registry import resolve_project
    res = resolve_project(
        project_slug=envelope.get("project_slug"),
        cwd=envelope.get("cwd"),
        git_remote=envelope.get("git_remote"),
        agent_id=envelope.get("agent_id", ""),
    )
    con = get_conn()
    try:
        con.execute(
            """INSERT OR IGNORE INTO prometheus_sessions
               (session_key, harness, harness_session_id, project_slug, agent_id, author_id, cwd, git_remote, current_action, status)
               VALUES (?,?,?,?,?,?,?,?,?, 'active')""",
            (sk, harness, hs_id, res["slug"], envelope.get("agent_id", ""), envelope.get("author_id", ""),
             envelope.get("cwd", ""), envelope.get("git_remote", ""), envelope.get("current_action", "")),
        )
        con.commit()
    finally:
        con.close()

    ctx = []
    try:
        ctx = recall_lane(f"proj:{res['slug']}", "decisao implementacao", top_k=3)
    except Exception:
        pass
    return {"session_key": sk, "project_slug": res["slug"], "confidence": res["confidence"],
            "needs_review": res["needs_review"], "context": ctx}


def heartbeat(session_key_: str, *, current_action=None, status=None) -> dict:
    init_schema()
    con = get_conn()
    try:
        cur = con.execute(
            """UPDATE prometheus_sessions SET last_seen_at = ?,
               current_action = COALESCE(?, current_action), status = COALESCE(?, status)
               WHERE session_key = ?""",
            (now_iso(), current_action, status, session_key_),
        )
        con.commit()
        ok = cur.rowcount > 0
    finally:
        con.close()
    return {"session_key": session_key_, "last_seen_at": now_iso(), "found": ok}


def close_session(session_key_: str) -> dict:
    init_schema()
    con = get_conn()
    try:
        cur = con.execute(
            "UPDATE prometheus_sessions SET status = 'closed', last_seen_at = ? WHERE session_key = ?",
            (now_iso(), session_key_),
        )
        con.commit()
        ok = cur.rowcount > 0
    finally:
        con.close()
    return {"session_key": session_key_, "status": "closed", "found": ok}


def _parse_ts(ts) -> float:
    """Parse timestamps sem depender de fromisoformat (compat Python 3.10)."""
    for fmt in ("%Y-%m-%d %H:%M:%S.%f", "%Y-%m-%d %H:%M:%S",
                "%Y-%m-%dT%H:%M:%S.%f", "%Y-%m-%dT%H:%M:%S"):
        try:
            return datetime.strptime(ts, fmt).timestamp()
        except ValueError:
            continue
    return 0.0


def presence(project_slug=None) -> list:
    init_schema()
    now = datetime.now().timestamp()
    con = get_conn()
    try:
        sql = ("SELECT session_key, harness, agent_id, project_slug, current_action, last_seen_at, status "
               "FROM prometheus_sessions WHERE status != 'closed'")
        params = []
        if project_slug:
            sql += " AND project_slug = ?"
            params.append(project_slug)
        rows = con.execute(sql, params).fetchall()
    finally:
        con.close()

    out = []
    for r in rows:
        last = _parse_ts(r["last_seen_at"]) if r["last_seen_at"] else 0.0
        age = now - last
        st = "active" if age <= ACTIVE_MAX_S else ("idle" if age <= IDLE_MAX_S else "stale")
        out.append({
            "session_key": r["session_key"],
            "harness": r["harness"],
            "agent_id": r["agent_id"],
            "project_slug": r["project_slug"],
            "current_action": r["current_action"],
            "last_seen_at": r["last_seen_at"],
            "status": st,
        })
    return out
