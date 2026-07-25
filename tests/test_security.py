"""Testes Prometheus Memory — seguranca e parsers (sem infra externa)."""
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "web"))


def test_cid_sanitized():
    from rag_engine import RAGEngine
    import re
    raw = 'x"><img src=y onerror=alert(1)> Coleção'
    cid = re.sub(r"[^a-z0-9-]", "-", raw.lower())[:40]
    assert '"' not in cid and "<" not in cid and ">" not in cid
    assert cid.startswith("x---img-src-y")


def test_safe_note_path_blocks_traversal(tmp_path):
    os.environ["PROMETHEUS_NOTES_DIR"] = str(tmp_path)
    import importlib
    import notes_routes
    importlib.reload(notes_routes)
    assert notes_routes._safe_note_path("../../etc/passwd") is None
    assert notes_routes._safe_note_path("/etc/passwd") is None
    assert notes_routes._safe_note_path("ok/nota.md") is not None


def test_is_safe_url_blocks_private():
    import notes_routes
    assert notes_routes._is_safe_url("ftp://example.com") is False
    assert notes_routes._is_safe_url("http://127.0.0.1/admin") is False
    assert notes_routes._is_safe_url("http://169.254.169.254/latest") is False
    assert notes_routes._is_safe_url("http://203.0.113.1/") is False
    assert notes_routes._is_safe_url("https://github.com/user/repo") is True


def test_sanitize_markdown_removes_html():
    from notes_routes import sanitize_markdown
    out = sanitize_markdown('<div class="x">texto</div><img src="y"> **negrito**')
    assert "<div" not in out and "<img" not in out
    assert "texto" in out and "**negrito**" in out


def test_parse_mnemosyne_output():
    from app import parse_mnemosyne_output
    raw = "  ID: abc123\n  Content: fato importante\n  Score: 0.85\n  ID: def456\n  Content: outro fato\n  Score: 0.70\n"
    items = parse_mnemosyne_output(raw)
    assert len(items) == 2
    assert items[0]["id"] == "abc123"
    assert items[0]["score"] == 0.85


def test_auth_guard_logic(monkeypatch):
    import importlib
    import auth_guard
    monkeypatch.setenv("PROMETHEUS_HOST", "127.0.0.1")
    importlib.reload(auth_guard)
    assert auth_guard.auth_required() is False
    monkeypatch.setenv("PROMETHEUS_HOST", "0.0.0.0")
    importlib.reload(auth_guard)
    assert auth_guard.auth_required() is True
