"""Testes Fase B — Skills por projeto: suggest (draft), aprovação humana, promoção.

Env isolado por teste (monkeypatch). Eventos inseridos direto no sidecar
(prometheus_project_events) — sem dependência do Mnemosyne no teste.
"""
import importlib
import json
import os
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "web"))


@pytest.fixture(autouse=True)
def _env(monkeypatch):
    monkeypatch.setenv("PROMETHEUS_DB", "/tmp/test-skills.db")
    monkeypatch.setenv("PROMETHEUS_PROJECTS_ROOT", str(Path.home() / "Projetos"))
    if os.path.exists("/tmp/test-skills.db"):
        os.remove("/tmp/test-skills.db")
    for mod in ("prometheus_db", "skills_builder"):
        importlib.reload(importlib.import_module(mod))
    importlib.import_module("prometheus_db").init_schema()
    yield


def _reg():
    return importlib.import_module("skills_builder")


def _db():
    return importlib.import_module("prometheus_db")


def _add_events(slug, titles):
    from datetime import datetime
    con = _db().get_conn()
    try:
        for i, t in enumerate(titles):
            con.execute(
                "INSERT INTO prometheus_project_events (id, project_slug, event_type, title, status_hint, created_at) "
                "VALUES (?,?,?,?,?,?)",
                (f"{slug}-{i}", slug, "research", t, "done",
                 datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")),
            )
        con.commit()
    finally:
        con.close()


def test_b1_suggest_creates_draft_with_evidence():
    _add_events("osmproj", [
        "pesquisa osm sync",
        "configura osm sync",
        "otimiza osm sync",
        "testa osm sync",
    ])
    skill = _reg().suggest_skill("osmproj")
    assert skill and skill["status"] == "draft" and skill["duplicate"] is False
    assert skill["confidence"] >= 0.5
    rows = _reg().list_skills("osmproj")
    assert len(rows) == 1
    ev = json.loads(rows[0]["evidence_json"])
    assert len(ev) >= 3, "evidências deveriam conter os eventos do padrão"


def test_b2_suggest_idempotent():
    _add_events("idemproj", ["api auth fix", "api auth fix", "api auth fix"])
    a = _reg().suggest_skill("idemproj")
    b = _reg().suggest_skill("idemproj")
    assert a["duplicate"] is False and b["duplicate"] is True
    assert len(_reg().list_skills("idemproj")) == 1


def test_b3_no_pattern_no_skill():
    _add_events("solto", ["implementa a", "implementa b", "implementa c"])
    assert _reg().suggest_skill("solto") is None


def test_b4_approve_human_only():
    _add_events("appr", ["deploy docker", "deploy docker", "deploy docker"])
    skill = _reg().suggest_skill("appr")
    assert skill["status"] == "draft"
    res = _reg().approve_skill(skill["id"])
    assert res and res["status"] == "active"
    # re-aprovar draft inexistente falha
    assert _reg().approve_skill(skill["id"]) is None
    assert _reg().approve_skill("nao-existe") is None


def test_b5_promotion_candidate():
    _add_events("proja", ["kafka setup", "kafka setup", "kafka setup"])
    _add_events("projb", ["kafka setup", "kafka setup", "kafka setup"])
    a = _reg().suggest_skill("proja")
    b = _reg().suggest_skill("projb")
    _reg().approve_skill(a["id"])
    _reg().approve_skill(b["id"])
    cands = _reg().promotion_candidates()
    assert any(c["name"] == a["name"] and c["n_projects"] >= 2 for c in cands)
