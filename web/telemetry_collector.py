#!/usr/bin/env python3
"""Prometheus Memory — Coletor de Telemetria (P5.1 · PLAN_P5_PROJETOS_VIVO.md).

Roda via systemd user timer (a cada 5 min) e escreve no MESMO prometheus_db da
UI: sessions, events e tasks com atribuicao de persona. Fontes de verdade
MECANICAS (nao depende de agente chamar API):

  1. ~/.config/opencode/workflow-state.json  -> history[] com stage/model/handoff/ts
  2. ~/.local/share/opencode/opencode.db     -> sessions/messages/todos (timestamps reais)
  3. git log dos repos registrados em prometheus_projects.repo_path

Idempotente: client_event_id = sha1(fonte:identificador). Incremental via
last_collect_ts em prometheus_meta.
"""
import hashlib
import json
import sqlite3
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

# ---------- paths ----------
HOME = Path.home()
WORKFLOW_STATE = Path.home() / ".config" / "opencode" / "workflow-state.json"
OPENCODE_DB = Path.home() / ".local" / "share" / "opencode" / "opencode.db"
MNEMOSYNE_HOME = Path.home() / ".hermes" / "mnemosyne"
# Mesmo resolucao do prometheus_db.py (PROMETHEUS_DB env > MNEMOSYNE_HOME/data/mnemosyne.db)
DB_PATH = Path(__import__("os").environ.get("PROMETHEUS_DB", MNEMOSYNE_HOME / "data" / "mnemosyne.db"))

PERSONA_BY_MODEL = {
    "kimi-for-coding/k3": "arquiteto",
    "deepseek/deepseek-v4-flash": "pedreiro",
    "deepseek/deepseek-v4-pro": "inspector",
    "zai-coding-plan/glm-4.5v": "visionario",
    "zai-coding-plan/glm-5.2": "arquiteto",
}
EVENT_TYPE_BY_STAGE = {
    "arquiteto": "planning",
    "pedreiro": "implementation",
    "inspector": "review",
    "visionario": "review",
}
STAGE_ALIASES = {"builder": "pedreiro", "inspetor": "inspector"}


def _sha1(*parts) -> str:
    h = hashlib.sha1()
    for p in parts:
        h.update(str(p).encode("utf-8", "replace"))
    return h.hexdigest()[:20]


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _connect() -> sqlite3.Connection:
    con = sqlite3.connect(str(DB_PATH), timeout=10)
    con.row_factory = sqlite3.Row
    return con


def _ensure_meta(con: sqlite3.Connection) -> None:
    con.execute(
        "CREATE TABLE IF NOT EXISTS prometheus_meta (key TEXT PRIMARY KEY, value TEXT)"
    )


def _get_meta(con: sqlite3.Connection, key: str, default: str = "0") -> str:
    row = con.execute(
        "SELECT value FROM prometheus_meta WHERE key=?", (key,)
    ).fetchone()
    return row["value"] if row else default


def _set_meta(con: sqlite3.Connection, key: str, value: str) -> None:
    con.execute(
        "INSERT INTO prometheus_meta(key,value) VALUES(?,?) "
        "ON CONFLICT(key) DO UPDATE SET value=excluded.value",
        (key, value),
    )


def _persona_from_model(model: str) -> str:
    if not model:
        return "unknown"
    for pat, persona in PERSONA_BY_MODEL.items():
        if pat in model:
            return persona
    return model.split("/")[-1]  # nova persona = slug do modelo (extensivel)


def _project_for_path(con: sqlite3.Connection, path: str) -> str | None:
    """Resolve o slug do projeto por prefixo de caminho."""
    if not path:
        return None
    path = str(Path(path).resolve())
    best, best_slug = 0, None
    for r in con.execute(
        "SELECT slug, repo_path, name FROM prometheus_projects WHERE status='active'"
    ).fetchall():
        rp = (r["repo_path"] or "").strip()
        if rp and path.startswith(str(Path(rp).resolve())):
            if len(rp) > best:
                best, best_slug = len(rp), r["slug"]
    return best_slug


# ---------- 1. workflow-state.json ----------
def ingest_workflow(con: sqlite3.Connection) -> int:
    if not WORKFLOW_STATE.exists():
        return 0
    try:
        wf = json.loads(WORKFLOW_STATE.read_text())
    except Exception:
        return 0
    hist = wf.get("history") or []
    last_ts = _get_meta(con, "last_workflow_ts")
    n = 0
    for item in hist:
        ts = item.get("ts") or ""
        if not ts or (last_ts and ts <= last_ts):
            continue
        stage = str(item.get("stage") or "").strip().lower()
        stage = STAGE_ALIASES.get(stage, stage)
        model = item.get("model") or ""
        persona = _persona_from_model(model)
        if stage and stage not in ("arquiteto", "pedreiro", "inspector", "visionario"):
            persona = stage
        handoff = str(item.get("handoff") or "").strip()
        title = handoff.splitlines()[0][:140] if handoff else f"{persona}: handoff"
        cid = _sha1("workflow", item.get("ts"), stage)
        # projeto: resolve por menção do slug (ou nomes conhecidos) no handoff/title
        pslug = None
        for r2 in con.execute("SELECT slug, name FROM prometheus_projects WHERE status='active'").fetchall():
            if r2["slug"] in handoff or r2["name"].lower() in handoff.lower():
                pslug = r2["slug"]
                break
        # sessao: upsert por (harness=opencode, session_key derivada do ts)
        sk = f"wf-{_sha1(item.get('ts'), stage)}"
        con.execute(
            "INSERT INTO prometheus_sessions(session_key,harness,harness_session_id,"
            "project_slug,agent_id,cwd,current_action,started_at,last_seen_at,status) "
            "VALUES(?,?,?,?,?,?,?,?,?,?) "
            "ON CONFLICT(session_key) DO UPDATE SET last_seen_at=excluded.last_seen_at,"
            "current_action=excluded.current_action,status='active'",
            (sk, "opencode", sk, pslug, persona, None, title[:200], ts, _now_iso(), "active"),
        )
        con.execute(
            "INSERT OR IGNORE INTO prometheus_project_events(id,project_slug,session_key,"
            "harness,agent_id,event_type,title,summary,created_at) "
            "VALUES(?,?,?,?,?,?,?,?,?)",
            (cid, pslug, sk, "opencode", persona, EVENT_TYPE_BY_STAGE.get(persona, "work"),
             title, handoff[:4000], ts),
        )
        if pslug:
            con.execute(
                "UPDATE prometheus_projects SET last_event_at=? WHERE slug=?",
                (ts, pslug),
            )
        n += 1
    _set_meta(con, "last_workflow_ts", max((h.get("ts") or "") for h in hist) or _now_iso())
    return n


# ---------- 2. opencode.db (sessions/todos) ----------
def ingest_opencode(con: sqlite3.Connection) -> int:
    if not OPENCODE_DB.exists():
        return 0
    try:
        src = sqlite3.connect(f"file:{OPENCODE_DB}?mode=ro", uri=True)
    except Exception:
        return 0
    src.row_factory = sqlite3.Row
    last = _get_meta(con, "last_opencode_ts", "1970-01-01")
    n = 0
    try:
        rows = src.execute(
            "SELECT id, project_id, title, directory, path, time_created "
            "FROM session ORDER BY time_created DESC LIMIT 200"
        ).fetchall()
    except Exception:
        rows = []
    last_f = 0.0
    try:
        last_f = float(last)
    except ValueError:
        last_f = 0.0
    for r in rows:
        ts = r["time_created"] or 0
        ts_f = float(ts)
        if ts_f <= last_f:
            continue
        persona = "opencode"
        # modelo da primeira mensagem
        try:
            m = src.execute(
                "SELECT data FROM message WHERE session_id=? ORDER BY time_created LIMIT 1",
                (r["id"],),
            ).fetchone()
            if m and m["data"]:
                d = json.loads(m["data"]) if isinstance(m["data"], str) else m["data"]
                model = (d.get("model") or "").split("/")[-1] if isinstance(d, dict) else ""
                if model:
                    persona = _persona_from_model(model)
        except Exception:
            pass
        cid = _sha1("opencode-session", r["id"])
        title = (r["title"] or f"sessão {r['id'][:6]}")[:140]
        try:
            ts_iso = datetime.fromtimestamp(ts_f, tz=timezone.utc).isoformat(
                timespec="seconds"
            )
        except (OverflowError, ValueError, OSError):
            ts_iso = _now_iso()
        con.execute(
            "INSERT OR IGNORE INTO prometheus_project_events(id,project_slug,session_key,"
            "harness,agent_id,event_type,title,summary,created_at) "
            "VALUES(?,?,?,?,?,?,?,?,?)",
            (cid, _project_for_path(con, r["directory"]), r["id"], "opencode", persona,
             "work", title, f"session {r['id'][:8]} · {Path(r['path']).name if r['path'] else ''}", ts_iso),
        )
        pslug2 = _project_for_path(con, r["directory"])
        if pslug2:
            con.execute(
                "UPDATE prometheus_projects SET last_event_at=? WHERE slug=?",
                (ts_iso, pslug2),
            )
        n += 1
    src.close()
    if rows:
        _set_meta(con, "last_opencode_ts", str(max(float(r["time_created"]) for r in rows)))
    return n


# ---------- 3. git log ----------
def ingest_git(con: sqlite3.Connection) -> int:
    import subprocess
    n = 0
    for r in con.execute(
        "SELECT slug, repo_path FROM prometheus_projects WHERE repo_path IS NOT NULL"
    ).fetchall():
        rp = r["repo_path"]
        if not Path(rp).joinpath(".git").exists():
            continue
        last = _get_meta(con, f"git:{r['slug']}", "0000-00-00")
        try:
            out = subprocess.run(
                ["git", "-C", rp, "log", "--pretty=%H|%an|%ae|%ad|%s", "--date=iso",
                 "-n", "50"],
                capture_output=True, text=True, timeout=15,
            ).stdout
        except Exception:
            continue
        for line in out.splitlines():
            parts = line.split("|", 4)
            if len(parts) < 5:
                continue
            sha, author, email, date, msg = parts[0], parts[1], parts[2], parts[3], parts[4]
            ds = date.split(" ")[0]
            if ds <= last:
                continue
            typ = "implementation"
            ml = msg.lower()
            if ml.startswith(("feat", "add", "create", "nova", "novo", "adiciona")):
                typ = "implementation"
            elif ml.startswith(("fix", "corrige", "ajusta")):
                typ = "fix"
            elif ml.startswith(("docs", "doc:", "chore", "refactor")):
                typ = "docs"
            cid = _sha1("git", r["slug"], sha)
            con.execute(
                "INSERT OR IGNORE INTO prometheus_project_events(id,project_slug,session_key,"
                "harness,agent_id,event_type,title,summary,created_at) "
                "VALUES(?,?,?,?,?,?,?,?,?)",
                (cid, r["slug"], None, "git", author, typ, msg[:140],
                 f"{sha[:9]} · {author} <{email}>", date.replace(" ", "T")),
            )
            n += 1
        if out:
            newest = "0000-00-00"
            for line in out.splitlines():
                p = line.split("|", 4)
                if len(p) >= 5:
                    d0 = p[3].split(" ")[0]
                    if d0 > newest:
                        newest = d0
            _set_meta(con, f"git:{r['slug']}", newest)
    return n


# ---------- tasks (kanban) ----------
def sync_tasks(con: sqlite3.Connection) -> int:
    """Tasks do kanban a partir dos eventos recentes por projeto."""
    n = 0
    for r in con.execute(
        "SELECT project_slug, agent_id, event_type, title, MAX(created_at) AS ts "
        "FROM prometheus_project_events WHERE project_slug IS NOT NULL "
        "GROUP BY project_slug, title"
    ).fetchall():
        if not r["project_slug"]:
            continue
        status = "done" if r["event_type"] in ("review", "docs", "fix") else (
            "doing" if r["event_type"] in ("implementation", "work") else "todo"
        )
        tid = _sha1("task", r["project_slug"], r["title"])
        con.execute(
            "INSERT OR IGNORE INTO prometheus_project_tasks(id,project_slug,title,status,"
            "source_event_id,confidence,updated_at) VALUES(?,?,?,?,?,?,?)",
            (tid, r["project_slug"], r["title"][:200], status, None, 0.7, r["ts"]),
        )
        n += 1
    return n


def run() -> None:
    con = _connect()
    _ensure_meta(con)
    wf = ingest_workflow(con)
    oc = ingest_opencode(con)
    git = ingest_git(con)
    tk = sync_tasks(con)
    con.commit()
    _set_meta(con, "last_run", _now_iso())
    con.commit()
    con.close()
    print(f"telemetry: workflow={wf} opencode={oc} git={git} tasks={tk} db={DB_PATH}")


if __name__ == "__main__":
    try:
        run()
    except Exception as e:  # noqa: BLE001
        print(f"telemetry ERROR: {type(e).__name__}: {e}", file=sys.stderr)
        sys.exit(1)
