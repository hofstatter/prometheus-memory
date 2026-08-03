#!/usr/bin/env python3
"""Connections Registry (Fase A2) — chaves API/MCPs/assinaturas por projeto.

- Scan read-only dos .env do projeto: só NOMES + fingerprint SHA-256 (nunca o valor).
- Curadoria manual: billing_type, cost_usd_month, expires_at, provider, notas.
- Alertas: "pago e sem uso" (>30d sem uso) e "expirando" (<30d).
- Chave compartilhada: fingerprint igual em 2+ projetos.
"""
import hashlib
import os
import re
import uuid
from datetime import datetime, timedelta
from pathlib import Path

from prometheus_db import get_conn, init_schema

PROJECTS_ROOT = Path(os.environ.get("PROMETHEUS_PROJECTS_ROOT", str(Path.home() / "Projetos")))
# Diretórios que NUNCA devem ser varridos (produção com secrets): default ~/Projetos/web
_EXCLUDE_DEFAULT = {str((PROJECTS_ROOT / "web").resolve())}
_EXCLUDE_EXTRA = {p.strip() for p in os.environ.get("PROMETHEUS_SCAN_EXCLUDE", "").split(",") if p.strip()}
EXCLUDE_DIRS = _EXCLUDE_DEFAULT | _EXCLUDE_EXTRA

KEY_RE = re.compile(r"(API_?KEY|TOKEN|SECRET|PASSWORD|ACCESS_KEY|CREDENTIAL)", re.IGNORECASE)
UNUSED_DAYS = 30
EXPIRING_DAYS = 30


def _now() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")


def fingerprint(value: str) -> str:
    """Hash do valor — nunca armazenamos o valor bruto."""
    return hashlib.sha256(value.encode("utf-8")).hexdigest()[:16]


def mask(fp: str) -> str:
    return (fp[:6] + "••••") if fp else ""


def _project_dir(slug: str) -> Path | None:
    # repo_path cadastrado (prometheus_projects) tem precedência
    init_schema()
    con = get_conn()
    try:
        row = con.execute("SELECT repo_path FROM prometheus_projects WHERE slug = ?", (slug,)).fetchone()
    finally:
        con.close()
    if row and row["repo_path"]:
        p = Path(row["repo_path"])
        if p.exists():
            return p
    cand = PROJECTS_ROOT / slug
    return cand if cand.exists() else None


def _parse_env(path: Path) -> dict:
    """Lê .env/.env.example (read-only). Retorna {NOME: fingerprint}. Ignora comentários/vazios."""
    out = {}
    try:
        for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, value = line.partition("=")
            key = key.strip()
            value = value.strip().strip('"').strip("'")
            if key and value and KEY_RE.search(key):
                out[key] = fingerprint(value)
    except OSError:
        pass
    return out


def scan_project(slug: str) -> dict:
    """Varre .env/.env.example do projeto e upsert de conexões auto-env (idempotente)."""
    init_schema()
    d = _project_dir(slug)
    if not d:
        return {"project_slug": slug, "scanned": False, "found": 0, "created": 0, "reason": "projeto sem diretorio"}
    if str(d.resolve()) in EXCLUDE_DIRS:
        return {"project_slug": slug, "scanned": False, "found": 0, "created": 0, "reason": "diretorio excluido da varredura"}

    merged: dict = {}
    for fname in (".env", ".env.example"):
        f = d / fname
        if f.exists():
            merged.update(_parse_env(f))

    con = get_conn()
    created = 0
    try:
        for env_var, fp in merged.items():
            exists = con.execute(
                "SELECT 1 FROM prometheus_connections WHERE project_slug = ? AND env_var = ? AND source = 'auto-env'",
                (slug, env_var),
            ).fetchone()
            if exists:
                continue
            con.execute(
                """INSERT INTO prometheus_connections
                   (id, project_slug, kind, name, provider, env_var, fingerprint, billing_type, status, source)
                   VALUES (?,?,?,?,?,?,?,?,?,?)""",
                (uuid.uuid4().hex[:12], slug, "api_key", env_var, env_var.replace("_", " ").title(),
                 env_var, fp, "unknown", "active", "auto-env"),
            )
            created += 1
        con.commit()
    finally:
        con.close()
    return {"project_slug": slug, "scanned": True, "found": len(merged), "created": created}


def list_connections(project_slug=None) -> list:
    init_schema()
    con = get_conn()
    try:
        sql = ("SELECT id, project_slug, kind, name, provider, env_var, fingerprint, billing_type, "
               "cost_usd_month, expires_at, last_used_at, status, source, notes, created_at, updated_at "
               "FROM prometheus_connections")
        params = []
        if project_slug:
            sql += " WHERE project_slug = ?"
            params.append(project_slug)
        sql += " ORDER BY project_slug, kind, name"
        rows = con.execute(sql, params).fetchall()
    finally:
        con.close()

    out = []
    for r in rows:
        item = dict(r)
        item["masked"] = mask(item.get("fingerprint"))
        out.append(item)
    return out


def add_connection(project_slug: str, *, name: str, provider: str = "", kind: str = "api_key",
                   env_var: str = "", billing_type: str = "unknown", cost_usd_month=None,
                   expires_at: str = "", notes: str = "", fingerprint: str = "") -> dict:
    init_schema()
    cid = uuid.uuid4().hex[:12]
    con = get_conn()
    try:
        con.execute(
            """INSERT INTO prometheus_connections
               (id, project_slug, kind, name, provider, env_var, fingerprint, billing_type,
                cost_usd_month, expires_at, status, source, notes)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (cid, project_slug, kind, name, provider, env_var, fingerprint, billing_type,
             float(cost_usd_month) if cost_usd_month is not None else None,
             expires_at or None, "active", "manual", notes),
        )
        con.commit()
    finally:
        con.close()
    return {"id": cid, "project_slug": project_slug}


def update_connection(cid: str, fields: dict) -> bool:
    init_schema()
    # fingerprint/env_var são imutáveis via API (identidade da chave — só o scan/auto define)
    allowed = {"name", "provider", "kind", "billing_type",
               "cost_usd_month", "expires_at", "last_used_at", "status", "notes"}
    sets = []
    params = []
    for k, v in fields.items():
        if k not in allowed:
            continue
        if k == "cost_usd_month" and v is not None and v != "":
            v = float(v)
        sets.append(f"{k} = ?")
        params.append(v if v not in (None, "") else None)
    if not sets:
        return False
    sets.append("updated_at = ?")
    params.append(_now())
    params.append(cid)
    con = get_conn()
    try:
        cur = con.execute(f"UPDATE prometheus_connections SET {', '.join(sets)} WHERE id = ?", params)
        con.commit()
        return cur.rowcount > 0
    finally:
        con.close()


def _shared_with(fp: str, exclude_slug: str) -> list:
    if not fp:
        return []
    init_schema()
    con = get_conn()
    try:
        rows = con.execute(
            "SELECT DISTINCT project_slug FROM prometheus_connections WHERE fingerprint = ? AND project_slug != ?",
            (fp, exclude_slug),
        ).fetchall()
        return [r["project_slug"] for r in rows]
    finally:
        con.close()


def alerts_for(project_slug: str, rows: list | None = None) -> list:
    init_schema()
    now = datetime.now()
    out = []
    if rows is None:
        rows = list_connections(project_slug)
    for c in rows:
        if c["project_slug"] != project_slug:
            continue
        # chave compartilhada
        if c["fingerprint"]:
            shared = _shared_with(c["fingerprint"], project_slug)
            if shared:
                out.append({"id": c["id"], "name": c["name"], "level": "info",
                            "text": f"chave compartilhada com: {', '.join(shared)}"})

        # expirando
        if c["expires_at"]:
            try:
                exp = datetime.strptime(c["expires_at"], "%Y-%m-%d")
                if exp <= now + timedelta(days=EXPIRING_DAYS) and exp > now:
                    out.append({"id": c["id"], "name": c["name"], "level": "warn",
                                "text": f"expira em {exp.strftime('%d/%m/%Y')} — rotacionar"})
            except ValueError:
                pass

        # pago e sem uso (assinatura/paygo sem uso há >30d; nunca usado só após 30d de existência)
        if c["billing_type"] in ("subscription", "paygo"):
            created = c["created_at"] or ""
            last = c["last_used_at"] or ""
            try:
                ref = datetime.strptime(last, "%Y-%m-%d %H:%M:%S.%f") if last else (
                    datetime.strptime(created, "%Y-%m-%d %H:%M:%S.%f") if created else now)
            except ValueError:
                ref = now
            if now - ref > timedelta(days=UNUSED_DAYS):
                out.append({"id": c["id"], "name": c["name"], "level": "error",
                            "text": "pago e sem uso há 30+ dias — revisar assinatura"})
    return out


def summary() -> dict:
    init_schema()
    rows = list_connections()
    by_project: dict = {}
    total_cost = 0.0
    unused = 0
    expiring = 0
    alerts: list = []
    for c in rows:
        cost = c["cost_usd_month"] or 0.0
        if c["billing_type"] in ("subscription", "paygo"):
            total_cost += cost
        by_project.setdefault(c["project_slug"], {"keys": 0, "cost": 0.0})
        by_project[c["project_slug"]]["keys"] += 1
        if c["billing_type"] in ("subscription", "paygo"):
            by_project[c["project_slug"]]["cost"] += cost
        for x in alerts_for(c["project_slug"], rows=rows):
            if x["id"] == c["id"]:
                alerts.append({**x, "project_slug": c["project_slug"]})
                if x["level"] == "error":
                    unused += 1
                elif x["level"] == "warn":
                    expiring += 1
    return {
        "total_cost_usd_month": round(total_cost, 2),
        "unused_keys": unused,
        "expiring_keys": expiring,
        "projects": by_project,
        "alerts": alerts[:50],
    }
