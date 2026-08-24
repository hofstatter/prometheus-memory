#!/usr/bin/env python3
"""
Mnemosyne REST API Wrapper
Exposes Mnemosyne memory as a simple HTTP API for tools that don't support MCP natively.
Also provides OpenAI-compatible /v1/embeddings and /v1/audio/speech endpoints.
Listen on port 8766.
"""
import os
import subprocess
import json
import io
import numpy as np
import requests as http
from flask import Flask, request, jsonify, send_file
from fastembed import TextEmbedding

app = Flask(__name__)
# token via env (MNEMOSYNE_MCP_TOKEN no .env/compose — nunca versionar)
TOKEN = os.environ.get("MNEMOSYNE_MCP_TOKEN", "")

_embed_model = None

def _get_embed_model():
    global _embed_model
    if _embed_model is None:
        _embed_model = TextEmbedding(model_name="BAAI/bge-small-en-v1.5")
    return _embed_model

def _check_auth():
    """Valida Bearer: token global (admin/tenant 1) OU API key de agente (multi-tenant F5)."""
    auth = request.headers.get("Authorization", "")
    if auth == f"Bearer {TOKEN}":
        request.environ["pm_identity"] = {"role": "admin", "tenant_id": 1, "agent_id": None}
        return True
    key = auth[len("Bearer "):].strip() if auth.startswith("Bearer ") else ""
    if key:
        try:
            from auth_gateway import validate_key
            info = validate_key(key)
            if info:
                request.environ["pm_identity"] = {"role": "agent", **info}
                return True
        except Exception:
            pass
    return False


@app.route("/whoami", methods=["GET"])
def whoami():
    if not _check_auth():
        return jsonify({"error": "unauthorized"}), 401
    return jsonify({"identity": request.environ.get("pm_identity", {})})

@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok", "service": "mnemosyne-api"})

@app.route("/recall", methods=["POST"])
def recall():
    if not _check_auth():
        return jsonify({"error": "unauthorized"}), 401
    data = request.get_json(silent=True) or {}
    query = data.get("query", "")
    top_k = data.get("top_k", 5)
    result = subprocess.run(
        ["mnemosyne", "recall", query, str(top_k)],
        capture_output=True, text=True, timeout=30
    )
    return jsonify({"result": result.stdout.strip(), "error": result.stderr.strip() if result.stderr else None})

@app.route("/store", methods=["POST"])
def store():
    if not _check_auth():
        return jsonify({"error": "unauthorized"}), 401
    data = request.get_json(silent=True) or {}
    content = data.get("content", "")
    source = data.get("source", "api")
    importance = data.get("importance", 0.5)
    cmd = ["mnemosyne", "store", content, source, str(importance)]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
    return jsonify({"result": result.stdout.strip(), "error": result.stderr.strip() if result.stderr else None})

@app.route("/stats", methods=["GET"])
def stats():
    if not _check_auth():
        return jsonify({"error": "unauthorized"}), 401
    result = subprocess.run(["mnemosyne", "stats"], capture_output=True, text=True, timeout=10)
    return jsonify({"result": result.stdout.strip()})

@app.route("/v1/embeddings", methods=["POST"])
def embeddings():
    data = request.get_json(silent=True) or {}
    inp = data.get("input", "")
    if isinstance(inp, list):
        texts = inp
    elif isinstance(inp, str):
        texts = [inp]
    else:
        texts = [str(inp)]

    model = _get_embed_model()
    embeddings = list(model.embed(texts))
    data_out = []
    total_tokens = 0
    for i, emb in enumerate(embeddings):
        total_tokens += len(texts[i].split()) if i < len(texts) else 0
        data_out.append({
            "object": "embedding",
            "embedding": emb.tolist(),
            "index": i
        })
    return jsonify({
        "object": "list",
        "data": data_out,
        "model": "bge-small-en-v1.5",
        "usage": {"prompt_tokens": total_tokens, "total_tokens": total_tokens}
    })

@app.route("/v1/audio/speech", methods=["POST"])
def openai_tts():
    """OpenAI-compatible TTS endpoint proxying Pocket TTS."""
    data = request.get_json(silent=True) or {}
    text = data.get("input", "")
    voice = data.get("voice", "rafael")
    if not text:
        return jsonify({"error": "input is required"}), 400
    try:
        resp = http.post("http://localhost:8770/tts",
                        files={"text": (None, text)},
                        timeout=60)
        resp.raise_for_status()
        return send_file(io.BytesIO(resp.content),
                        mimetype="audio/wav",
                        as_attachment=True,
                        download_name="speech.wav")
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8766, debug=False)
