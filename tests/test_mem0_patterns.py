"""Testes Fase C — Mem0 parity: extração, dedup, grounding temporal, threshold, entities."""
import importlib
import os
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "web"))


@pytest.fixture(autouse=True)
def _env(monkeypatch):
    monkeypatch.setenv("PROMETHEUS_DB", "/tmp/test-mem0.db")
    monkeypatch.setenv("PROMETHEUS_PROJECTS_ROOT", str(Path.home() / "Projetos"))
    if os.path.exists("/tmp/test-mem0.db"):
        os.remove("/tmp/test-mem0.db")
    for mod in ("prometheus_db", "memory", "dedup", "entity_store", "extractor"):
        importlib.reload(importlib.import_module(mod))
    importlib.import_module("prometheus_db").init_schema()
    yield


def _mod(name):
    return importlib.import_module(name)


def test_c1_ground_temporal():
    ext = _mod("extractor")
    out = ext.ground_temporal("hoje decidimos trocar o modelo; ontem testamos a api", today="2026-08-03")
    assert "2026-08-03" in out and "2026-08-02" in out
    out2 = ext.ground_temporal("fiz deploy há 3 dias", today="2026-08-03")
    assert "2026-07-31" in out2


def test_c2_extract_facts_mock(monkeypatch):
    ext = _mod("extractor")
    monkeypatch.setattr(ext, "call_llm", lambda *a, **k: '["Fato um.", "Fato dois."]')
    facts = ext.extract_facts("mensagem qualquer")
    assert facts == ["Fato um.", "Fato dois."]
    monkeypatch.setattr(ext, "call_llm", lambda *a, **k: "")
    assert ext.extract_facts("msg") == []


def test_c3_dedup_normalized():
    d = _mod("dedup")
    assert d.content_hash("  Decisão: X  ") == d.content_hash("decisão: x")


def test_c4_remember_inferred_dedup(monkeypatch):
    memory = _mod("memory")
    # força extração determinística (sem LLM real)
    monkeypatch.setattr(_mod("extractor"), "call_llm",
                        lambda *a, **k: '["Decisão: trocar Visionário GLM por MiniMax M3 em 2026-08-03"]')
    r1 = memory.remember_inferred("trocar o Visionário hoje", channel="proj:evscar", session="prom-proj-evscar")
    assert r1["stored"] == 1 and r1["degraded"] is False
    r2 = memory.remember_inferred("trocar o Visionário hoje", channel="proj:evscar", session="prom-proj-evscar")
    assert r2["skipped_duplicates"] >= 1 and r2["stored"] == 0, "2ª gravação deve ser duplicata"
    # channel diferente → não dedup cruzado
    r3 = memory.remember_inferred("trocar o Visionário hoje", channel="proj:provador", session="prom-proj-provador")
    assert r3["stored"] == 1


def test_c5_remember_inferred_fallback(monkeypatch):
    memory = _mod("memory")
    monkeypatch.setattr(_mod("extractor"), "call_llm", lambda *a, **k: "")
    r = memory.remember_inferred("fato bruto sem llm", channel="proj:x", session="prom-proj-x")
    assert r["degraded"] is True and r["stored"] == 1


def test_c6_entities_linked():
    es = _mod("entity_store")
    n = es.extract_and_link("mem123", "Decisão: trocar Visionário GLM-4.6V por MiniMax M3")
    assert n >= 1
    mems = es.memories_for("Visionário")
    assert "mem123" in mems
    assert es.list_entities()


def test_c7_threshold():
    memory = _mod("memory")
    res = [{"id": "a", "score": 0.8}, {"id": "b", "score": 0.2}]
    assert [r["id"] for r in memory.apply_threshold(res, 0.5)] == ["a"]
    assert len(memory.apply_threshold(res, None)) == 2
