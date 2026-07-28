"""Prometheus Skill Registry — Camada 1 (privada, sua "oficina" de skills).

Skills ficam no registry local (SQLite). Você insere/edita pela UI. IDEs sincronizam
via /api/skills/<name>/download. Publicar na Camada 2 (GitHub) é opcional e explícito.
"""
import hashlib
import sqlite3
import time
from pathlib import Path

import os as _os
DB_PATH = Path(_os.environ.get(
    "PROMETHEUS_DB",
    str(Path.home() / ".hermes" / "mnemosyne" / "data" / "mnemosyne.db"),
))


def _db():
    con = sqlite3.connect(str(DB_PATH), timeout=10)
    con.execute("PRAGMA busy_timeout=5000")
    con.execute("""
        CREATE TABLE IF NOT EXISTS skills (
            name TEXT PRIMARY KEY,
            version INTEGER DEFAULT 1,
            description TEXT DEFAULT '',
            content TEXT NOT NULL,
            roles_json TEXT DEFAULT '[]',
            source TEXT DEFAULT 'local',
            checksum TEXT DEFAULT '',
            created_at TEXT DEFAULT (datetime('now')),
            updated_at TEXT DEFAULT (datetime('now'))
        )
    """)
    con.commit()
    return con


def _checksum(content: str) -> str:
    return hashlib.sha256(content.encode()).hexdigest()[:12]


def list_skills() -> list:
    con = _db()
    rows = con.execute(
        "SELECT name, version, description, source, checksum, updated_at FROM skills ORDER BY updated_at DESC"
    ).fetchall()
    con.close()
    return [{"name": r[0], "version": r[1], "description": r[2], "source": r[3], "checksum": r[4], "updated_at": r[5]} for r in rows]


def get_skill(name: str) -> dict | None:
    con = _db()
    row = con.execute("SELECT name, version, description, content, roles_json, source, checksum, created_at, updated_at FROM skills WHERE name=?", (name,)).fetchone()
    con.close()
    if not row:
        return None
    return {"name": row[0], "version": row[1], "description": row[2], "content": row[3], "roles_json": row[4],
            "source": row[5], "checksum": row[6], "created_at": row[7], "updated_at": row[8]}


def upsert_skill(name: str, content: str, description: str = "", roles_json: str = "[]", source: str = "local") -> dict:
    con = _db()
    existing = con.execute("SELECT version FROM skills WHERE name=?", (name,)).fetchone()
    version = (existing[0] + 1) if existing else 1
    chk = _checksum(content)
    con.execute(
        """INSERT INTO skills(name, version, description, content, roles_json, source, checksum, updated_at)
           VALUES(?,?,?,?,?,?,?,datetime('now'))
           ON CONFLICT(name) DO UPDATE SET version=?, description=?, content=?, roles_json=?, source=?, checksum=?, updated_at=datetime('now')""",
        (name, version, description, content, roles_json, source, chk, version, description, content, roles_json, source, chk)
    )
    con.commit()
    con.close()
    return {"name": name, "version": version, "checksum": chk}


def delete_skill(name: str) -> bool:
    con = _db()
    cur = con.execute("DELETE FROM skills WHERE name=?", (name,))
    con.commit()
    n = cur.rowcount
    con.close()
    return n > 0
