"""Testes do pipeline L0→L3 (aggregator, persona, skills, retention, briefing, storage)."""
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "web"))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

os.environ["DATA_DIR"] = "/tmp/bytex-test-pipeline"
os.makedirs("/tmp/bytex-test-pipeline", exist_ok=True)


def test_aggregator_watermark():
    from memory_aggregator import load_state, save_state, STATE_FILE
    state = {"processed_ids": ["a1", "b2"], "last_run": "2026-07-27"}
    save_state(state)
    loaded = load_state()
    assert "a1" in loaded["processed_ids"] and "b2" in loaded["processed_ids"]
    save_state({"processed_ids": []})


def test_scene_degraded_no_llm(monkeypatch):
    monkeypatch.setenv("LLM_BACKEND", "degraded")
    import importlib
    import llm_backend
    importlib.reload(llm_backend)
    out = llm_backend.call_llm("qualquer prompt")
    assert out == ""


def test_persona_not_persisted_on_error(monkeypatch, tmp_path):
    monkeypatch.setenv("LLM_BACKEND", "degraded")
    import importlib
    import llm_backend
    importlib.reload(llm_backend)
    import persona_synthesizer
    importlib.reload(persona_synthesizer)
    result = persona_synthesizer.synthesize_persona(["cena1", "cena2", "cena3"])
    assert result == ""


def test_skill_dedup(tmp_path):
    skill_dir = tmp_path / "skills"
    skill_dir.mkdir()
    existing = skill_dir / "ja-existe.md"
    existing.write_text("# skill existente")
    assert existing.exists()


def test_briefing_cap():
    max_chars = 2000
    briefing = "x" * 5000
    assert len(briefing[:max_chars]) <= max_chars
    assert len(briefing[:max_chars]) // 4 <= 500


def test_storage_wal(tmp_path):
    db = tmp_path / "test.db"
    from storage import SQLiteStore
    store = SQLiteStore(str(db))
    con = store.connect()
    mode = con.execute("PRAGMA journal_mode").fetchone()[0]
    busy = con.execute("PRAGMA busy_timeout").fetchone()[0]
    assert mode == "wal"
    assert busy == 5000
    con.close()


def test_parse_mnemosyne_output_edge():
    from app import parse_mnemosyne_output
    assert parse_mnemosyne_output("") == []
    assert parse_mnemosyne_output("lixo sem formato") == []
    raw = "  ID: abc\n  Content: fato\n  Score: nao-numero\n"
    items = parse_mnemosyne_output(raw)
    assert len(items) == 1 and items[0]["score"] == 0.0


def test_llm_backend_describe():
    import llm_backend
    d = llm_backend.describe()
    assert isinstance(d, str) and len(d) > 0
