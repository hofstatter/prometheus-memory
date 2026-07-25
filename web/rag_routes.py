"""Prometheus RAG Routes — Blueprint Flask."""
import os, uuid, sys
from flask import Blueprint, request, jsonify
from werkzeug.utils import secure_filename
from pathlib import Path

_path = Path(__file__).resolve().parent
if str(_path) not in sys.path:
    sys.path.insert(0, str(_path))
from rag_engine import get_engine, MNEMOSYNE_DB, MNEMOSYNE_HOME

rag_bp = Blueprint('rag', __name__, url_prefix='/api/rag')
UPLOAD_DIR = MNEMOSYNE_HOME / "uploads"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
ALLOWED_EXTENSIONS = {".pdf", ".txt", ".md", ".docx", ".png", ".jpg", ".jpeg"}
MAX_UPLOAD_BYTES = 50 * 1024 * 1024

def _engine():
    return get_engine()

@rag_bp.post("/collections")
def create_collection():
    data = request.get_json() or {}
    name = data.get("name", "").strip()
    if not name:
        return jsonify({"error": "name required"}), 400
    eng = _engine()
    cid = eng.create_collection(name, data.get("description", ""))
    return jsonify({"id": cid, "name": name})

@rag_bp.get("/collections")
def list_collections():
    eng = _engine()
    return jsonify(eng.list_collections())

@rag_bp.post("/upload")
def upload_document():
    eng = _engine()
    file = request.files.get("file")
    collection_id = request.form.get("collection_id", "default")
    if not file:
        return jsonify({"error": "no file"}), 400
    if not eng.list_collections():
        eng.create_collection("default", "Default collection")
    filename = secure_filename(file.filename)
    if Path(filename).suffix.lower() not in ALLOWED_EXTENSIONS:
        return jsonify({"error": f"extensão não suportada (use: {', '.join(sorted(ALLOWED_EXTENSIONS))})"}), 400
    filepath = UPLOAD_DIR / f"{uuid.uuid4().hex[:8]}_{filename}"
    file.save(str(filepath))
    try:
        if filepath.stat().st_size > MAX_UPLOAD_BYTES:
            return jsonify({"error": "arquivo excede 50MB"}), 413
        text = eng.extract_file(str(filepath))
        if not text or len(text.strip()) < 10:
            return jsonify({"error": "no text extracted"}), 400
        result = eng.index_text(collection_id, filename, text, "")
        if result:
            return jsonify(result)
        return jsonify({"error": "indexing failed"}), 500
    except Exception as e:
        return jsonify({"error": "falha ao processar documento"}), 500
    finally:
        if filepath.exists():
            filepath.unlink()

@rag_bp.post("/search")
def search():
    data = request.get_json() or {}
    query = data.get("query", "").strip()
    if not query:
        return jsonify([])
    eng = _engine()
    results = eng.search(query, data.get("collection_id"), data.get("top_k", 5))
    return jsonify(results)

@rag_bp.get("/documents")
def list_documents():
    eng = _engine()
    return jsonify(eng.list_documents(request.args.get("collection_id")))

@rag_bp.delete("/documents/<doc_id>")
def delete_document(doc_id):
    eng = _engine()
    eng.delete_document(doc_id)
    return jsonify({"ok": True})

@rag_bp.get("/stats")
def stats():
    eng = _engine()
    return jsonify(eng.stats())
