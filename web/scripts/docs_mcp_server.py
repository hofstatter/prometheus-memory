#!/usr/bin/env python3
"""Prometheus Docs MCP (:8767, SSE) — Docs-as-Service para o Atlas e agentes.
Tools: docs_list, docs_read, docs_write, docs_history, docs_revert.
Git-backed em DOCS_DIR (default /data/docs). Auth: Bearer PROMETHEUS_TOKEN.
Padrão: FastMCP + SSE (mesmo do MCP Mnemosyne :8765).
"""
from __future__ import annotations
import os
import subprocess
from pathlib import Path
from datetime import datetime, timezone

DOCS_DIR = Path(os.environ.get("DOCS_DIR", "/data/docs"))
TOKEN = os.environ.get("PROMETHEUS_TOKEN", "")
MAX_BYTES = 1024 * 1024  # 1MB


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _git(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run(["git", *args], cwd=DOCS_DIR, capture_output=True, text=True)


def _ensure_git() -> None:
    DOCS_DIR.mkdir(parents=True, exist_ok=True)
    if not (DOCS_DIR / ".git").exists():
        _git("init")
        _git("config", "user.email", "atlas@prometheus.local")
        _git("config", "user.name", "Atlas")


def _safe_path(path: str) -> Path:
    p = (DOCS_DIR / path).resolve()
    if not str(p).startswith(str(DOCS_DIR.resolve())):
        raise ValueError("path traversal")
    return p


# ---------- tools ----------
def docs_list() -> list:
    """Lista os documentos .md disponíveis (path, size, last_commit)."""
    out = []
    for f in sorted(DOCS_DIR.rglob("*.md")):
        rel = str(f.relative_to(DOCS_DIR))
        commit = _git("log", "-1", "--format=%h %s", "--", rel).stdout.strip()
        out.append({"path": rel, "size": f.stat().st_size, "last_commit": commit})
    return out


def docs_read(path: str, lines: int = 0) -> dict:
    """Lê um documento (opcional: só as primeiras N linhas — bootstrap)."""
    p = _safe_path(path)
    if not p.exists():
        raise ValueError(f"documento não encontrado: {path}")
    content = p.read_text(encoding="utf-8", errors="replace")
    if lines > 0:
        content = "\n".join(content.splitlines()[:lines])
    return {"path": path, "content": content}


def docs_write(path: str, content: str) -> dict:
    """Escreve/substitui um documento (git commit automático)."""
    _ensure_git()
    p = _safe_path(path)
    if len(content.encode("utf-8", "replace")) > MAX_BYTES:
        raise ValueError("documento > 1MB")
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content, encoding="utf-8")
    _git("add", "-A")
    _git("commit", "-m", f"docs: {path} (via Atlas/MCP)")
    h = _git("rev-parse", "--short", "HEAD").stdout.strip()
    return {"ok": True, "path": path, "version": h}


def docs_history(path: str) -> list:
    """Histórico de commits de um documento."""
    _safe_path(path)
    out = _git("log", "--format=%h|%s|%ai", "--", path).stdout.strip()
    return [
        dict(zip(("hash", "message", "timestamp"), line.split("|")))
        for line in out.splitlines() if line
    ]


def docs_revert(path: str, hash: str) -> dict:
    """Reverte um documento para uma versão (hash do commit)."""
    _safe_path(path)
    _git("checkout", hash, "--", path)
    _git("commit", "-m", f"docs: revert {path} para {hash}")
    return {"ok": True, "path": path, "version": hash}


def main() -> int:
    from fastmcp import FastMCP
    mcp = FastMCP("prometheus-docs")
    mcp.tool(docs_list)
    mcp.tool(docs_read)
    mcp.tool(docs_write)
    mcp.tool(docs_history)
    mcp.tool(docs_revert)
    mcp.run(transport="sse", host="0.0.0.0", port=int(os.environ.get("DOCS_MCP_PORT", "8767")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
