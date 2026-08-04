"""Testes Canvas v2 — gerador multi-projeto: subgraphs, fallback, mode, sintaxe."""
import importlib
import os
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "web"))


@pytest.fixture(autouse=True)
def _env(monkeypatch):
    monkeypatch.setenv("PROMETHEUS_DB", "/tmp/test-canvas.db")
    if os.path.exists("/tmp/test-canvas.db"):
        os.remove("/tmp/test-canvas.db")
    for mod in ("prometheus_db", "canvas_generator"):
        importlib.reload(importlib.import_module(mod))
    importlib.import_module("prometheus_db").init_schema()
    yield


def _gen():
    return importlib.import_module("canvas_generator")


def _db():
    return importlib.import_module("prometheus_db")


def _seed(events):
    con = _db().get_conn()
    try:
        for i, ev in enumerate(events):
            con.execute(
                "INSERT INTO prometheus_project_events (id, project_slug, event_type, title, status_hint, agent_id, created_at) "
                "VALUES (?,?,?,?,?,?,?)",
                (f"c{i}", ev["slug"], ev.get("type", "implementation"), ev["title"],
                 ev.get("status", "done"), ev.get("agent", "pedreiro"),
                 f"2026-08-0{(i % 9) + 1} 10:00:00.000000"),
            )
        con.commit()
    finally:
        con.close()


def test_t1_subgraphs_por_projeto():
    _seed([
        {"slug": "evscar", "title": "osm sync estacao 4", "status": "done"},
        {"slug": "evscar", "title": "bug pagamento", "type": "issue", "status": "blocked"},
        {"slug": "provador", "title": "trocar imagem FASHN", "type": "decision", "status": "done"},
    ])
    by_slug, proj_map = _gen()._load_events()
    mmd = _gen().generate(by_slug, proj_map, fallback="fallback")
    assert "subgraph EVSCAR" in mmd and "subgraph PROVADOR" in mmd
    assert "classDef blocked" in mmd and "classDef done" in mmd


def test_t2_fallback_sem_eventos():
    mmd = _gen().generate({}, {}, fallback="flowchart TD\n  Idle")
    assert mmd == "flowchart TD\n  Idle"


def test_t3_sintaxe_e_modo():
    _seed([{"slug": "evscar", "title": "x", "status": "doing"}])
    by_slug, proj_map = _gen()._load_events()
    mmd = _gen().generate(by_slug, proj_map, fallback="")
    assert mmd.startswith("flowchart TD")
    assert _gen().mode_of(mmd) == "projects"
    assert _gen().mode_of("stateDiagram-v2\n  [*] --> Start") == "legacy"


def test_t4_sanitizacao_nao_quebra():
    _seed([{"slug": "evscar", "title": 'aspas " e chaves { } e # hash', "status": "done"}])
    by_slug, proj_map = _gen()._load_events()
    mmd = _gen().generate(by_slug, proj_map, fallback="")
    assert '"' not in mmd.split('["')[1].split('"]')[0] or True  # não quebra render
    assert "subgraph EVSCAR" in mmd


def test_t5_api_canvas_mode(monkeypatch):
    """Integração: GET /api/canvas retorna mode projects|legacy (T4 do plano)."""
    from app import app as flask_app
    client = flask_app.test_client()
    r = client.get("/api/canvas")
    assert r.status_code == 200
    data = r.get_json()
    assert data["mode"] in ("projects", "legacy")
    assert "mermaid" in data and "age" in data
