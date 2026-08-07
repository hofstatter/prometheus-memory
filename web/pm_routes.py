#!/usr/bin/env python3
"""Blueprint /api/pm — sessões, eventos, projetos, presença (Fase A0)."""
from flask import Blueprint, jsonify, request
from pathlib import Path

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


@pm_bp.get("/projects/<slug>/tasks")
def pm_project_tasks(slug):
    """Tasks do kanban (prometheus_project_tasks) com persona/timestamp do evento-fonte."""
    from prometheus_db import get_conn
    try:
        con = get_conn()
        try:
            rows = con.execute(
                "SELECT t.id, t.title, t.status, t.updated_at, "
                "       e.agent_id, e.event_type, e.created_at AS event_created_at "
                "FROM prometheus_project_tasks t "
                "LEFT JOIN prometheus_project_events e ON e.id = t.source_event_id "
                "WHERE t.project_slug = ? ORDER BY t.updated_at DESC LIMIT 200",
                (slug,),
            ).fetchall()
            tasks = [dict(r) for r in rows]
            # fallback: eventos sem task derivada, agrupados por status_hint
            if not tasks:
                evs = con.execute(
                    "SELECT id, agent_id, event_type, title, status_hint, created_at "
                    "FROM prometheus_project_events WHERE project_slug = ? "
                    "ORDER BY created_at DESC LIMIT 100",
                    (slug,),
                ).fetchall()
                tasks = [dict(r) for r in evs]
            return jsonify({"tasks": tasks})
        finally:
            con.close()
    except Exception as e:
        return jsonify({"error": str(e)[:200], "tasks": []}), 500


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


@pm_bp.get("/projects/<slug>/notes")
def pm_project_notes(slug):
    """Notas do projeto (P5.5) — agrupa ~/notes/*.md por subpasta/conteúdo e filtra pelo slug."""
    notes_dir = Path(__import__("os").environ.get(
        "PROMETHEUS_NOTES_DIR", str(Path.home() / "notes")))
    if not notes_dir.exists():
        return jsonify({"notes": [], "groups": []})
    from prometheus_db import get_conn
    try:
        con = get_conn()
        try:
            row = con.execute(
                "SELECT name FROM prometheus_projects WHERE slug = ?", (slug,)
            ).fetchone()
        finally:
            con.close()
    except Exception:
        row = None
    pname = (row[0] if row else slug).lower()
    notes = []
    for f in notes_dir.rglob("*.md"):
        st = f.stat()
        rel = f.relative_to(notes_dir)
        group = str(rel.parent) if str(rel.parent) != "." else "geral"
        try:
            head = f.read_text(encoding="utf-8", errors="replace")[:600].lower()
        except OSError:
            continue
        if slug.lower() not in head and pname not in head:
            continue
        notes.append({
            "id": rel.as_posix(),
            "name": f.stem,
            "group": group,
            "size": st.st_size,
            "modified": __import__("datetime").datetime.fromtimestamp(
                st.st_mtime).isoformat(),
        })
    notes.sort(key=lambda x: x["modified"], reverse=True)
    groups = {}
    for n in notes:
        groups.setdefault(n["group"], []).append(n)
    return jsonify({"notes": notes, "groups": groups, "total": len(notes)})


@pm_bp.get("/projects/<slug>/tokens")
def pm_project_tokens(slug):
    """Estimativa de tokens por projeto (P5.5) — fatia do total global proporcional aos eventos."""
    from token_savings import compute_savings
    from prometheus_db import get_conn
    try:
        savings = compute_savings()
    except Exception as e:
        savings = {"total_tokens_saved": 0, "offload_tokens_saved": 0,
                   "compression_tokens_saved": 0, "offloaded_bytes": 0}
    try:
        con = get_conn()
        try:
            tot = con.execute(
                "SELECT COUNT(*) AS n FROM prometheus_project_events"
            ).fetchone()["n"] or 0
            mine = con.execute(
                "SELECT COUNT(*) AS n FROM prometheus_project_events WHERE project_slug = ?",
                (slug,),
            ).fetchone()["n"] or 0
        finally:
            con.close()
    except Exception:
        tot, mine = 0, 0
    share = (mine / tot) if tot else 0.0
    total = savings.get("total_tokens_saved", 0)
    return jsonify({
        "project_slug": slug,
        "events_share_pct": round(share * 100, 1),
        "estimated_tokens_saved": int(total * share),
        "global_tokens_saved": int(total),
        "offload_tokens_saved": int(savings.get("offload_tokens_saved", 0) * share),
        "compression_tokens_saved": int(savings.get("compression_tokens_saved", 0) * share),
        "note": "Estimativa proporcional aos eventos do projeto sobre o total global",
    })


@pm_bp.get("/projects/<slug>/mcps")
def pm_project_mcps(slug):
    """MCPs do projeto (P5.5) — detecta opencode.jsonc (bloco mcp) e docker-compose services."""
    from prometheus_db import get_conn
    import json as _json
    try:
        con = get_conn()
        try:
            row = con.execute(
                "SELECT repo_path FROM prometheus_projects WHERE slug = ?", (slug,)
            ).fetchone()
        finally:
            con.close()
    except Exception:
        row = None
    rp = (row[0] if row else None) or ""
    mcps = []
    docker = []
    if rp:
        root = Path(rp)
        for cfg_name in ("opencode.jsonc", "opencode.json", ".opencode/opencode.jsonc"):
            cfg = root / cfg_name
            if cfg.exists():
                try:
                    txt = cfg.read_text()
                    txt = _json.loads(txt) if cfg_name.endswith(".json") else txt
                    import re as _re
                    # jsonc -> json: remove comentários // e /* */ SEM quebrar "https://"
                    def _no_comment(m):
                        return m.group(1)
                    txt = _re.sub(r'("(?:[^"\\]|\\.)*")|//[^\n]*|/\*.*?\*/', _no_comment, txt, flags=_re.DOTALL)
                    data = _json.loads(txt)
                    mcp_block = data.get("mcp") or {}
                    for name, conf in mcp_block.items():
                        mcps.append({
                            "name": name,
                            "type": (conf or {}).get("type", "local"),
                            "source": cfg_name,
                        })
                except Exception:
                    pass
        for dc_name in ("docker-compose.yml", "docker-compose.yaml", "compose.yaml", "compose.yml"):
            dc = root / dc_name
            if dc.exists():
                try:
                    txt = dc.read_text()
                    svc = []
                    in_services = False
                    lines = txt.splitlines()
                    for i, line in enumerate(lines):
                        raw = line
                        stripped = raw.strip()
                        if not stripped or stripped.startswith("#"):
                            continue
                        indent = len(raw) - len(raw.lstrip(" "))
                        if stripped == "services:":
                            in_services = True
                            continue
                        if in_services and indent == 2 and stripped.endswith(":"):
                            nm = stripped.rstrip(":")
                            # valida: é serviço se a linha seguinte (indent 4) tem image:/build:/container_name:
                            nxt = lines[i + 1].strip() if i + 1 < len(lines) else ""
                            if nm and " " not in nm and "{" not in nm and (
                                nxt.startswith(("image:", "build:", "container_name:", "extends:"))
                            ):
                                svc.append(nm)
                    docker = svc
                except OSError:
                    pass
                break
    return jsonify({"mcps": mcps, "docker_services": docker, "repo_path": rp})


@pm_bp.get("/projects/<slug>/git/log")
def pm_git_log(slug):
    """Histórico git real do projeto (P5.4) — últimos N commits com hash, msg, autor, data.

    Usa repo_path de prometheus_projects; roda `git log` read-only.
    """
    try:
        n = int(request.args.get("n", 20))
    except (TypeError, ValueError):
        n = 20
    n = max(1, min(n, 100))
    from prometheus_db import get_conn
    try:
        con = get_conn()
        try:
            row = con.execute(
                "SELECT repo_path FROM prometheus_projects WHERE slug = ?",
                (slug,),
            ).fetchone()
        finally:
            con.close()
    except Exception:
        row = None
    rp = (row[0] if row else None) or ""
    if not rp or not Path(rp).joinpath(".git").exists():
        return jsonify({"tracked": False, "commits": [], "repo_path": rp})
    import subprocess
    try:
        out = subprocess.run(
            ["git", "-C", rp, "log", "--pretty=%H%x1e%h%x1e%an%x1e%ae%x1e%ad%x1e%s", "--date=iso",
             "-n", str(n)],
            capture_output=True, text=True, timeout=15,
        ).stdout
    except (subprocess.SubprocessError, OSError) as e:
        return jsonify({"tracked": True, "error": str(e)[:200], "commits": []})
    commits = []
    for line in out.split("\n"):
        line = line.strip()
        if not line:
            continue
        parts = line.split("\x1e", 5)
        if len(parts) < 6:
            continue
        commits.append({
            "sha": parts[0], "short": parts[1], "author": parts[2],
            "email": parts[3], "date": parts[4].replace(" ", "T"), "message": parts[5],
        })
    return jsonify({"tracked": True, "commits": commits, "repo_path": rp})


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


@pm_bp.get("/entities/<name>/memories")
def pm_entities_memories(name):
    from entity_store import memories_for
    try:
        return jsonify({"entity": name, "memory_ids": memories_for(name)})
    except Exception as e:
        return jsonify({"error": str(e)[:200], "memory_ids": []})


@pm_bp.get("/entities")
def pm_entities_list():
    from entity_store import list_entities
    try:
        return jsonify({"entities": list_entities(limit=int(request.args.get("limit", 100)))})
    except Exception as e:
        return jsonify({"error": str(e)[:200], "entities": []})


@pm_bp.get("/presence")
def pm_presence():
    project = request.args.get("project", "") or None
    from session_registry import presence
    try:
        return jsonify({"sessions": presence(project_slug=project)})
    except Exception as e:
        return jsonify({"error": str(e)[:200], "sessions": []})


@pm_bp.get("/analytics/personas")
def pm_analytics_personas():
    """Relatório por persona (P5.3) — counts por persona × event_type, %, lista detalhada.

    window: horas (default 24). Extensível: persona = agent_id, sem hardcode.
    Eventos 'work' de sessões são classificados pelo papel da persona
    (arquiteto→planning, pedreiro→implementation, inspector/visionario→review).
    """
    try:
        window = int(request.args.get("window", 24))
    except (TypeError, ValueError):
        window = 24
    window = max(1, min(window, 24 * 30))
    project = request.args.get("project", "") or None
    PERSONA_ROLE = {
        "arquiteto": "planning",
        "pedreiro": "implementation",
        "inspector": "review",
        "visionario": "review",
    }
    from prometheus_db import get_conn
    try:
        con = get_conn()
        try:
            where = "created_at >= datetime('now', ?)"
            params = [f"-{window} hours"]
            if project:
                where += " AND project_slug = ?"
                params.append(project)
            rows = con.execute(
                f"SELECT agent_id, event_type, COUNT(*) AS n, "
                f"MAX(created_at) AS last_ts "
                f"FROM prometheus_project_events WHERE {where} "
                f"GROUP BY agent_id, event_type ORDER BY n DESC",
                params,
            ).fetchall()
            # agrega por persona, classificando 'work' pelo papel da persona
            personas = {}
            total = 0
            for r in rows:
                pid = r["agent_id"] or "unknown"
                etype = r["event_type"]
                if etype == "work" and pid in PERSONA_ROLE:
                    etype = PERSONA_ROLE[pid]
                p = personas.setdefault(pid, {"persona": pid, "counts": {}, "total": 0, "last_ts": None})
                p["counts"][etype] = p["counts"].get(etype, 0) + r["n"]
                p["total"] += r["n"]
                p["last_ts"] = max(p["last_ts"], r["last_ts"]) if p["last_ts"] else r["last_ts"]
                total += r["n"]
            for p in personas.values():
                p["pct"] = round(100 * p["total"] / total, 1) if total else 0.0
            # lista detalhada (itens por persona, limitada)
            detail_rows = con.execute(
                f"SELECT agent_id, event_type, title, created_at "
                f"FROM prometheus_project_events WHERE {where} "
                f"ORDER BY created_at DESC LIMIT 60",
                params,
            ).fetchall()
            detail = []
            for r in detail_rows:
                etype = r["event_type"]
                if etype == "work" and (r["agent_id"] or "") in PERSONA_ROLE:
                    etype = PERSONA_ROLE[r["agent_id"]]
                detail.append({
                    "persona": r["agent_id"] or "unknown", "event_type": etype,
                    "title": r["title"], "created_at": r["created_at"],
                })
            return jsonify({
                "window_hours": window,
                "total_events": total,
                "personas": list(personas.values()),
                "detail": detail,
            })
        finally:
            con.close()
    except Exception as e:
        return jsonify({"error": str(e)[:200], "personas": [], "detail": [], "total_events": 0})


@pm_bp.get("/analytics/daily")
def pm_analytics_daily():
    """Relatório diário por persona (P5.7) — gera para o dia se ainda não existe; consulta histórico."""
    day = request.args.get("day", "")
    from prometheus_db import get_conn
    import json as _json
    try:
        con = get_conn()
        try:
            if not day:
                # dia de hoje (o coletor gera o relatório ao cruzar 00:00 via last_report_day)
                try:
                    from telemetry_collector import _daily_report_date
                    day = _daily_report_date()
                except Exception:
                    from datetime import datetime as _dt
                    day = _dt.now().strftime("%Y-%m-%d")
            row = con.execute(
                "SELECT data_json FROM prometheus_reports_daily WHERE day = ?", (day,)
            ).fetchone()
            if row:
                return jsonify(_json.loads(row["data_json"]))
            return jsonify({"day": day, "total_events": 0, "personas": [], "detail": [],
                            "note": "sem relatório gerado ainda — o coletor gera ao cruzar 00:00 (ou no próximo ciclo)"})
        finally:
            con.close()
    except Exception as e:
        return jsonify({"error": str(e)[:200], "personas": [], "detail": [], "total_events": 0})
