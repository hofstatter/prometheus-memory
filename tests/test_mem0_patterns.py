"""Testes Fase C — Mem0 parity: extração, dedup, grounding temporal, threshold, entities."""
import importlib
import os
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "web"))


@pytest.fixture(autouse=True)
def _env(monkeypatch, tmp_path):
    monkeypatch.setenv("PROMETHEUS_DB", "/tmp/test-mem0.db")
    monkeypatch.setenv("PROMETHEUS_PROJECTS_ROOT", str(Path.home() / "Projetos"))
    monkeypatch.setenv("PROMETHEUS_NOTES_DIR", str(tmp_path / "notas"))
    if os.path.exists("/tmp/test-mem0.db"):
        os.remove("/tmp/test-mem0.db")
    for mod in ("prometheus_db", "memory", "dedup", "entity_store", "extractor", "notes_routes"):
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


def test_c6_entities_linked(monkeypatch):
    es = _mod("entity_store")
    # fallback determinístico: LLM indisponível → heurística v1
    monkeypatch.setattr(es, "call_llm", lambda *a, **k: "")
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


def test_c8_entities_llm_acronyms(monkeypatch):
    es = _mod("entity_store")
    monkeypatch.setattr(es, "call_llm", lambda *a, **k:
        '[{"fact": 0, "name": "FASHN", "type": "project"}, '
        '{"fact": 0, "name": "EVSCAR", "type": "project"}]')
    n = es.extract_and_link("mem1", "FASHN e EVSCAR usam o Prometheus Memory")
    assert n >= 2
    ents = {e["name"]: e["type"] for e in es.list_entities()}
    assert ents.get("FASHN") == "project"
    assert ents.get("EVSCAR") == "project"
    assert "mem1" in es.memories_for("FASHN")


def test_c9_entities_type_upgrade(monkeypatch):
    es = _mod("entity_store")
    db = _mod("prometheus_db")
    con = db.get_conn()
    con.execute("INSERT INTO prometheus_entities (id, name, type) VALUES ('e1', 'ZedAI', 'auto')")
    con.commit()
    monkeypatch.setattr(es, "call_llm", lambda *a, **k:
        '[{"fact": 0, "name": "ZedAI", "type": "tech"}]')
    es.extract_and_link("mem9", "ZedAI é uma API de visão")
    row = con.execute("SELECT type FROM prometheus_entities WHERE name = 'ZedAI'").fetchone()
    assert row["type"] == "tech"
    con.close()


def test_c10_entities_fallback(monkeypatch):
    es = _mod("entity_store")
    monkeypatch.setattr(es, "call_llm", lambda *a, **k: "")
    n = es.extract_and_link("mem10", "Decisão: trocar Visionário")
    assert n >= 1
    assert "mem10" in es.memories_for("Visionário")


def test_c11_batch_mapping(monkeypatch):
    es = _mod("entity_store")
    # índice 9 errado (FASHN está no fato 0) → scan resolve; RAG índice certo
    monkeypatch.setattr(es, "call_llm", lambda *a, **k:
        '[{"fact": 9, "name": "FASHN", "type": "project"}, '
        '{"fact": 1, "name": "RAG", "type": "tech"}]')
    batch = es.extract_entities_batch(["fato sobre FASHN", "usamos RAG multimodal"])
    assert {k: [e["name"] for e in v] for k, v in batch.items()} == {0: ["FASHN"], 1: ["RAG"]}


def test_c12_semantic_dedup(monkeypatch):
    memory = _mod("memory")
    monkeypatch.setattr(_mod("extractor"), "call_llm", lambda *a, **k:
        '["Decisão: trocar Visionário GLM por MiniMax M3 em 2026-08-03"]')
    state = {"ret": []}
    monkeypatch.setattr(memory, "recall_lane", lambda ch, q, top_k=5: state["ret"])
    r1 = memory.remember_inferred("trocar o Visionário hoje", channel="proj:dedup",
                                  session="prom-proj-dedup")
    assert r1["stored"] == 1 and r1["degraded"] is False
    state["ret"] = [{"content": "Decisão: trocar Visionário GLM por MiniMax M3 em 2026-08-03",
                     "score": 0.95}]
    r2 = memory.remember_inferred("o Visionário foi substituído pelo MiniMax M3",
                                  channel="proj:dedup", session="prom-proj-dedup")
    assert r2["skipped_duplicates"] >= 1 and r2["stored"] == 0, "quase-duplicata deve ser pulada"


def test_c13_semantic_guard(monkeypatch):
    memory = _mod("memory")
    monkeypatch.setattr(_mod("extractor"), "call_llm", lambda *a, **k:
        '["Decisão: trocar Visionário GLM por MiniMax M3 em 2026-08-03", '
        '"FASHN lançou o produto X em 2026-08-04"]')
    monkeypatch.setattr(memory, "recall_lane", lambda ch, q, top_k=5:
        [{"content": "Decisão: trocar Visionário GLM por MiniMax M3 em 2026-08-03", "score": 0.95}])
    r = memory.remember_inferred("decisão antiga e novidade da FASHN", channel="proj:guard",
                                 session="prom-proj-guard")
    assert r["stored"] == 1, "fato distinto não pode ser pulado"
    assert r["skipped_duplicates"] == 1, "fato quase-duplicado deve ser pulado"


def test_c14_notes_fts_idempotent():
    nr = _mod("notes_routes")
    db = _mod("prometheus_db").get_conn()
    nr._sync_notes_fts(db)
    first = db.execute("SELECT COUNT(*) c FROM notes_fts").fetchone()["c"]
    nr._sync_notes_fts(db)
    second = db.execute("SELECT COUNT(*) c FROM notes_fts").fetchone()["c"]
    assert first == second, "sync incremental não pode duplicar linhas"
    db.close()


def test_c15_notes_index_note(tmp_path, monkeypatch):
    nr = _mod("notes_routes")
    db = _mod("prometheus_db").get_conn()
    nr._fts_ready(db)
    note = nr.NOTES_DIR / "nova.md"
    note.write_text("nota criada pela API")
    nr._index_note("nova.md")
    rows = db.execute("SELECT name FROM notes_fts").fetchall()
    assert any(r["name"] == "nova.md" for r in rows), "create deve indexar a nota"
    note.write_text("nota editada pela API")
    nr._index_note("nova.md")
    content = db.execute(
        "SELECT content FROM notes_fts WHERE name = 'nova.md'"
    ).fetchone()["content"]
    assert "editada" in content, "update deve atualizar o conteúdo"
    note.unlink()
    nr._index_note("nova.md")
    rows = db.execute("SELECT name FROM notes_fts WHERE name = 'nova.md'").fetchall()
    assert rows == [], "delete deve remover do índice"
    db.close()


def test_c16_entities_containment_resolve():
    es = _mod("entity_store")
    db = _mod("prometheus_db")
    con = db.get_conn()
    con.execute("INSERT INTO prometheus_entities (id, name, type) VALUES ('e1', 'MiniMax M3', 'tech')")
    con.commit()
    assert es.resolve_canonical(con, "MiniMax", "tech") == "e1"
    assert es.resolve_canonical(con, "MiniMax M3", "tech") == "e1"
    assert es.resolve_canonical(con, "MiniMax", "org") is None, "type diferente não resolve"
    con.close()


def test_c17_entities_accent_normalize():
    es = _mod("entity_store")
    db = _mod("prometheus_db")
    con = db.get_conn()
    con.execute("INSERT INTO prometheus_entities (id, name, type) VALUES ('e2', 'Visão', 'tech')")
    con.commit()
    assert es.normalize_name("Visão") == "visao"
    assert es.resolve_canonical(con, "Visao", "tech") == "e2", "acento normaliza para canônico"
    con.close()


def test_c18_entities_types_do_not_merge():
    es = _mod("entity_store")
    db = _mod("prometheus_db")
    con = db.get_conn()
    con.execute("INSERT INTO prometheus_entities (id, name, type) VALUES ('e3', 'Apple', 'org')")
    con.execute("INSERT INTO prometheus_entities (id, name, type) VALUES ('e4', 'Apple', 'tech')")
    con.commit()
    assert es.resolve_canonical(con, "Apple", "org") == "e3"
    assert es.resolve_canonical(con, "Apple", "tech") == "e4"
    assert es.resolve_canonical(con, "AI", "tech") is None, "containment < 3 chars não merge"
    con.close()


def test_c19_merge_sums_and_relinks():
    es = _mod("entity_store")
    db = _mod("prometheus_db")
    con = db.get_conn()
    con.execute("INSERT INTO prometheus_entities (id, name, type, mention_count) "
                "VALUES ('c1', 'FASHN', 'project', 5)")
    con.execute("INSERT INTO prometheus_entities (id, name, type, mention_count) "
                "VALUES ('c2', 'FASHN Projeto', 'project', 3)")
    con.execute("INSERT INTO prometheus_memory_entities (memory_id, entity_id) VALUES ('m1', 'c2')")
    con.commit()
    res = es.merge_into(con, "c2", "c1")
    assert res["ok"] and res["mentions_moved"] == 3
    c1 = con.execute("SELECT mention_count FROM prometheus_entities WHERE id = 'c1'").fetchone()
    assert c1["mention_count"] == 8, "menções somadas"
    linked = con.execute(
        "SELECT memory_id FROM prometheus_memory_entities WHERE entity_id = 'c1'"
    ).fetchall()
    assert "m1" in [r["memory_id"] for r in linked], "memória re-linkada no canônico"
    alias = con.execute("SELECT canonical_id FROM prometheus_entities WHERE id = 'c2'").fetchone()
    assert alias["canonical_id"] == "c1", "alias marcado"
    con.close()
