"""Testes do fluxo de login (auth_guard)."""
import importlib
import os
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "web"))


def _reload(monkeypatch, password="test-password-123", token="tok123"):
    monkeypatch.setenv("PROMETHEUS_HOST", "0.0.0.0")
    monkeypatch.setenv("PROMETHEUS_PASSWORD", password)
    monkeypatch.setenv("PROMETHEUS_TOKEN", token)
    import auth_guard
    importlib.reload(auth_guard)
    return auth_guard


def test_session_roundtrip(monkeypatch):
    ag = _reload(monkeypatch)
    session = ag.make_session()
    assert ag.check_session(session) is True
    assert ag.check_session(session + "x") is False
    assert ag.check_session("lixo") is False


def test_session_expired(monkeypatch):
    ag = _reload(monkeypatch)
    exp = str(int(time.time()) - 10)
    fake = f"{exp}.{ag._sign('session:' + exp)}"
    assert ag.check_session(fake) is False


def test_valid_credential_session_and_token(monkeypatch):
    ag = _reload(monkeypatch)
    session = ag.make_session()
    assert ag._valid_credential(f"Bearer {session}") is True
    assert ag._valid_credential("Bearer tok123") is True
    assert ag._valid_credential("Bearer errado") is False
    assert ag._valid_credential("") is False


def test_login_rate_limit(monkeypatch):
    ag = _reload(monkeypatch)
    from flask import Flask
    app = Flask(__name__)
    app.register_blueprint(ag.auth_bp)
    client = app.test_client()
    for i in range(5):
        r = client.post("/api/auth/login", json={"password": "errada"})
        assert r.status_code == 401
    r = client.post("/api/auth/login", json={"password": "errada"})
    assert r.status_code == 429
    # durante a janela de rate limit, ate a senha certa aguarda (anti-brute-force)
    r = client.post("/api/auth/login", json={"password": "test-password-123"})
    assert r.status_code == 429
    ag._logins.clear()
    r = client.post("/api/auth/login", json={"password": "test-password-123"})
    assert r.status_code == 200
    assert "token" in r.get_json()
