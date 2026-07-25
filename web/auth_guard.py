#!/usr/bin/env python3
"""Auth do Prometheus: login por senha (sessao HMAC) + token de API.

Modos:
- bind localhost: tudo livre
- bind exposto (default): leitura livre, escritas exigem sessao ou token
- PROMETHEUS_PROTECT_READS=true: tudo exige sessao ou token

Sessao: token HMAC "{exp}.{sig}" (30 dias), emitido por /api/auth/login.
API/agents: Authorization: Bearer $PROMETHEUS_TOKEN.
"""
import base64
import hashlib
import hmac
import os
import time
from functools import wraps

from flask import Blueprint, jsonify, request

PROMETHEUS_HOST = os.environ.get("PROMETHEUS_HOST", "127.0.0.1")
PROMETHEUS_TOKEN = os.environ.get("PROMETHEUS_TOKEN", "")
PROMETHEUS_PASSWORD = os.environ.get("PROMETHEUS_PASSWORD", "")
PROTECT_READS = os.environ.get("PROMETHEUS_PROTECT_READS", "false").lower() == "true"
LOCAL_HOSTS = ("127.0.0.1", "localhost", "::1")
PUBLIC_POST_PATHS = ("/api/notes/search", "/api/rag/search")
PUBLIC_PATHS = ("/health", "/api/auth/login")
SESSION_TTL = 30 * 86400

auth_bp = Blueprint("auth", __name__)

_logins: dict[str, list[float]] = {}
LOGIN_LIMIT = 5
LOGIN_WINDOW = 60


def auth_required():
    return PROMETHEUS_HOST not in LOCAL_HOSTS


def _secret() -> str:
    return PROMETHEUS_TOKEN or PROMETHEUS_PASSWORD or "prometheus-default-secret"


def _sign(payload: str) -> str:
    return hmac.new(_secret().encode(), payload.encode(), hashlib.sha256).hexdigest()[:32]


def make_session() -> str:
    exp = str(int(time.time()) + SESSION_TTL)
    return f"{exp}.{_sign('session:' + exp)}"


def check_session(token: str) -> bool:
    if not token or "." not in token:
        return False
    exp, sig = token.rsplit(".", 1)
    if not exp.isdigit() or int(exp) < time.time():
        return False
    return hmac.compare_digest(sig, _sign("session:" + exp))


def _valid_credential(header: str) -> bool:
    token = header[7:] if header.startswith("Bearer ") else ""
    if not token:
        return False
    if PROMETHEUS_TOKEN and hmac.compare_digest(token, PROMETHEUS_TOKEN):
        return True
    return check_session(token)


@auth_bp.post("/api/auth/login")
def login():
    ip = request.headers.get("X-Forwarded-For", request.remote_addr or "?").split(",")[0].strip()
    now = time.time()
    attempts = [t for t in _logins.get(ip, []) if now - t < LOGIN_WINDOW]
    if len(attempts) >= LOGIN_LIMIT:
        return jsonify({"error": "muitas tentativas — aguarde 1 minuto"}), 429
    if not PROMETHEUS_PASSWORD:
        return jsonify({"error": "login desabilitado (PROMETHEUS_PASSWORD nao configurada)"}), 503
    pwd = (request.get_json(silent=True) or {}).get("password", "")
    if not pwd or not hmac.compare_digest(pwd, PROMETHEUS_PASSWORD):
        attempts.append(now)
        _logins[ip] = attempts
        return jsonify({"error": "senha incorreta"}), 401
    _logins.pop(ip, None)
    return jsonify({"token": make_session(), "expires_days": 30})


@auth_bp.get("/api/auth/check")
def check():
    if not auth_required():
        return jsonify({"authenticated": True})
    ok = _valid_credential(request.headers.get("Authorization", ""))
    return jsonify({"authenticated": ok})


def require_token_if_exposed(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if not auth_required():
            return f(*args, **kwargs)
        path = request.path
        if path in PUBLIC_PATHS or path == "/" or path.startswith("/static/"):
            return f(*args, **kwargs)
        if not PROTECT_READS and (request.method == "GET" or path in PUBLIC_POST_PATHS):
            return f(*args, **kwargs)
        if not PROMETHEUS_TOKEN and not PROMETHEUS_PASSWORD:
            return jsonify({"error": "PROMETHEUS_TOKEN ou PROMETHEUS_PASSWORD obrigatorio quando PROMETHEUS_HOST != 127.0.0.1"}), 500
        if not _valid_credential(request.headers.get("Authorization", "")):
            return jsonify({"error": "unauthorized"}), 401
        return f(*args, **kwargs)

    return wrapper
