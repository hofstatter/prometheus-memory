#!/usr/bin/env python3
"""Tech Profile (Fase A3) — Stack & Runtime por projeto.

Análise por bytes (estilo GitHub linguist) + frameworks (manifests) + DBs
(compose/DATABASE_URL) + containers (docker ps) + git (read-only).
Resultado cacheado em prometheus_tech_profile — re-scan sob demanda.
"""
import json
import os
import re
import subprocess
import time
from datetime import datetime
from pathlib import Path

from prometheus_db import get_conn, init_schema

PROJECTS_ROOT = Path(os.environ.get("PROMETHEUS_PROJECTS_ROOT", str(Path.home() / "Projetos")))
_EXCLUDE_DIRNAMES = {"node_modules", ".next", "dist", "build", "__pycache__", ".git",
                     "venv", ".venv", "docker-volumes", ".cache", ".nuxt", ".output",
                     "target", ".tox", ".pytest_cache", "coverage"}

EXT_LANG = {
    ".py": "Python", ".ts": "TypeScript", ".tsx": "TypeScript", ".js": "JavaScript",
    ".jsx": "JavaScript", ".html": "HTML", ".css": "CSS", ".scss": "SCSS",
    ".sql": "SQL", ".sh": "Shell", ".go": "Go", ".rs": "Rust", ".java": "Java",
    ".rb": "Ruby", ".php": "PHP", ".c": "C", ".h": "C", ".cpp": "C++",
    ".hpp": "C++", ".vue": "Vue", ".svelte": "Svelte", ".astro": "Astro",
}
_DOC_EXT = {".md", ".rst", ".txt"}
_CONFIG_EXT = {".json", ".yml", ".yaml", ".toml", ".ini", ".cfg", ".lock"}

FRAMEWORK_DEPS = {
    "next": "Next.js", "react": "React", "vue": "Vue", "nuxt": "Nuxt",
    "svelte": "Svelte", "angular": "Angular", "express": "Express",
    "fastify": "Fastify", "prisma": "Prisma", "tailwindcss": "Tailwind CSS",
    "django": "Django", "flask": "Flask", "fastapi": "FastAPI",
    "sqlalchemy": "SQLAlchemy", "pydantic": "Pydantic", "tensorflow": "TensorFlow",
    "pytorch": "PyTorch", "transformers": "Hugging Face", "gunicorn": "Gunicorn",
    "uvicorn": "Uvicorn", "next-auth": "NextAuth", "typeorm": "TypeORM",
}
DB_IMAGES = {
    "postgres": "PostgreSQL", "mysql": "MySQL", "mariadb": "MariaDB",
    "redis": "Redis", "meilisearch": "Meilisearch", "mongo": "MongoDB",
    "minio": "MinIO", "clickhouse": "ClickHouse", "sqlite": "SQLite",
}


def _now() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")


def _project_dir(slug: str) -> Path | None:
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
    cand = (PROJECTS_ROOT / slug).resolve()
    root = PROJECTS_ROOT.resolve()
    return cand if cand.exists() and cand.is_relative_to(root) else None


def _walk_code(d: Path) -> tuple[dict, int, int]:
    """Retorna ({lang: bytes}, docs_bytes, config_bytes). Ignora dirs excluídos."""
    langs: dict = {}
    docs = config = 0
    for root, dirs, files in os.walk(d):
        dirs[:] = [x for x in dirs if x not in _EXCLUDE_DIRNAMES]
        for fname in files:
            ext = Path(fname).suffix.lower()
            fp = Path(root) / fname
            try:
                size = fp.stat().st_size
            except OSError:
                continue
            if ext in _DOC_EXT:
                docs += size
            elif ext in _CONFIG_EXT:
                config += size
            elif ext in EXT_LANG:
                langs[EXT_LANG[ext]] = langs.get(EXT_LANG[ext], 0) + size
    return langs, docs, config


def _languages_percent(langs: dict) -> list:
    total = sum(langs.values())
    if not total:
        return []
    return [{"language": lang, "percent": round(bytes_ / total * 100, 1)}
            for lang, bytes_ in sorted(langs.items(), key=lambda kv: -kv[1])]


def _frameworks(d: Path) -> list:
    """Manifests na raiz + subdiretórios de 1º nível (monorepo-aware)."""
    found = {}
    scan_dirs = [d] + [c for c in d.iterdir() if c.is_dir() and c.name not in _EXCLUDE_DIRNAMES]
    for base in scan_dirs:
        pkg = base / "package.json"
        if pkg.exists():
            try:
                data = json.loads(pkg.read_text(encoding="utf-8", errors="replace"))
                deps = {**(data.get("dependencies") or {}), **(data.get("devDependencies") or {})}
                for dep, ver in deps.items():
                    fw = FRAMEWORK_DEPS.get(dep.split("/")[-1])
                    if fw:
                        found.setdefault(fw, ver.lstrip("^~"))
            except Exception:
                pass
        for manifest, pat in (("requirements.txt", r"^([a-zA-Z0-9_\-\.]+)"),
                              ("pyproject.toml", r"^([a-zA-Z0-9_\-\.]+)\s*=")):
            f = base / manifest
            if not f.exists():
                continue
            try:
                for line in f.read_text(encoding="utf-8", errors="replace").splitlines():
                    line = line.strip()
                    if not line or line.startswith(("#", "-", "[", "]")):
                        continue
                    m = re.match(pat, line)
                    if not m:
                        continue
                    fw = FRAMEWORK_DEPS.get(m.group(1).strip().lower())
                    if fw:
                        found.setdefault(fw, "")
            except Exception:
                pass
    return [{"name": n, "version": v or ""} for n, v in sorted(found.items())]


def _databases(d: Path) -> list:
    dbs = set()
    compose = d / "docker-compose.yml"
    if not compose.exists():
        compose = d / "docker-compose.yaml"
    if compose.exists():
        try:
            text = compose.read_text(encoding="utf-8", errors="replace")
            for img, label in DB_IMAGES.items():
                if re.search(rf"image:\s*[^\n]*{img}", text):
                    dbs.add(label)
        except OSError:
            pass
    for env_f in (d / ".env", d / ".env.example"):
        if env_f.exists():
            try:
                text = env_f.read_text(encoding="utf-8", errors="replace")
                m = re.search(r"DATABASE_URL=(\w+)://", text)
                if m:
                    scheme = m.group(1).lower()
                    for img, label in DB_IMAGES.items():
                        if scheme.startswith(img):
                            dbs.add(label)
            except OSError:
                pass
    return sorted(dbs)


def _git_info(d: Path) -> dict:
    def _run(*args):
        try:
            r = subprocess.run(["git", "-C", str(d)] + list(args), capture_output=True,
                               text=True, timeout=6)
            return r.stdout.strip() if r.returncode == 0 else ""
        except (subprocess.SubprocessError, OSError):
            return ""

    if not _run("rev-parse", "--is-inside-work-tree"):
        return {"tracked": False}
    dirty = _run("status", "--porcelain")
    log = _run("log", "--oneline", "-5")
    return {
        "tracked": True,
        "branch": _run("symbolic-ref", "--short", "HEAD") or _run("rev-parse", "--abbrev-ref", "HEAD"),
        "remote": _run("remote", "get-url", "origin"),
        "dirty_count": len([x for x in dirty.splitlines() if x.strip()]),
        "commits": [c for c in log.splitlines() if c.strip()][:5],
    }


def _containers(slug: str, d: Path) -> list:
    prefix = slug.lower()
    dirname = d.name.lower()
    try:
        r = subprocess.run(["docker", "ps", "--format", "{{.Names}}\t{{.Status}}\t{{.Ports}}"],
                           capture_output=True, text=True, timeout=6)
        out = []
        for line in r.stdout.splitlines():
            if not line.strip():
                continue
            parts = line.split("\t")
            name = parts[0]
            if prefix in name.lower() or dirname in name.lower():
                out.append({"name": name, "status": parts[1] if len(parts) > 1 else "",
                            "ports": parts[2] if len(parts) > 2 else ""})
        return out
    except (subprocess.SubprocessError, OSError):
        return []


def _systemd_services(slug: str, d: Path) -> list:
    """Serviços systemd user cujo nome referencia o projeto (ex.: prometheus-*) — usado
    quando o projeto roda local (systemd) em vez de Docker. Read-only."""
    prefix = slug.lower().replace("_", "-")
    dirname = d.name.lower().replace("_", "-")
    roots = {prefix.split("-")[0], dirname.split("-")[0]}
    try:
        r = subprocess.run(
            ["systemctl", "--user", "list-units", "--type=service", "--state=running",
             "--no-legend", "--plain"],
            capture_output=True, text=True, timeout=6,
        )
        out = []
        for line in r.stdout.splitlines():
            parts = line.split()
            if not parts:
                continue
            unit = parts[0].lower()
            unit_root = unit.split("-")[0] if "-" in unit else unit.removesuffix(".service")
            # match restrito: prefixo exato + separador (evita falso-positivo 'backup-prometheus')
            match = (
                unit.startswith(prefix + "-") or unit.startswith(prefix + ".")
                or unit.startswith(prefix + "@") or unit.startswith(dirname + "-")
                or (unit_root in roots and unit_root != "system")
            )
            if match:
                name = parts[0].removesuffix(".service")
                status = " ".join(parts[1:3]) if len(parts) > 2 else "running"
                out.append({"name": name, "status": status})
        return out
    except (subprocess.SubprocessError, OSError):
        return []


def scan_project(slug: str) -> dict:
    init_schema()
    start = time.time()
    d = _project_dir(slug)
    if not d:
        return {"project_slug": slug, "scanned": False, "reason": "projeto sem diretorio"}
    langs, docs_bytes, config_bytes = _walk_code(d)
    containers = _containers(slug, d)
    systemd_services = _systemd_services(slug, d) if not containers else []
    profile = {
        "languages": _languages_percent(langs),
        "docs_bytes": docs_bytes,
        "config_bytes": config_bytes,
        "frameworks": _frameworks(d),
        "databases": _databases(d),
        "git": _git_info(d),
        "containers": containers,
        "systemd_services": systemd_services,
    }
    duration_ms = int((time.time() - start) * 1000)
    con = get_conn()
    try:
        con.execute(
            """INSERT INTO prometheus_tech_profile
               (project_slug, repo_path, languages_json, frameworks_json, databases_json,
                containers_json, systemd_json, git_json, analyzed_at, scan_duration_ms)
               VALUES (?,?,?,?,?,?,?,?,?,?)
               ON CONFLICT(project_slug) DO UPDATE SET
                 repo_path=excluded.repo_path, languages_json=excluded.languages_json,
                 frameworks_json=excluded.frameworks_json, databases_json=excluded.databases_json,
                 containers_json=excluded.containers_json, systemd_json=excluded.systemd_json,
                 git_json=excluded.git_json,
                 analyzed_at=excluded.analyzed_at, scan_duration_ms=excluded.scan_duration_ms""",
            (slug, str(d), json.dumps(profile["languages"]), json.dumps(profile["frameworks"]),
             json.dumps(profile["databases"]), json.dumps(profile["containers"]),
             json.dumps(profile["systemd_services"]),
             json.dumps(profile["git"]), _now(), duration_ms),
        )
        con.commit()
    finally:
        con.close()
    profile["project_slug"] = slug
    profile["scanned"] = True
    profile["scan_duration_ms"] = duration_ms
    profile["docs_bytes"] = docs_bytes
    profile["config_bytes"] = config_bytes
    return profile


def get_profile(slug: str) -> dict | None:
    init_schema()
    con = get_conn()
    try:
        row = con.execute(
            "SELECT project_slug, repo_path, languages_json, frameworks_json, databases_json, "
            "containers_json, systemd_json, git_json, analyzed_at, scan_duration_ms "
            "FROM prometheus_tech_profile WHERE project_slug = ?",
            (slug,),
        ).fetchone()
    finally:
        con.close()
    if not row:
        return None
    return {
        "project_slug": row["project_slug"],
        "repo_path": row["repo_path"],
        "languages": json.loads(row["languages_json"] or "[]"),
        "frameworks": json.loads(row["frameworks_json"] or "[]"),
        "databases": json.loads(row["databases_json"] or "[]"),
        "containers": json.loads(row["containers_json"] or "[]"),
        "systemd_services": json.loads(row["systemd_json"] or "[]"),
        "git": json.loads(row["git_json"] or "{}"),
        "analyzed_at": row["analyzed_at"],
        "scan_duration_ms": row["scan_duration_ms"],
    }
