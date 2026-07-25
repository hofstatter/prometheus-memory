#!/usr/bin/env python3
"""Auth condicional: token Bearer obrigatorio quando bind != localhost.

Modos (PROMETHEUS_PROTECT_READS):
- false (default): so escritas (POST/PUT/DELETE) exigem token — UI navegavel
- true: todas as rotas /api/* exigem token (modo estrito)
"""
import hmac
import os
from functools import wraps

from flask import jsonify, request

PROMETHEUS_HOST = os.environ.get("PROMETHEUS_HOST", "127.0.0.1")
PROMETHEUS_TOKEN = os.environ.get("PROMETHEUS_TOKEN", "")
PROTECT_READS = os.environ.get("PROMETHEUS_PROTECT_READS", "false").lower() == "true"
LOCAL_HOSTS = ("127.0.0.1", "localhost", "::1")
PUBLIC_POST_PATHS = ("/api/notes/search", "/api/rag/search")


def auth_required():
    return PROMETHEUS_HOST not in LOCAL_HOSTS


def _unauthorized():
    if not PROMETHEUS_TOKEN:
        return jsonify({"error": "PROMETHEUS_TOKEN nao configurado (obrigatorio quando PROMETHEUS_HOST != 127.0.0.1)"}), 500
    auth = request.headers.get("Authorization", "")
    token = auth[7:] if auth.startswith("Bearer ") else ""
    if not token or not hmac.compare_digest(token, PROMETHEUS_TOKEN):
        return jsonify({"error": "unauthorized"}), 401
    return None


def require_token_if_exposed(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if not auth_required():
            return f(*args, **kwargs)
        if not PROTECT_READS and (request.method == "GET" or request.path in PUBLIC_POST_PATHS):
            return f(*args, **kwargs)
        denial = _unauthorized()
        if denial:
            return denial
        return f(*args, **kwargs)

    return wrapper
