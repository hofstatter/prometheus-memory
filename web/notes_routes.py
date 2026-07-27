"""Prometheus Notes Routes — Hub de captura inteligente."""
import re, os, json, uuid
import ipaddress
import socket
from pathlib import Path
from urllib.parse import urlparse
from datetime import datetime
from flask import Blueprint, request, jsonify
import requests as http

notes_bp = Blueprint('notes', __name__, url_prefix='/api/notes')
NOTES_DIR = Path(os.environ.get("PROMETHEUS_NOTES_DIR", Path.home() / "notes"))
NOTES_DIR.mkdir(parents=True, exist_ok=True)
FIRECRAWL_API_KEY = os.environ.get("FIRECRAWL_API_KEY", "")

def _safe_note_path(note_id: str):
    """Resolve note_id dentro de NOTES_DIR; retorna None se escapar (path traversal)."""
    try:
        p = (NOTES_DIR / note_id).resolve()
        if p == NOTES_DIR.resolve() or NOTES_DIR.resolve() not in p.parents:
            return None
        return p
    except (OSError, ValueError):
        return None

def _is_safe_url(url: str) -> bool:
    """SSRF guard: só http/https e host que não resolva para IP privado/loopback."""
    try:
        parsed = urlparse(url)
        if parsed.scheme not in ("http", "https"):
            return False
        host = parsed.hostname
        if not host:
            return False
        for info in socket.getaddrinfo(host, None):
            ip = ipaddress.ip_address(info[4][0])
            if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved or ip.is_multicast:
                return False
        return True
    except (ValueError, socket.gaierror, OSError):
        return False

SOURCE_DETECTORS = {
    "kimi": ["kimi.com", "moonshot.cn"],
    "x": ["x.com", "twitter.com"],
    "github": ["github.com"],
}

def detect_source(url):
    for source, patterns in SOURCE_DETECTORS.items():
        if any(p in url for p in patterns):
            return source
    return "web"

def _fetch_safe(url: str, headers: dict, max_redirects: int = 5, max_bytes: int = 10_000_000):
    """GET com SSRF guard revalidado a cada redirect e limite de download."""
    current = url
    for _ in range(max_redirects + 1):
        if not _is_safe_url(current):
            raise ValueError("URL bloqueada (redirect para destino nao publico)")
        resp = http.get(current, headers=headers, timeout=15, allow_redirects=False, stream=True)
        if resp.is_redirect or resp.is_permanent_redirect:
            location = resp.headers.get("Location", "")
            if not location:
                raise ValueError("redirect sem Location")
            from urllib.parse import urljoin
            current = urljoin(current, location)
            continue
        chunks, total = [], 0
        for chunk in resp.iter_content(65536, decode_unicode=False):
            total += len(chunk)
            if total > max_bytes:
                raise ValueError("resposta excede 10MB")
            chunks.append(chunk)
        resp.close()
        return resp, b"".join(chunks).decode(resp.encoding or "utf-8", errors="replace")
    raise ValueError("redirects demais")


def extract_from_url(url):
    if not _is_safe_url(url):
        return {"title": url, "text": "URL bloqueada: apenas http(s) públicos são permitidos.", "source": "error"}
    headers = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36"}
    source = detect_source(url)

    try:
        resp, html = _fetch_safe(url, headers)
    except Exception as e:
        return {"title": url, "text": "Erro ao acessar a URL.", "source": "error"}

    if source == "github":
        text_parts = []
        try:
            parsed = urlparse(url)
            repo_path = parsed.path.strip("/")
            if parsed.hostname == "github.com" and repo_path.count("/") >= 1:
                api_url = f"https://api.github.com/repos/{repo_path}/readme"
                r = http.get(api_url, headers=headers, timeout=10)
                if r.status_code == 200:
                    import base64
                    readme = base64.b64decode(r.json().get("content", "")).decode()
                    text_parts.append(f"# README\n\n{readme}")
        except Exception:
            pass
        text_parts.append(_extract_html_text(html))
        return {
            "title": url.rstrip("/").split("/")[-1] or "GitHub",
            "text": "\n\n".join(text_parts)[:50000],
            "source": "github"
        }

    if source == "x":
        return _extract_tweet(html, url)

    text = _extract_html_text(html)
    if len(text) < 200 and FIRECRAWL_API_KEY:
        try:
            r = http.post("https://api.firecrawl.dev/v1/scrape",
                headers={"Authorization": f"Bearer {FIRECRAWL_API_KEY}"},
                json={"url": url, "formats": ["markdown"]}, timeout=30)
            if r.status_code == 200 and r.json().get("success"):
                text = r.json()["data"]["markdown"]
                source = "firecrawl"
        except Exception:
            pass

    title = _extract_title(html) or url
    return {"title": title, "text": text[:50000], "source": source}

def _extract_html_text(html):
    try:
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(html, "lxml")
        for tag in soup(["script", "style", "nav", "footer", "header"]):
            tag.decompose()
        body = soup.find("article") or soup.find("main") or soup.body
        return body.get_text(separator="\n", strip=True) if body else ""
    except Exception:
        return ""

def _extract_title(html):
    m = re.search(r"<title>(.+?)</title>", html, re.IGNORECASE)
    return m.group(1).strip() if m else ""

LIGATURES = {
    "\ufb00": "ff", "\ufb01": "fi", "\ufb02": "fl", "\ufb03": "ffi",
    "\ufb04": "ffl", "\ufb05": "st", "\ufb06": "st",
    "\u2018": "'", "\u2019": "'", "\u201c": '"', "\u201d": '"',
    "\u2013": "-", "\u2014": "—", "\u00a0": " ",
}

def sanitize_markdown(text):
    """Limpa conteúdo extraído: HTML cru, badges, ligaduras, escapes, brancos."""
    if not text:
        return ""
    for lig, rep in LIGATURES.items():
        text = text.replace(lig, rep)
    # Remove tags HTML cruas (div, img, br, p, span, align attrs etc.)
    text = re.sub(r"<img[^>]*>", "", text)
    text = re.sub(r"</?(div|span|br|p|center|figure|picture|source|a)\b[^>]*>", "", text)
    # Linhas de badge/shield: [![...](...)](...) ou [![...](...)]
    text = re.sub(r"^\s*(\[!\[[^\]]*\]\([^)]*\)\]\([^)]*\)|\[!\[[^\]]*\]\([^)]*\)\])\s*$", "", text, flags=re.M)
    # Badges inline remanescentes
    text = re.sub(r"\[!\[[^\]]*\]\([^)]*\)\]\([^)]*\)", "", text)
    # Desescapa markdown (web\_open\_url → web_open_url)
    text = re.sub(r"\\([_*\[\]`#|>-])", r"\1", text)
    # Linhas vazias com só espaços
    text = re.sub(r"^\s+$", "", text, flags=re.M)
    # Colapsa 3+ quebras de linha
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()

def _extract_tweet(html, url):
    blocks = re.findall(r'<script[^>]*type="application/ld\+json"[^>]*>(.*?)</script>', html, re.DOTALL)
    for block in blocks:
        try:
            data = json.loads(block)
            if isinstance(data, dict):
                items = data.get("@graph", [data])
                for item in items:
                    if item.get("@type") == "SocialMediaPosting":
                        author = item.get("author", {})
                        author_name = author.get("name", "") if isinstance(author, dict) else str(author)
                        return {
                            "title": f"X Post — {author_name}",
                            "text": item.get("articleBody", ""),
                            "source": "x",
                            "author": author_name,
                            "date": item.get("datePublished", "")
                        }
        except json.JSONDecodeError:
            continue
    desc = re.findall(r'<meta[^>]*name="description"[^>]*content="([^"]+)"', html)
    text = desc[0] if desc else _extract_html_text(html)
    return {"title": "X Post", "text": text[:50000], "source": "x"}

@notes_bp.get("")
def list_notes():
    notes = []
    for f in sorted(NOTES_DIR.rglob("*.md"), key=lambda x: x.stat().st_mtime, reverse=True)[:50]:
        stat = f.stat()
        content = f.read_text()[:300]
        notes.append({
            "id": f.relative_to(NOTES_DIR).as_posix(),
            "name": f.stem,
            "size": stat.st_size,
            "preview": content[:200],
            "modified": datetime.fromtimestamp(stat.st_mtime).isoformat()
        })
    return jsonify(notes)

@notes_bp.post("/import")
def import_url():
    data = request.get_json() or {}
    url = data.get("url", "").strip()
    if not url:
        return jsonify({"error": "url required"}), 400

    result = extract_from_url(url)
    if result.get("source") == "error":
        return jsonify({"error": result["text"]}), 400
    safe_title = re.sub(r'[^\w\s-]', '', result["title"])[:60].strip()
    filename = f"{safe_title or 'nota'}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"

    cat = result.get("source", "web")
    cat_dir = NOTES_DIR / cat
    cat_dir.mkdir(parents=True, exist_ok=True)
    filepath = cat_dir / filename

    body = sanitize_markdown(result['text'])
    content = f"# {result['title']}\n\n**Fonte:** {url}\n**Extraído em:** {datetime.now().isoformat()}\n**Método:** {result['source']}\n\n{body}"
    filepath.write_text(content)

    return jsonify({
        "id": filepath.relative_to(NOTES_DIR).as_posix(),
        "name": filepath.stem,
        "source": result["source"],
        "size": len(content),
        "url": url
    })

@notes_bp.get("/<path:note_id>")
def get_note(note_id):
    filepath = _safe_note_path(note_id)
    if filepath is None:
        return jsonify({"error": "invalid path"}), 400
    if not filepath.exists() or filepath.suffix != ".md":
        return jsonify({"error": "not found"}), 404
    return jsonify({"id": note_id, "content": filepath.read_text()})

@notes_bp.put("/<path:note_id>")
def update_note(note_id):
    filepath = _safe_note_path(note_id)
    if filepath is None:
        return jsonify({"error": "invalid path"}), 400
    if not filepath.exists() or filepath.suffix != ".md":
        return jsonify({"error": "not found"}), 404
    data = request.get_json() or {}
    content = data.get("content", "")
    if len(content) > 1_000_000:
        return jsonify({"error": "content too large"}), 413
    filepath.write_text(content)
    return jsonify({"ok": True})

@notes_bp.delete("/<path:note_id>")
def delete_note(note_id):
    filepath = _safe_note_path(note_id)
    if filepath is None:
        return jsonify({"error": "invalid path"}), 400
    if not filepath.exists() or filepath.suffix != ".md":
        return jsonify({"error": "not found"}), 404
    filepath.unlink()
    return jsonify({"ok": True})

@notes_bp.post("/search")
def search_notes():
    data = request.get_json() or {}
    query = data.get("query", "").lower().strip()
    if not query:
        return jsonify([])
    results = []
    for f in NOTES_DIR.rglob("*.md"):
        content = f.read_text().lower()
        if query in content:
            idx = content.find(query)
            start = max(0, idx - 100)
            end = min(len(content), idx + len(query) + 200)
            results.append({
                "id": f.relative_to(NOTES_DIR).as_posix(),
                "name": f.stem,
                "snippet": "..." + content[start:end] + "...",
                "score": 100
            })
    return jsonify(results[:10])


@notes_bp.post("/fts")
def fts_notes():
    """Busca FTS5 (rank) nas notas — upgrade do search por substring."""
    data = request.get_json() or {}
    query = (data.get("query") or "").strip()
    if not query:
        return jsonify([])
    import sqlite3
    from pathlib import Path as _P
    db_path = _P(__import__("os").environ.get("PROMETHEUS_DB", _P.home() / ".hermes" / "mnemosyne" / "data" / "mnemosyne.db"))
    db = sqlite3.connect(str(db_path))
    try:
        db.execute("""CREATE VIRTUAL TABLE IF NOT EXISTS notes_fts USING fts5(name, content, tokenize='porter')""")
        for f in NOTES_DIR.rglob("*.md"):
            try:
                db.execute("INSERT INTO notes_fts(name, content) VALUES(?, ?)",
                           (f.relative_to(NOTES_DIR).as_posix(), f.read_text(errors="replace")))
            except Exception:
                continue
        db.commit()
        rows = db.execute(
            "SELECT name, snippet(notes_fts, 1, '<b>', '</b>', '...', 30) FROM notes_fts WHERE notes_fts MATCH ? ORDER BY rank LIMIT 10",
            (query,)
        ).fetchall()
        return jsonify([{"id": r[0], "snippet": r[1]} for r in rows])
    except Exception as e:
        return jsonify({"error": str(e)[:200]}), 500
    finally:
        db.close()
