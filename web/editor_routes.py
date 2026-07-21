"""Prometheus Editor Routes — Edição inline de memórias estilo Obsidian.

GET /api/memory/<id> é servido por app.py (registrado antes deste blueprint).
Aqui ficam apenas PUT (update) e DELETE (delete).
"""
import subprocess
from flask import Blueprint, request, jsonify

editor_bp = Blueprint('editor', __name__, url_prefix='/api/memory')

def run_mnemosyne(*args, timeout=10):
    r = subprocess.run(["mnemosyne"] + list(args), capture_output=True, text=True, timeout=timeout)
    return r

@editor_bp.put("/<mem_id>")
def update_memory(mem_id):
    data = request.get_json() or {}
    new_content = data.get("content", "").strip()
    new_importance = data.get("importance", "0.5")

    if not new_content:
        return jsonify({"error": "content required"}), 400
    if len(new_content) > 100_000:
        return jsonify({"error": "content too large"}), 413
    try:
        imp = max(0.0, min(1.0, float(new_importance)))
    except (TypeError, ValueError):
        return jsonify({"error": "importance must be 0.0-1.0"}), 400

    r = run_mnemosyne("update", mem_id, new_content, str(imp), timeout=15)
    return jsonify({"ok": r.returncode == 0, "id": mem_id})

@editor_bp.delete("/<mem_id>")
def delete_memory(mem_id):
    r = run_mnemosyne("delete", mem_id, timeout=10)
    return jsonify({"ok": r.returncode == 0})
