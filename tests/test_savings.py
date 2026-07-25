"""Testes briefing + token savings."""
import importlib
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "web"))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))


def test_briefing_cap():
    max_chars = 2000
    briefing = "x" * 5000
    assert len(briefing[:max_chars]) <= max_chars
    assert len(briefing[:max_chars]) // 4 <= 500


def test_savings_math(tmp_path):
    refs = tmp_path / "refs" / "2026-07-25"
    refs.mkdir(parents=True)
    (refs / "abc_1.md").write_bytes(b"x" * 4000)
    os.environ["MNEMOSYNE_HOME"] = str(tmp_path)
    import token_savings
    importlib.reload(token_savings)
    d = token_savings.compute_savings(recalls_served=10)
    assert d["offloaded_bytes"] == 4000
    assert d["offload_tokens_saved"] == 1000
    assert d["compression_tokens_saved"] == 400
    assert d["total_tokens_saved"] == 1400


def test_savings_empty(tmp_path):
    os.environ["MNEMOSYNE_HOME"] = str(tmp_path)
    import token_savings
    importlib.reload(token_savings)
    d = token_savings.compute_savings(0)
    assert d["total_tokens_saved"] == 0
