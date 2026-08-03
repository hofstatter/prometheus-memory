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


@pm_bp.get("/presence")
def pm_presence():
    project = request.args.get("project", "") or None
    from session_registry import presence
    try:
        return jsonify({"sessions": presence(project_slug=project)})
    except Exception as e:
        return jsonify({"error": str(e)[:200], "sessions": []})
