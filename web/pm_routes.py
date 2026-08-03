#!/usr/bin/env python3
"""Blueprint /api/pm — sessões, eventos, projetos, presença (Fase A0)."""
from flask import Blueprint, jsonify, request

pm_bp = Blueprint("pm", __name__, url_prefix="/api/pm")


def _body() -> dict:
    return request.get_json(silent=True) or {}


@pm_bp.post("/sessions/start")
def sessions_start():
    b = _body()
    if not (b.get("harness") or "").strip() or not (b.get("harness_session_id") or "").strip():
        return jsonify({"error": "harness e harness_session_id obrigatorios"}), 400
    from session_registry import start_session
    try:
        return jsonify(start_session(b)), 201
    except Exception as e:
        return jsonify({"error": str(e)[:200]}), 500


@pm_bp.post("/sessions/heartbeat")
def sessions_heartbeat():
    b = _body()
    sk = (b.get("session_key") or "").strip()
    if not sk:
        return jsonify({"error": "session_key obrigatoria"}), 400
    from session_registry import heartbeat
    try:
        return jsonify(heartbeat(sk, current_action=b.get("current_action"), status=b.get("status")))
    except Exception as e:
        return jsonify({"error": str(e)[:200]}), 500


@pm_bp.post("/sessions/close")
def sessions_close():
    b = _body()
    sk = (b.get("session_key") or "").strip()
    if not sk:
        return jsonify({"error": "session_key obrigatoria"}), 400
    from session_registry import close_session
    try:
        return jsonify(close_session(sk))
    except Exception as e:
        return jsonify({"error": str(e)[:200]}), 500


@pm_bp.post("/events")
def pm_events():
    b = _body()
    cid = (b.get("client_event_id") or "").strip()
    if not cid:
        return jsonify({"error": "client_event_id obrigatorio (idempotencia)"}), 400
    if not (b.get("event_type") or "").strip() or not (b.get("title") or "").strip():
        return jsonify({"error": "event_type e title obrigatorios"}), 400
    from projects_registry import ingest_event
    try:
        res = ingest_event(b, client_event_id=cid)
        return jsonify(res), (200 if res.get("duplicate") else 201)
    except Exception as e:
        return jsonify({"error": str(e)[:200]}), 500


@pm_bp.get("/projects")
def pm_projects():
    from projects_registry import list_projects
    try:
        return jsonify({"projects": list_projects()})
    except Exception as e:
        return jsonify({"error": str(e)[:200], "projects": []})


@pm_bp.get("/projects/<slug>/report")
def pm_project_report(slug):
    from projects_registry import get_report
    try:
        rep = get_report(slug)
        if not rep:
            return jsonify({"error": "projeto sem relatorio"}), 404
        return jsonify(rep)
    except Exception as e:
        return jsonify({"error": str(e)[:200]}), 500


@pm_bp.get("/projects/<slug>/events")
def pm_project_events(slug):
    from projects_registry import list_events
    try:
        return jsonify({"events": list_events(slug, limit=int(request.args.get("limit", 100)))})
    except Exception as e:
        return jsonify({"error": str(e)[:200], "events": []})


@pm_bp.get("/projects/<slug>/connections")
def pm_connections_list(slug):
    from connections_registry import list_connections, alerts_for
    try:
        return jsonify({"connections": list_connections(slug), "alerts": alerts_for(slug)})
    except Exception as e:
        return jsonify({"error": str(e)[:200], "connections": [], "alerts": []})


@pm_bp.post("/projects/<slug>/connections/scan")
def pm_connections_scan(slug):
    from connections_registry import scan_project
    try:
        return jsonify(scan_project(slug))
    except Exception as e:
        return jsonify({"error": str(e)[:200]}), 500


@pm_bp.post("/connections")
def pm_connections_create():
    b = _body()
    slug = (b.get("project_slug") or "").strip()
    name = (b.get("name") or "").strip()
    if not slug or not name:
        return jsonify({"error": "project_slug e name obrigatorios"}), 400
    from connections_registry import add_connection
    from prometheus_db import get_conn
    con = get_conn()
    try:
        exists = con.execute("SELECT 1 FROM prometheus_projects WHERE slug = ?", (slug,)).fetchone()
    finally:
        con.close()
    if not exists:
        return jsonify({"error": "projeto inexistente — registre um evento primeiro"}), 400
    try:
        res = add_connection(slug, name=name, provider=b.get("provider", ""),
                             kind=b.get("kind", "api_key"), env_var=b.get("env_var", ""),
                             billing_type=b.get("billing_type", "unknown"),
                             cost_usd_month=b.get("cost_usd_month"),
                             expires_at=b.get("expires_at", ""), notes=b.get("notes", ""))
        return jsonify(res), 201
    except Exception as e:
        return jsonify({"error": str(e)[:200]}), 500


@pm_bp.put("/connections/<cid>")
def pm_connections_update(cid):
    from connections_registry import update_connection
    try:
        ok = update_connection(cid, _body())
        if not ok:
            return jsonify({"error": "nada a atualizar ou id inexistente"}), 404
        return jsonify({"id": cid, "updated": True})
    except Exception as e:
        return jsonify({"error": str(e)[:200]}), 500


@pm_bp.get("/connections/summary")
def pm_connections_summary():
    from connections_registry import summary
    try:
        return jsonify(summary())
    except Exception as e:
        return jsonify({"error": str(e)[:200]}), 500


@pm_bp.get("/projects/<slug>/stack")
def pm_stack_get(slug):
    from tech_profile import get_profile
    try:
        prof = get_profile(slug)
        if not prof:
            return jsonify({"error": "sem perfil ainda — POST /stack/scan para analisar"}), 404
        return jsonify(prof)
    except Exception as e:
        return jsonify({"error": str(e)[:200]}), 500


@pm_bp.post("/projects/<slug>/stack/scan")
def pm_stack_scan(slug):
    from tech_profile import scan_project
    try:
        return jsonify(scan_project(slug))
    except Exception as e:
        return jsonify({"error": str(e)[:200]}), 500


@pm_bp.get("/projects/<slug>/git")
def pm_git_get(slug):
    from tech_profile import get_profile
    try:
        prof = get_profile(slug)
        return jsonify({"git": (prof or {}).get("git", {"tracked": False})})
    except Exception as e:
        return jsonify({"error": str(e)[:200], "git": {"tracked": False}}), 500


@pm_bp.get("/projects/<slug>/runtime")
def pm_runtime_get(slug):
    from tech_profile import get_profile
    try:
        prof = get_profile(slug)
        if not prof:
            return jsonify({"error": "sem perfil ainda — POST /stack/scan"}), 404
        return jsonify({"containers": prof.get("containers", []), "git": prof.get("git", {})})
    except Exception as e:
        return jsonify({"error": str(e)[:200]}), 500


@pm_bp.post("/projects/<slug>/skills/suggest")
def pm_skills_suggest(slug):
    from skills_builder import suggest_skill
    try:
        skill = suggest_skill(slug)
        if not skill:
            return jsonify({"project_slug": slug, "suggested": False,
                            "reason": "sem padrão suficiente (3+ eventos com tema comum)"})
        return jsonify({**skill, "suggested": True})
    except Exception as e:
        return jsonify({"error": str(e)[:200]}), 500


@pm_bp.get("/projects/<slug>/skills")
def pm_skills_list(slug):
    from skills_builder import list_skills
    try:
        return jsonify({"skills": list_skills(slug)})
    except Exception as e:
        return jsonify({"error": str(e)[:200], "skills": []})


@pm_bp.post("/skills/<sid>/approve")
def pm_skills_approve(sid):
    from skills_builder import approve_skill
    try:
        res = approve_skill(sid)
        if not res:
            return jsonify({"error": "skill inexistente ou não está em draft"}), 404
        return jsonify(res)
    except Exception as e:
        return jsonify({"error": str(e)[:200]}), 500


@pm_bp.post("/skills/<sid>/mark-used")
def pm_skills_mark_used(sid):
    from skills_builder import mark_used
    try:
        res = mark_used(sid)
        if not res or not res.get("used"):
            return jsonify({"error": "skill inexistente"}), 404
        return jsonify(res)
    except Exception as e:
        return jsonify({"error": str(e)[:200]}), 500


@pm_bp.get("/skills/promotions")
def pm_skills_promotions():
    from skills_builder import promotion_candidates
    try:
        return jsonify({"candidates": promotion_candidates()})
    except Exception as e:
        return jsonify({"error": str(e)[:200], "candidates": []})


@pm_bp.get("/presence")
def pm_presence():
    project = request.args.get("project", "") or None
    from session_registry import presence
    try:
        return jsonify({"sessions": presence(project_slug=project)})
    except Exception as e:
        return jsonify({"error": str(e)[:200], "sessions": []})
