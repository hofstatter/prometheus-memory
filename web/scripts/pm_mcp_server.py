#!/usr/bin/env python3
"""Prometheus PM — Micro-MCP stdio de telemetria de projetos (PLAN_TELEMETRIA_PUSH_MCP F1).

Expõe 3 tools que traduzem chamadas MCP → HTTP para o painel Prometheus (:8777):
  pm_event    — registra evento de projeto (Kanban/Timeline em tempo real)
  pm_session  — presença: start / heartbeat / close
  pm_tasks    — leitura do board de tarefas de um projeto

Token: lido de PROMETHEUS_TOKEN (env) ou do .env do projeto web
(~/Projetos/web/.env). NUNCA imprime o token.

Uso:
  python3 pm_mcp_server.py            # sobe como MCP stdio
  python3 pm_mcp_server.py --selftest # dispara 1 evento de teste e sai
"""
from __future__ import annotations

import hashlib
import json
import os
import sys
import time
import urllib.request
import urllib.error
from datetime import datetime, timezone
from pathlib import Path

HOST = os.environ.get("PROMETHEUS_HOST", "127.0.0.1")
PORT = int(os.environ.get("PROMETHEUS_PORT", "8777"))
BASE = f"http://{HOST}:{PORT}"
WEB_ENV = Path(os.environ.get("PROMETHEUS_WEB_ENV", str(Path.home() / "Projetos" / "web" / ".env")))


def _load_token() -> str:
    """PROMETHEUS_TOKEN (env) > PROMETHEUS_TOKEN= no web/.env. Nunca imprime."""
    tok = os.environ.get("PROMETHEUS_TOKEN", "").strip()
    if tok:
        return tok
    try:
        for line in WEB_ENV.read_text(encoding="utf-8", errors="replace").splitlines():
            line = line.strip()
            if line.startswith("PROMETHEUS_TOKEN="):
                return line.split("=", 1)[1].strip().strip('"').strip("'")
    except OSError:
        pass
    return ""


def _sha1(*parts: str, n: int = 20) -> str:
    h = hashlib.sha1()
    for p in parts:
        h.update(str(p).encode("utf-8", "replace"))
    return h.hexdigest()[:n]


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _session_key(cwd: str = "") -> str:
    """Chave de sessão coarse: opencode + cwd + data. OpenCode não injeta session id no env MCP."""
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    return f"opencode:{_sha1(cwd or os.getcwd(), today, n=12)}"


def _client_event_id(session_key: str, event_type: str, title: str) -> str:
    minute = datetime.now(timezone.utc).strftime("%Y%m%d%H%M")
    return _sha1(session_key, event_type, title, minute, n=20)


def _post(path: str, payload: dict) -> dict:
    token = _load_token()
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    req = urllib.request.Request(BASE + path, data=json.dumps(payload).encode(), headers=headers, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            body = r.read().decode("utf-8", "replace")
            return {"status": r.status, "data": json.loads(body) if body else {}}
    except urllib.error.HTTPError as e:
        return {"status": e.code, "data": {"error": e.read().decode("utf-8", "replace")[:300]}}
    except Exception as e:  # noqa: BLE001
        return {"status": 0, "data": {"error": f"{type(e).__name__}: {e}"[:300]}}


def _get(path: str) -> dict:
    token = _load_token()
    headers = {}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    req = urllib.request.Request(BASE + path, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            body = r.read().decode("utf-8", "replace")
            return {"status": r.status, "data": json.loads(body) if body else {}}
    except urllib.error.HTTPError as e:
        return {"status": e.code, "data": {"error": e.read().decode("utf-8", "replace")[:300]}}
    except Exception as e:  # noqa: BLE001
        return {"status": 0, "data": {"error": f"{type(e).__name__}: {e}"[:300]}}


def _agent_id() -> str:
    return os.environ.get("OPENCODE_AGENT_ID") or os.environ.get("OPENCODE_AGENT") or "opencode"


# ---------- tools ----------
def pm_event(
    event_type: str,
    title: str,
    summary: str = "",
    status_hint: str = "",
    progress_delta: float = 0.0,
    project_slug: str = "",
    cwd: str = "",
) -> dict:
    """Registra um evento de projeto no painel Prometheus (Kanban/Timeline em tempo real).

    event_type: planning|implementation|review|note|decision|docs|fix
    title: título curto do marco/entrega
    summary: detalhe opcional
    status_hint: done (revisão/docs/fix/decision) ou doing (work em andamento)
    project_slug: slug do projeto (ex.: evscar, prometheus-memory); vazio = resolve por cwd
    """
    sk = _session_key(cwd)
    payload = {
        "client_event_id": _client_event_id(sk, event_type, title),
        "harness": "opencode",
        "harness_session_id": sk,
        "agent_id": _agent_id(),
        "event_type": event_type,
        "title": title,
        "summary": summary,
        "status_hint": status_hint,
        "progress_delta": float(progress_delta or 0),
        "project_slug": project_slug,
        "cwd": cwd or os.getcwd(),
    }
    return _post("/api/pm/events", payload)


def pm_session(action: str, current_action: str = "", project_slug: str = "", cwd: str = "") -> dict:
    """Presença: inicia/atualiza/encerra a sessão do agente no painel.

    action: start (início de sessão) | heartbeat (atividade contínua) | close (fim de sessão)
    """
    sk = _session_key(cwd)
    if action == "start":
        return _post("/api/pm/sessions/start", {
            "harness": "opencode",
            "harness_session_id": sk,
            "agent_id": _agent_id(),
            "current_action": current_action,
            "project_slug": project_slug,
            "cwd": cwd or os.getcwd(),
        })
    if action == "close":
        return _post("/api/pm/sessions/close", {"session_key": sk})
    return _post("/api/pm/sessions/heartbeat", {
        "session_key": sk,
        "current_action": current_action,
    })


def pm_tasks(project_slug: str) -> dict:
    """Lê as tarefas (board) de um projeto do painel Prometheus."""
    if not project_slug:
        return {"status": 400, "data": {"error": "project_slug obrigatorio"}}
    return _get(f"/api/pm/projects/{project_slug}/tasks")


# ---------- MCP / selftest ----------
def _selftest() -> int:
    print(f"[selftest] base={BASE} token={'set' if _load_token() else 'MISSING'}", flush=True)
    res = pm_event("note", "telemetry selftest", summary="push MCP OK", status_hint="done",
                   project_slug="prometheus-memory")
    print("[selftest] pm_event ->", json.dumps(res, ensure_ascii=False)[:400], flush=True)
    ok = res.get("status") in (200, 201)
    print("[selftest] RESULTADO:", "OK" if ok else "FALHOU", flush=True)
    return 0 if ok else 1


def main() -> int:
    if "--selftest" in sys.argv:
        return _selftest()
    from fastmcp import FastMCP

    mcp = FastMCP("prometheus-pm")
    mcp.tool(pm_event)
    mcp.tool(pm_session)
    mcp.tool(pm_tasks)
    mcp.run(transport="stdio")
    return 0


if __name__ == "__main__":
    sys.exit(main())
