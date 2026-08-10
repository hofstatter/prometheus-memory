#!/usr/bin/env python3
"""
Prometheus Memory — Web UI Unificada
Timeline + Grafo + Canvas + Documents (RAG) + Notes + Editor
Configuração via variáveis de ambiente (ver .env.example).
"""
import os, sys, json, subprocess
from pathlib import Path
from datetime import datetime
from flask import Flask, render_template, jsonify, request

SRC_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SRC_DIR))

MNEMOSYNE_HOME = Path(os.environ.get("MNEMOSYNE_HOME", Path.home() / ".hermes" / "mnemosyne"))
MNEMOSYNE_DB = Path(os.environ.get("PROMETHEUS_DB", MNEMOSYNE_HOME / "data" / "mnemosyne.db"))
CANVAS_FILE = MNEMOSYNE_HOME / "canvas.mmd"
NOTES_DIR = Path(os.environ.get("PROMETHEUS_NOTES_DIR", Path.home() / "notes"))
PROMETHEUS_HOST = os.environ.get("PROMETHEUS_HOST", "127.0.0.1")
PROMETHEUS_PORT = int(os.environ.get("PROMETHEUS_PORT", "8777"))
EXCLUDED_CONTENT = [x.strip().lower() for x in os.environ.get("PROMETHEUS_EXCLUDE", "").split(",") if x.strip()]
KNOWN_PROJECTS = [x.strip() for x in os.environ.get("PROMETHEUS_PROJECTS", "").split(",") if x.strip()]
DEFAULT_PROJECT = os.environ.get("PROMETHEUS_PROJECT", "geral")

app = Flask(__name__, template_folder=str(SRC_DIR / "templates"), static_folder=str(SRC_DIR / "static"))
app.config["MAX_CONTENT_LENGTH"] = 50 * 1024 * 1024

from auth_guard import require_token_if_exposed, auth_bp

app.register_blueprint(auth_bp)


@app.after_request
def security_headers(resp):
    resp.headers["X-Content-Type-Options"] = "nosniff"
    resp.headers["X-Frame-Options"] = "DENY"
    resp.headers["Referrer-Policy"] = "no-referrer"
    resp.headers["Content-Security-Policy"] = "default-src 'self'; script-src 'self' 'unsafe-inline' https://cdn.tailwindcss.com https://cdn.jsdelivr.net https://unpkg.com; style-src 'self' 'unsafe-inline'; img-src 'self' data:"
    return resp


@app.before_request
def _auth_gate():
    if request.path == "/health":
        return None
    return require_token_if_exposed(lambda: None)()


def run_mnemosyne(*args, timeout=15):
    try:
        r = subprocess.run(["mnemosyne"] + list(args), capture_output=True, text=True, timeout=timeout)
        return r.stdout
    except subprocess.TimeoutExpired:
        return ""

def parse_mnemosyne_output(raw: str) -> list:
    items, cur = [], {}
    for line in raw.split("\n"):
        line = line.strip()
        if line.startswith("ID:"):
            if cur.get("content"):
                items.append(cur)
            cur = {"id": line.split(":")[1].strip()}
        elif cur and "ID:" not in line and "Content:" in line and "Error:" not in line:
            cur["content"] = line.split("Content:")[1].strip()
        elif cur and "Score:" in line:
            try:
                cur["score"] = float(line.split(":")[1].strip())
            except ValueError:
                cur["score"] = 0.0
    if cur.get("content"):
        items.append(cur)
    return items

def extract_project(content: str) -> str:
    import re
    m = re.findall(r'\[(\w+)\]', content)
    for x in m:
        if x.lower() not in ("unknown", "unk"):
            return x
    first = content.strip().split()[0] if content.strip() else ""
    for k in KNOWN_PROJECTS:
        if k.lower() == first.lower():
            return k
    for k in KNOWN_PROJECTS:
        if k.lower() in content.lower():
            return k
    return DEFAULT_PROJECT

# ─── Routes ────────────────────────────────────────

@app.route("/")
def index():
    resp = render_template("index.html")
    from flask import make_response
    r = make_response(resp)
    r.headers["Cache-Control"] = "no-store, must-revalidate"
    return r

@app.route("/health")
def health():
    checks = {}
    try:
        import sqlite3
        db = sqlite3.connect(str(MNEMOSYNE_DB), timeout=3)
        db.execute("SELECT 1")
        db.close()
        checks["db"] = True
    except Exception:
        checks["db"] = False
    try:
        from rag_engine import get_engine
        get_engine()
        checks["embeddings"] = True
    except Exception:
        checks["embeddings"] = False
    try:
        subprocess.run(["mnemosyne", "stats"], capture_output=True, timeout=3)
        checks["cli"] = True
    except Exception:
        checks["cli"] = False
    ok = all(checks.values())
    return jsonify({"status": "ok" if ok else "degraded", "checks": checks, "service": "prometheus-memory"}), 200 if ok else 503

# ─── API: Timeline ─────────────────────────────────

@app.route("/api/timeline")
def timeline():
    raw = run_mnemosyne("recall", "cena fato implementacao decisao correcao plano", "30")
    memories = parse_mnemosyne_output(raw)
    for m in memories:
        m["project"] = extract_project(m.get("content", ""))
    memories = [m for m in memories if not any(ex in m.get("content", "").lower() for ex in EXCLUDED_CONTENT)]
    for m in memories:
        m["content"] = _mask_sensitive(m.get("content") or "")
    return jsonify(memories)

# ─── API: Checkpoints (checkpoint automático de sessão) ──────────────

def _mask_sensitive(text: str) -> str:
    """Mascara credenciais na EXIBIÇÃO (banco fica intocado).

    PLAN_CHECKPOINT_MASK.md (10/08/2026). Substitui valores sensíveis por
    marcadores visíveis (ex.: ***(senha)***) para que o olho identifique
    facilmente que ali há uma credencial — sem expô-la.
    """
    import re as _re
    if not text:
        return text
    # 1. stdin quoted com sudo/pkexec:  pkexec ... <<< "SENHA" (aspas normais " ou escapadas \")
    text = _re.sub(r'<<<\s*\\"[^\\"]{1,120}\\"', '<<< \\"***(senha)***\\"', text)
    text = _re.sub(r'<<<\s*"[^"]{1,120}"', '<<< "***(senha)***"', text)
    # 2. password/passwd/senha = valor
    text = _re.sub(r'(?i)(password|passwd|senha)\s*=\s*\S+', r'\1=***(senha)***', text)
    # 3. api key
    text = _re.sub(r'(?i)(api[_-]?key)\s*=\s*\S+', r'\1=***(api_key)***', text)
    # 4. token (valor >= 12 chars)
    text = _re.sub(r'(?i)(token)\s*=\s*["\']?\S{12,}["\']?', r'\1=***(token)***', text)
    # 5. Authorization: Bearer X
    text = _re.sub(r'(?i)(authorization:\s*bearer\s+)\S+', r'\1***(bearer)***', text)
    return text


@app.route("/api/checkpoints")
def checkpoints():
    """Checkpoints automáticos de sessão (PLAN_CHECKPOINT_AUTO.md).

    Lê memórias do Mnemosyne com source='checkpoint' (briefings) e
    'checkpoint-verbatim' (prova literal), agrupadas por ciclo. A ordem é
    cronológica inversa (mais recente primeiro). Usa o índice idx_source.
    """
    import sqlite3
    from prometheus_db import DB_PATH
    try:
        limit = min(max(int(request.args.get("limit", 50)), 1), 200)
    except (TypeError, ValueError):
        limit = 50
    try:
        con = sqlite3.connect(str(DB_PATH), timeout=10)
        con.row_factory = sqlite3.Row
        rows = con.execute(
            "SELECT id, content, source, importance, created_at "
            "FROM memories WHERE source IN ('checkpoint','checkpoint-verbatim') "
            "ORDER BY created_at DESC LIMIT ?",
            (limit,),
        ).fetchall()
        con.close()
    except Exception as e:
        return jsonify({"error": str(e)[:200], "checkpoints": []}), 500
    items = [dict(r) for r in rows]
    for it in items:
        it["content"] = _mask_sensitive(it.get("content") or "")
    return jsonify({"checkpoints": items, "count": len(items)})

# ─── API: Graph ────────────────────────────────────

@app.route("/api/graph")
def graph():
    """Grafo real: graph_edges + triples + analytics (degree/PageRank).

    F1 · PLAN_SEMANTICA_GRAFO_F1 — delega ao graph_service (leitura SQLite
    read-only, Python puro). Params: ?limit= (10..500), ?entities=0/1.
    """
    from graph_service import fetch_graph
    try:
        limit = min(max(int(request.args.get("limit", 250)), 10), 500)
    except (TypeError, ValueError):
        limit = 250
    include_entities = request.args.get("entities", "1") != "0"
    try:
        return jsonify(fetch_graph(limit=limit, include_entities=include_entities))
    except Exception as e:
        return jsonify({"error": str(e)[:200], "nodes": [], "edges": [], "analytics": {}}), 500

# ─── API: Canvas ───────────────────────────────────

@app.route("/api/canvas")
def canvas():
    age = "atualizado agora"
    if CANVAS_FILE.exists():
        mmd = CANVAS_FILE.read_text()
        mtime = datetime.fromtimestamp(CANVAS_FILE.stat().st_mtime)
        diff = (datetime.now() - mtime).total_seconds()
        if diff < 60:
            age = f"atualizado agora"
        elif diff < 3600:
            age = f"atualizado há {int(diff/60)}min"
        else:
            age = f"atualizado há {int(diff/3600)}h"
    else:
        stats_raw = run_mnemosyne("stats")
        total = "0"
        for line in stats_raw.split("\n"):
            if "Total memories:" in line:
                total = line.split(":")[1].strip()
        mmd = f"stateDiagram-v2\n    [*] --> Mnemosyne\n    note right of Mnemosyne: {total} memorias\n    Mnemosyne --> [*]"
        age = "canvas ainda não gerado"
    _scripts_cand = [SRC_DIR / "scripts", SRC_DIR.parent / "scripts"]
    for _sc in _scripts_cand:
        if _sc.exists() and str(_sc) not in sys.path:
            sys.path.insert(0, str(_sc))
    from canvas_generator import mode_of
    return jsonify({"mermaid": mmd, "age": age, "mode": mode_of(mmd)})

@app.route("/api/canvas/projects")
def canvas_projects():
    from projects_registry import list_projects
    try:
        return jsonify({"projects": list_projects()})
    except Exception as e:
        return jsonify({"error": str(e)[:200], "projects": []})

# ─── API: Canvas node detail ──────────────────────

@app.route("/api/canvas/node/<node_id>")
def canvas_node(node_id):
    ref_path = MNEMOSYNE_HOME / "refs"
    if ref_path.exists():
        for date_dir in sorted(ref_path.glob("????-??-??"), reverse=True):
            for f in date_dir.glob(f"*_{node_id}.md"):
                return jsonify({"content": f.read_text()[:5000], "node_id": node_id})
    return jsonify({"content": f"Conteúdo offloaded não encontrado (node: {node_id})", "node_id": node_id})

# ─── API: Resource monitor (tempo real) ──────────────────────

@app.route("/api/stats/resources")
def stats_resources():
    import shutil
    out = {"gpu": None, "ram": None, "disk": None, "process_mb": None, "cpu": None}

    try:
        r = subprocess.run(
            ["nvidia-smi", "--query-gpu=utilization.gpu,memory.used,memory.total", "--format=csv,noheader,nounits"],
            capture_output=True, text=True, timeout=4)
        if r.returncode == 0:
            util, used, total = [float(x.strip()) for x in r.stdout.strip().splitlines()[0].split(",")]
            out["gpu"] = {"util": util, "used_mb": used, "total_mb": total, "pct": round(used * 100 / total, 1)}
    except Exception:
        pass

    try:
        meminfo = {}
        for line in open("/proc/meminfo"):
            k, v = line.split(":")
            meminfo[k] = int(v.strip().split()[0])
        total = meminfo["MemTotal"] / 1048576
        avail = meminfo.get("MemAvailable", 0) / 1048576
        used = total - avail
        out["ram"] = {"used_gb": round(used, 1), "total_gb": round(total, 1), "pct": round(used * 100 / total, 1)}
    except Exception:
        pass

    try:
        du = shutil.disk_usage(str(MNEMOSYNE_HOME))
        used_gb = du.used / 1e9
        out["disk"] = {"used_gb": round(used_gb, 1), "total_gb": round(du.total / 1e9, 1), "pct": round(du.used * 100 / du.total, 1)}
    except Exception:
        pass

    try:
        for line in open("/proc/self/status"):
            if line.startswith("VmRSS"):
                out["process_mb"] = round(int(line.split()[1]) / 1024, 1)
                break
    except Exception:
        pass

    # CPU%: psutil (se instalado) senão fallback manual com /proc/stat (2 leituras)
    try:
        import psutil
        out["cpu"] = {"pct": psutil.cpu_percent(interval=0.1)}
    except Exception:
        try:
            def _cpu_times():
                t = {}
                for line in open("/proc/stat"):
                    if line.startswith("cpu "):
                        vals = [int(x) for x in line.split()[1:]]
                        idle = vals[3] + (vals[4] if len(vals) > 4 else 0)
                        t = {"total": sum(vals), "idle": idle}
                        break
                return t
            a = _cpu_times()
            import time as _t
            _t.sleep(0.1)
            b = _cpu_times()
            dt = b["total"] - a["total"]
            di = b["idle"] - a["idle"]
            pct = round(100 * (1 - di / dt), 1) if dt > 0 else 0.0
            out["cpu"] = {"pct": pct}
        except Exception:
            pass

    return jsonify(out)


# ─── API: Context Briefing (inicio de sessao barato) ─────────

@app.route("/api/context/briefing")
def context_briefing():
    """Resumo comprimido (~500 tokens) p/ agente iniciar sessao com contexto maximo
    e custo minimo: persona L3 + cenas recentes + fatos recentes."""
    max_chars = int(request.args.get("max_chars", "2000"))
    sections = []

    persona_path = MNEMOSYNE_HOME / "persona.md"
    if persona_path.exists():
        sections.append("## Persona\n" + persona_path.read_text(errors="replace")[:800])

    raw = run_mnemosyne("recall", "cena", "5")
    cenas = [m["content"][:200] for m in parse_mnemosyne_output(raw) if m.get("content")]
    if cenas:
        sections.append("## Cenas recentes\n" + "\n".join(f"- {c}" for c in cenas[:5]))

    raw = run_mnemosyne("recall", "implementacao decisao correcao", "5")
    fatos = [m["content"][:160] for m in parse_mnemosyne_output(raw) if m.get("content")]
    if fatos:
        sections.append("## Fatos recentes\n" + "\n".join(f"- {f}" for f in fatos[:5]))

    briefing = "\n\n".join(sections)[:max_chars]
    est_tokens = len(briefing) // 4
    return jsonify({
        "briefing": briefing,
        "chars": len(briefing),
        "tokens_estimated": est_tokens,
        "usage": "Injete no system prompt no inicio da sessao do agente",
    })


# ─── API: Token Savings ──────────────────────────────────────

@app.route("/api/stats/savings")
def stats_savings():
    import sys as _sys
    for _cand in (str(SRC_DIR), str(SRC_DIR.parent / "scripts")):
        if _cand not in _sys.path:
            _sys.path.insert(0, _cand)
    try:
        from token_savings import compute_savings, offloaded_bytes
        recalls = 0
        try:
            import sqlite3 as _sq
            _con = _sq.connect(f"file:{MNEMOSYNE_DB}?mode=ro", uri=True)
            for _t in ("working_memory", "episodic_memory"):
                _cols = [c[1] for c in _con.execute(f"PRAGMA table_info({_t})").fetchall()]
                if "recall_count" in _cols:
                    recalls += _con.execute(f"SELECT COALESCE(SUM(recall_count),0) FROM {_t}").fetchone()[0]
            _con.close()
        except Exception:
            raw = run_mnemosyne("stats")
            import re as _re
            m = _re.search(r"recall_count\D*(\d+)", raw)
            if m:
                recalls = int(m.group(1))
        if not offloaded_bytes() and not recalls:
            return jsonify(compute_savings(0))
        return jsonify(compute_savings(recalls))
    except Exception as e:
        return jsonify({"error": "savings indisponivel", "detail": str(e)[:120]}), 500


# ─── API: Skill Registry (Camada 1) ────────────────

@app.route("/api/skills")
def skills_list():
    from skills_registry import list_skills
    return jsonify({"skills": list_skills()})


def _validate_skill_name(name: str) -> bool:
    """Slug validation: lowercase a-z, 0-9, hyphen and underscore."""
    import re as _re
    return bool(_re.match(r"^[a-z0-9_-]+$", name))


@app.route("/api/skills", methods=["POST"])
def skills_create():
    data = request.get_json() or {}
    name = (data.get("name") or "").strip().lower().replace(" ", "-")
    content = (data.get("content") or "").strip()
    if not name or not content:
        return jsonify({"error": "name e content obrigatorios"}), 400
    if not _validate_skill_name(name):
        return jsonify({"error": "name invalido: use apenas letras minusculas, numeros, hifen e underscore"}), 400
    from skills_registry import upsert_skill
    result = upsert_skill(name, content, data.get("description", ""), data.get("roles_json", "[]"))
    return jsonify(result), 201


@app.route("/api/skills/<name>")
def skills_get(name):
    from skills_registry import get_skill
    sk = get_skill(name)
    if not sk:
        return jsonify({"error": "skill nao encontrada"}), 404
    return jsonify(sk)


@app.route("/api/skills/<name>", methods=["PUT"])
def skills_update(name):
    data = request.get_json() or {}
    content = (data.get("content") or "").strip()
    if not content:
        return jsonify({"error": "content obrigatorio"}), 400
    if not _validate_skill_name(name):
        return jsonify({"error": "name invalido: use apenas letras minusculas, numeros, hifen e underscore"}), 400
    from skills_registry import upsert_skill
    result = upsert_skill(name, content, data.get("description", ""), data.get("roles_json", "[]"))
    return jsonify(result)


@app.route("/api/skills/<name>", methods=["DELETE"])
def skills_delete(name):
    from skills_registry import delete_skill
    if not delete_skill(name):
        return jsonify({"error": "skill nao encontrada"}), 404
    return "", 204


@app.route("/api/skills/<name>/raw")
def skills_raw(name):
    from skills_registry import get_skill
    sk = get_skill(name)
    if not sk:
        return jsonify({"error": "skill nao encontrada"}), 404
    from flask import Response
    return Response(sk["content"], mimetype="text/markdown")


# ─── API: Multi-agent Memory (v0.2) ───────────────

@app.route("/api/memory/remember", methods=["POST"])
def memory_remember():
    data = request.get_json() or {}
    content = (data.get("content") or "").strip()
    if not content:
        return jsonify({"error": "content vazio"}), 400
    agent_id = data.get("agent_id", "")
    source = data.get("source", "api")
    try:
        importance = float(data.get("importance", 0.5))
    except (TypeError, ValueError):
        importance = 0.5
    try:
        if data.get("infer"):
            from memory import remember_inferred
            project_slug = (data.get("project_slug") or "").strip()
            if project_slug:
                from projects_registry import slugify
                slug = slugify(project_slug)
                res = remember_inferred(content, channel=f"proj:{slug}", session=f"prom-proj-{slug}",
                                        source=source, importance=importance)
                res["project_slug"] = slug
                res["agent_id"] = agent_id or ""
            else:
                res = remember_inferred(content, agent_id=agent_id, source=source, importance=importance)
                res["agent_id"] = agent_id or ""
                res["project_slug"] = ""
            return jsonify({**res, "id": (res["ids"] or [""])[0]}), 201
        from memory import remember
        mid = remember(content, agent_id=agent_id, source=source, importance=importance)
        return jsonify({"id": mid, "stored": True, "agent_id": agent_id or "default"}), 201
    except Exception as e:
        return jsonify({"error": str(e)[:200]}), 500


@app.route("/api/memory/recall", methods=["POST"])
def memory_recall():
    data = request.get_json() or {}
    query = (data.get("query") or "").strip()
    if not query:
        return jsonify({"error": "query vazia"}), 400
    try:
        from memory import apply_threshold, recall
        try:
            top_k = int(data.get("top_k", 5))
        except (TypeError, ValueError):
            return jsonify({"error": "top_k deve ser inteiro"}), 400
        results = recall(query, agent_id=data.get("agent_id", ""), top_k=top_k)
        threshold = data.get("threshold")
        if threshold is not None:
            try:
                results = apply_threshold(results, float(threshold))
            except (TypeError, ValueError):
                pass
        try:
            from graph_service import degree_by_memory
            _degrees = degree_by_memory()
        except Exception:
            _degrees = {}
        for r in results:
            r["graph_degree"] = _degrees.get(str(r.get("id")), 0)
        return jsonify({"count": len(results), "agent_id": data.get("agent_id", "default"),
                        "results": [{"id": r.get("id"),
                                     "content": _mask_sensitive(r.get("content") or ""),
                                     "score": r.get("score"),
                                     "graph_degree": r.get("graph_degree", 0)} for r in results]})
    except Exception as e:
        return jsonify({"error": str(e)[:200]}), 500


@app.route("/api/agents")
def list_agents_memory():
    try:
        from memory import list_agents
        return jsonify({"agents": list_agents()})
    except Exception as e:
        return jsonify({"error": str(e)[:200], "agents": []})


# ─── API: Search ───────────────────────────────────

@app.route("/api/search")
def search():
    q = request.args.get("q", "")
    project = request.args.get("project", "")
    tier = request.args.get("tier", "")
    limit = int(request.args.get("limit", "50"))
    if not q:
        return jsonify([])
    args = ["recall", q, str(limit)]
    raw = run_mnemosyne(*args)
    results = parse_mnemosyne_output(raw)
    for r in results:
        r["project"] = extract_project(r.get("content", ""))
    for r in results:
        r["content"] = _mask_sensitive(r.get("content") or "")
    if project:
        results = [r for r in results if r["project"] == project]
    # Exclude Bytex_AgentOS memories (separate project, runs on VPS)
    results = [r for r in results if not any(ex in r.get("content", "").lower() for ex in EXCLUDED_CONTENT)]
    if tier:
        results = [r for r in results if tier.lower() in r.get("content", "").lower()]
    return jsonify(results[:limit])

# ─── API: Stats ────────────────────────────────────

@app.route("/api/stats")
def stats():
    raw = run_mnemosyne("stats")
    total = scenes = persona = 0
    for line in raw.split("\n"):
        if "Total memories:" in line:
            total = int(line.split(":")[1].strip())
        if "episodic memory:" in line and "total:" in line:
            scenes = int(line.split("total:")[1].strip()) if "total:" in line else 0
    if CANVAS_FILE.exists():
        persona = 1
    rag_docs = 0
    try:
        from rag_engine import get_engine
        rag_docs = get_engine().stats()["documents"]
    except Exception:
        pass
    return jsonify({
        "total_memories": total, "scenes": scenes, "persona": persona,
        "canvas": CANVAS_FILE.exists(),
        "rag_docs": rag_docs,
        "notes_count": len(list(NOTES_DIR.rglob("*.md"))) if NOTES_DIR.exists() else 0
    })

# ─── API: Projects ────────────────────────────────

@app.route("/api/projects")
def projects():
    query = " ".join(KNOWN_PROJECTS) if KNOWN_PROJECTS else "implementacao decisao config correcao plano"
    raw = run_mnemosyne("recall", query, "100")
    memories = parse_mnemosyne_output(raw)
    proj_set = set()
    for m in memories:
        content_lower = m.get("content", "").lower()
        if any(ex in content_lower for ex in EXCLUDED_CONTENT):
            continue
        proj_set.add(extract_project(m.get("content", "")))
    return jsonify(sorted(proj_set))

# ─── API: Memory detail ────────────────────────────

@app.route("/api/memory/<mem_id>")
def memory_detail(mem_id):
    import sqlite3
    db = sqlite3.connect(str(MNEMOSYNE_DB), timeout=10)
    try:
        db.execute("PRAGMA busy_timeout=5000")
        row = db.execute(
            "SELECT id, content, importance FROM memories WHERE id = ?", (mem_id,)
        ).fetchone()
    finally:
        db.close()
    if not row:
        return jsonify({"error": "not found"}), 404
    content = row[1] or ""
    return jsonify({
        "id": row[0],
        "content": _mask_sensitive(content),
        "importance": str(row[2] if row[2] is not None else 0.5),
        "project": extract_project(content),
    })

# ─── RAG, Notes, Editor blueprints ─────────────────

_path = str(Path(__file__).resolve().parent)
if _path not in sys.path:
    sys.path.insert(0, _path)

try:
    from rag_routes import rag_bp
    app.register_blueprint(rag_bp)
    print("[Prometheus] RAG blueprint registrado", flush=True)
except Exception as e:
    print(f"[Prometheus] RAG blueprint não registrado: {e}", flush=True)

try:
    from notes_routes import notes_bp
    app.register_blueprint(notes_bp)
    print("[Prometheus] Notes blueprint registrado", flush=True)
except Exception as e:
    print(f"[Prometheus] Notes blueprint não registrado: {e}", flush=True)

try:
    from editor_routes import editor_bp
    app.register_blueprint(editor_bp)
    print("[Prometheus] Editor blueprint registrado", flush=True)
except Exception as e:
    print(f"[Prometheus] Editor blueprint não registrado: {e}", flush=True)

try:
    from pm_routes import pm_bp
    app.register_blueprint(pm_bp)
    print("[Prometheus] PM blueprint registrado", flush=True)
except Exception as e:
    print(f"[Prometheus] PM blueprint não registrado: {e}", flush=True)

# ─── Main ──────────────────────────────────────────

if __name__ == "__main__":
    app.run(host=PROMETHEUS_HOST, port=PROMETHEUS_PORT, debug=False)
