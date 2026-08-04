"""Testes do harness LongMemEval (M5) — funções puras, sem LLM nem ingest."""
import importlib
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "evals"))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "web"))


@pytest.fixture(autouse=True)
def _mod():
    return importlib.import_module("longmemeval_runner")


def test_l1_select_subset_stratified(_mod):
    data = []
    types = ["a", "a", "b", "b", "b", "c"]
    for i, t in enumerate(types):
        data.append({"question_id": f"q{i}", "question_type": t})
    sub = _mod._select_subset(data, 4)
    assert 1 <= len(sub) <= 4
    got = {i["question_type"] for i in sub}
    assert got <= {"a", "b", "c"}
    # estável com mesmo seed
    assert [i["question_id"] for i in sub] == \
           [i["question_id"] for i in _mod._select_subset(data, 4)]


def test_l2_render_content(_mod):
    raw = ("[MEMORIA memoria_facts]\n"
           "[Fact sequence] first: first purchase from that new clothing brand\n"
           "[Fact metric] purchases_remember_getting_pct: 10%\n"
           "[Fact metric] case_saved_from_pct: 10%")
    out = _mod._render_content(raw)
    assert "MEMORIA" not in out, "tag de suplemento descartada"
    assert "purchases remember getting pct: 10%" in out, "snake_case decodificado"
    assert "first: first purchase" in out, "fact sequence preservada"


def test_l3_render_plain(_mod):
    assert _mod._render_content("memória normal") == "memória normal"


def test_l4_parse_int(_mod):
    assert _mod._parse_int("1") == 1
    assert _mod._parse_int("Veredito: 0") == 0
    assert _mod._parse_int("") is None
    assert _mod._parse_int("incorreta") is None
