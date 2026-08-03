"""Testes Fase A0 — lanes, idempotência, presença, resolver, backward compat (T1-T7)."""
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "web"))

os.environ["PROMETHEUS_DB"] = "/tmp/test-lanes.db"
if os.path.exists("/tmp/test-lanes.db"):
    os.remove("/tmp/test-lanes.db")

import importlib
import prometheus_db
import projects_registry
import session_registry
import memory as memory_mod

prometheus_db.init_schema()


def _reload_all():
    """Reload p/ garantir env atual (roda junto com test_multiagent no mesmo processo)."""
    for mod in (prometheus_db, projects_registry, session_registry, memory_mod):
        importlib.reload(mod)
    prometheus_db.init_schema()


def _ingest(harness, hs_id, slug, event_type, title, cid, status_hint="done", agent_id="pedreiro"):
    return projects_registry.ingest_event(
        {"harness": harness, "harness_session_id": hs_id, "project_slug": slug,
         "agent_id": agent_id, "event_type": event_type, "title": title,
         "status_hint": status_hint},
        client_event_id=cid,
    )


def test_t1_isolation_two_sessions():
    _reload_all()
    _ingest("opencode", "a1", "evscar", "implementation", "fix frontend evscar", "a1:1")
    _ingest("opencode", "b2", "provador", "decision", "decisao provador", "b2:1")
    r_ev = [x.get("content", "") for x in session_registry.recall_lane("proj:evscar", "decisao provador", top_k=10)]
    assert not any("provador" in c for c in r_ev), "vazamento: evscar viu memoria do provador"
    r_pv = [x.get("content", "") for x in session_registry.recall_lane("proj:provador", "decisao provador", top_k=10)]
    assert any("provador" in c for c in r_pv)


def test_t2_shared_project_lane_different_harnesses():
    _reload_all()
    _ingest("opencode", "c3", "evscar", "research", "pesquisa OSM", "c3:1")
    _ingest("codex", "d4", "evscar", "implementation", "fix api backend", "d4:1")
    con = prometheus_db.get_conn()
    try:
        n = con.execute("SELECT COUNT(*) AS n FROM prometheus_project_events WHERE project_slug = 'evscar'").fetchone()["n"]
    finally:
        con.close()
    assert n >= 2, "eventos de harnesses diferentes no mesmo projeto nao conviveram"
    r = [x.get("content", "") for x in session_registry.recall_lane("proj:evscar", "backend api", top_k=10)]
    assert any("backend" in c for c in r)


def test_t3_idempotency():
    _reload_all()
    a = _ingest("opencode", "e5", "idemproj", "plan", "plano t3", "e5:1")
    b = _ingest("opencode", "e5", "idemproj", "plan", "plano t3", "e5:1")
    assert a["duplicate"] is False
    assert b["duplicate"] is True
    con = prometheus_db.get_conn()
    try:
        n_ev = con.execute("SELECT COUNT(*) AS n FROM prometheus_project_events WHERE project_slug = 'idemproj'").fetchone()["n"]
        n_in = con.execute("SELECT COUNT(*) AS n FROM prometheus_events_ingest WHERE client_event_id = 'e5:1'").fetchone()["n"]
    finally:
        con.close()
    assert n_ev == 1, "retry duplicou evento"
    assert n_in == 1, "retry duplicou ingest"


def test_t4_presence_stale_and_heartbeat():
    _reload_all()
    session_registry.start_session({"harness": "opencode", "harness_session_id": "p1",
                                    "project_slug": "evscar", "agent_id": "pedreiro"})
    con = prometheus_db.get_conn()
    try:
        con.execute("UPDATE prometheus_sessions SET last_seen_at = '2020-01-01T00:00:00' WHERE session_key = 'opencode:p1'")
        con.commit()
    finally:
        con.close()
    st = {r["session_key"]: r["status"] for r in session_registry.presence(project_slug="evscar")}
    assert st.get("opencode:p1") == "stale"
    session_registry.heartbeat("opencode:p1", current_action="debug")
    st = {r["session_key"]: r["status"] for r in session_registry.presence(project_slug="evscar")}
    assert st.get("opencode:p1") == "active"


def test_t4b_presence_idle_to_stale():
    """Edge case (revisão Inspetor): sessão idle via heartbeat também deve virar stale."""
    _reload_all()
    session_registry.start_session({"harness": "opencode", "harness_session_id": "p2",
                                    "project_slug": "evscar", "agent_id": "pedreiro"})
    session_registry.heartbeat("opencode:p2", status="idle")
    con = prometheus_db.get_conn()
    try:
        con.execute("UPDATE prometheus_sessions SET last_seen_at = '2020-01-01T00:00:00' WHERE session_key = 'opencode:p2'")
        con.commit()
    finally:
        con.close()
    st = {r["session_key"]: r["status"] for r in session_registry.presence(project_slug="evscar")}
    assert st.get("opencode:p2") == "stale"


def test_t5_resolver():
    _reload_all()
    assert projects_registry.resolve_project(cwd="/home/herbert/Projetos/evscar")["slug"] == "evscar"
    assert projects_registry.resolve_project(project_slug="Evscar!@")["slug"] == "evscar"
    assert projects_registry.resolve_project(project_slug="Evscar!@")["confidence"] == 1.0
    r = projects_registry.resolve_project(text="nenhum sinal de projeto aqui")
    assert r["slug"] == "geral" and r["needs_review"] is True
    r2 = projects_registry.resolve_project(cwd="/tmp/fora-de-projetos", git_remote="git@github.com:org/provador-digital.git")
    assert r2["slug"] == "provador-digital"


def test_t6_backward_compat():
    importlib.reload(memory_mod)
    mid = memory_mod.remember("segredo do atlas", agent_id="atlas", importance=0.9)
    assert mid
    r = [x.get("content", "") for x in memory_mod.recall("segredo", agent_id="atlas", top_k=10)]
    assert "segredo do atlas" in r


def test_t9_list_events():
    """list_events alimenta kanban/timeline: mais recente primeiro, com campos completos."""
    _reload_all()
    _ingest("opencode", "h9", "evscar", "plan", "plano antigo", "h9:1")
    _ingest("opencode", "h9", "evscar", "implementation", "impl nova", "h9:2")
    evs = projects_registry.list_events("evscar")
    assert len(evs) >= 2
    assert evs[0]["title"] == "impl nova", "esperado mais recente primeiro"
    for e in evs:
        assert "harness" in e and "status_hint" in e and "created_at" in e


def test_t7_report_progress():
    _reload_all()
    _ingest("opencode", "g7", "reportproj", "implementation", "impl 1", "g7:1")
    _ingest("opencode", "g7", "reportproj", "implementation", "impl 2", "g7:2")
    _ingest("opencode", "g7", "reportproj", "implementation", "impl 3", "g7:3")
    _ingest("opencode", "g7", "reportproj", "issue", "issue bloqueada", "g7:4", status_hint="blocked")
    rep = projects_registry.refresh_report("reportproj")
    assert rep["progress"] > 0
    assert rep["open_issues"] >= 1
