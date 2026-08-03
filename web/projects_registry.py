#!/usr/bin/env python3
"""Project Registry — Project Resolver v1 + ingest idempotente + relatório v1.

Fase A0: eventos de projeto via lanes sidecar prometheus_*. A memória canônica
é gravada na lane proj:<slug> somente quando confidence >= 0.6 (sem needs_review).
"""
import os
import re
import uuid
from datetime import datetime
from pathlib import Path

from prometheus_db import get_conn, init_schema

KNOWN_PROJECTS = [x.strip() for x in os.environ.get("PROMETHEUS_PROJECTS", "").split(",") if x.strip()]
PROJECTS_ROOT = Path(os.environ.get("PROMETHEUS_PROJECTS_ROOT", str(Path.home() / "Projetos")))

WEIGHTS = {
    "plan": 1.0,
    "decision": 2.0,
    "implementation": 4.0,
    "issue_resolved": 3.0,
    "skill_created": 2.0,
    "research": 1.0,
    "note": 0.5,
    "issue": 1.0,
}
DONE_HINTS = {"done", "resolved"}
CONFIDENCE_OK = 0.6


def now_iso() -> str:
    # Formato consistente p/ ordenação lexicográfica (space + microssegundos)
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")


def slugify(name: str) -> str:
    s = re.sub(r"[^a-z0-9-]", "-", str(name).lower()).strip("-")
    return s or "geral"


def _project_from_cwd(cwd) -> str | None:
    """Primeiro diretório sob PROJECTS_ROOT contido no cwd (monorepo-aware)."""
    if not cwd:
        return None
    try:
        p = Path(cwd).resolve()
        rel = p.relative_to(PROJECTS_ROOT.resolve())
        return rel.parts[0] if rel.parts else None
    except (ValueError, OSError):
        return None


def _project_from_git_remote(git_remote) -> str | None:
    if not git_remote:
        return None
    g = str(git_remote).strip()
    m = re.search(r"[:/]([\w.-]+/[\w.-]+?)(?:\.git)?$", g)
    if not m:
        return None
    parts = m.group(1).split("/")
    return parts[-1] if parts else None


def _project_exists(slug: str) -> bool:
    init_schema()
    con = get_conn()
    try:
        row = con.execute("SELECT 1 FROM prometheus_projects WHERE slug = ?", (slug,)).fetchone()
        return row is not None
    finally:
        con.close()


def resolve_project(*, project_slug=None, cwd=None, git_remote=None, agent_id="", text=""):
    """Retorna {slug, confidence, source, needs_review}. Sinais em ordem de força."""
    if project_slug and str(project_slug).strip():
        return {"slug": slugify(project_slug), "confidence": 1.0, "source": "explicit", "needs_review": False}

    slug = _project_from_cwd(cwd)
    if slug:
        known = slugify(slug) in {slugify(k) for k in KNOWN_PROJECTS} or _project_exists(slugify(slug))
        return {"slug": slugify(slug), "confidence": 0.95 if known else 0.9,
                "source": "cwd", "needs_review": False}

    slug = _project_from_git_remote(git_remote)
    if slug:
        return {"slug": slugify(slug), "confidence": 0.9, "source": "git_remote", "needs_review": False}

    # Sinal 4: sessão recente do mesmo agente (última não-closed)
    if agent_id:
        init_schema()
        con = get_conn()
        try:
            row = con.execute(
                "SELECT project_slug FROM prometheus_sessions WHERE agent_id = ? AND status != 'closed' "
                "ORDER BY last_seen_at DESC LIMIT 1",
                (agent_id,),
            ).fetchone()
            if row and row["project_slug"]:
                return {"slug": row["project_slug"], "confidence": 0.75, "source": "recent_session",
                        "needs_review": False}
        finally:
            con.close()

    m = re.search(r"\[([\w][\w-]*)\]", text or "")
    if m and m.group(1).lower() not in ("unknown", "unk"):
        return {"slug": slugify(m.group(1)), "confidence": 0.6, "source": "text", "needs_review": False}

    return {"slug": "geral", "confidence": 0.4, "source": "fallback", "needs_review": True}


def ingest_event(envelope: dict, *, client_event_id: str) -> dict:
    """Ingest idempotente de evento canônico. Retorna dict de resultado."""
    init_schema()
    con = get_conn()
    try:
        dup = con.execute(
            "SELECT 1 FROM prometheus_events_ingest WHERE client_event_id = ?", (client_event_id,)
        ).fetchone()
        if dup:
            return {"client_event_id": client_event_id, "duplicate": True}

        res = resolve_project(
            project_slug=envelope.get("project_slug"),
            cwd=envelope.get("cwd"),
            git_remote=envelope.get("git_remote"),
            agent_id=envelope.get("agent_id", ""),
            text=f"{envelope.get('title', '')} {envelope.get('summary', '')}",
        )
        slug = res["slug"]
        ev_id = uuid.uuid4().hex[:12]
        harness = envelope.get("harness", "")
        hs_id = envelope.get("harness_session_id", "")
        session_key = f"{harness}:{hs_id}" if harness and hs_id else ""
        now = now_iso()
        con.execute(
            """INSERT INTO prometheus_project_events
               (id, project_slug, session_key, harness, agent_id, event_type, title, summary, memory_id, status_hint, progress_delta, created_at)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?)""",
            (ev_id, slug, session_key, harness, envelope.get("agent_id", ""),
             envelope.get("event_type", "note"), envelope.get("title", ""),
             envelope.get("summary", ""), "", envelope.get("status_hint", ""),
             float(envelope.get("progress_delta", 0) or 0), now),
        )
        con.execute(
            "INSERT INTO prometheus_events_ingest (client_event_id, session_key, project_slug, memory_id) "
            "VALUES (?,?,?,?)",
            (client_event_id, session_key, slug, ""),
        )
        con.execute(
            """INSERT INTO prometheus_projects (slug, name, last_event_at) VALUES (?,?,?)
               ON CONFLICT(slug) DO UPDATE SET last_event_at = excluded.last_event_at""",
            (slug, envelope.get("name") or slug, now),
        )
        con.commit()
    finally:
        con.close()

    memory_id = ""
    if not res["needs_review"]:
        title = (envelope.get("title") or "").strip()
        summary = (envelope.get("summary") or "").strip()
        content = f"[{slug}] {envelope.get('event_type', 'note')} {title}" + (f": {summary}" if summary else "")
        try:
            from session_registry import remember_project
            memory_id = remember_project(slug, content, source=f"event:{envelope.get('event_type', 'note')}")
        except Exception:
            memory_id = ""

    if memory_id:
        con = get_conn()
        try:
            con.execute("UPDATE prometheus_events_ingest SET memory_id = ? WHERE client_event_id = ?",
                        (memory_id, client_event_id))
            con.execute("UPDATE prometheus_project_events SET memory_id = ? WHERE id = ?", (memory_id, ev_id))
            con.commit()
        finally:
            con.close()

    refresh_report(slug)
    return {"id": ev_id, "project_slug": slug, "confidence": res["confidence"],
            "needs_review": res["needs_review"], "memory_id": memory_id, "duplicate": False}


def refresh_report(slug: str) -> dict:
    """Materializa prometheus_project_reports (progresso heurístico v1)."""
    init_schema()
    con = get_conn()
    try:
        rows = con.execute(
            "SELECT event_type, status_hint, title FROM prometheus_project_events WHERE project_slug = ? "
            "ORDER BY created_at DESC, id DESC",
            (slug,),
        ).fetchall()
        done_w = total_w = 0.0
        open_issues = 0
        last_decision = last_implementation = ""
        for r in rows:
            w = WEIGHTS.get(r["event_type"], 1.0)
            if r["status_hint"] == "blocked":
                if r["event_type"] == "issue":
                    open_issues += 1
                continue
            total_w += w
            if r["status_hint"] in DONE_HINTS:
                done_w += w
            if r["event_type"] == "issue" and r["status_hint"] not in DONE_HINTS:
                open_issues += 1
            if r["event_type"] == "decision" and not last_decision:
                last_decision = r["title"] or ""
            if r["event_type"] == "implementation" and not last_implementation:
                last_implementation = r["title"] or ""
        progress = round(min(1.0, max(0.0, done_w / max(total_w, 1.0))) * 100, 1)
        active = con.execute(
            "SELECT COUNT(*) AS n FROM prometheus_sessions WHERE project_slug = ? AND status != 'closed'",
            (slug,),
        ).fetchone()["n"]
        summary = f"{len(rows)} eventos, {open_issues} issue(s) em aberto"
        now = now_iso()
        con.execute(
            """INSERT INTO prometheus_project_reports
               (project_slug, summary, progress, open_issues, last_decision, last_implementation, active_sessions, updated_at)
               VALUES (?,?,?,?,?,?,?,?)
               ON CONFLICT(project_slug) DO UPDATE SET
                 summary=excluded.summary, progress=excluded.progress, open_issues=excluded.open_issues,
                 last_decision=excluded.last_decision, last_implementation=excluded.last_implementation,
                 active_sessions=excluded.active_sessions, updated_at=excluded.updated_at""",
            (slug, summary, progress, open_issues, last_decision, last_implementation, active, now),
        )
        con.commit()
    finally:
        con.close()
    return {"project_slug": slug, "summary": summary, "progress": progress,
            "open_issues": open_issues, "last_decision": last_decision,
            "last_implementation": last_implementation, "active_sessions": active}


def list_events(slug: str, limit: int = 100) -> list:
    """Eventos do projeto, mais recentes primeiro (alimenta kanban/timeline da UI)."""
    init_schema()
    con = get_conn()
    try:
        rows = con.execute(
            "SELECT id, project_slug, session_key, harness, agent_id, event_type, title, summary, "
            "memory_id, status_hint, created_at FROM prometheus_project_events "
            "WHERE project_slug = ? ORDER BY created_at DESC, id DESC LIMIT ?",
            (slug, int(limit)),
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        con.close()


def get_report(slug: str) -> dict | None:
    init_schema()
    con = get_conn()
    try:
        row = con.execute(
            "SELECT project_slug, summary, progress, open_issues, last_decision, last_implementation, "
            "active_sessions, updated_at FROM prometheus_project_reports WHERE project_slug = ?",
            (slug,),
        ).fetchone()
        return dict(row) if row else None
    finally:
        con.close()


def list_projects() -> list:
    init_schema()
    con = get_conn()
    try:
        rows = con.execute(
            """SELECT p.slug, p.name, p.last_event_at, p.status,
                      COALESCE(r.progress, 0) AS progress,
                      COALESCE(r.active_sessions, 0) AS active_sessions
               FROM prometheus_projects p
               LEFT JOIN prometheus_project_reports r ON r.project_slug = p.slug
               ORDER BY COALESCE(p.last_event_at, '') DESC"""
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        con.close()
