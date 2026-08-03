"""Testes Fase A3 — Stack & Runtime: linguagens %, frameworks, DBs, git (read-only).

Env isolado por teste (monkeypatch). Containers/docker não são testados (indisponível em CI).
"""
import importlib
import os
import subprocess
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "web"))

_ROOT = Path("/tmp/test-stack-root")
_PROJ = _ROOT / "meuapp"
for sub in ("src", "templates"):
    (_PROJ / sub).mkdir(parents=True, exist_ok=True)
(_PROJ / "src" / "main.py").write_text("# " + "x" * 600)
(_PROJ / "src" / "util.py").write_text("# " + "y" * 200)
(_PROJ / "templates" / "index.html").write_text("<p>" + "h" * 200)
(_PROJ / "package.json").write_text('{"dependencies": {"next": "^16.0.0", "react": "19.2.4", "prisma": "^6.0.0"}}')
(_PROJ / "requirements.txt").write_text("fastapi\nuvicorn\n")
(_PROJ / "docker-compose.yml").write_text(
    "services:\n  db:\n    image: postgres:16-alpine\n  cache:\n    image: redis:7-alpine\n"
)
(_PROJ / "README.md").write_text("# " + "d" * 500)
try:
    subprocess.run(["git", "init", "-q", str(_PROJ)], timeout=10, check=True)
    subprocess.run(["git", "-C", str(_PROJ), "add", "-A"], timeout=10, check=True)
    subprocess.run(["git", "-C", str(_PROJ), "-c", "user.email=t@t", "-c", "user.name=t",
                    "commit", "-qm", "init"], timeout=10, check=True)
    GIT_OK = True
except Exception:
    GIT_OK = False


@pytest.fixture(autouse=True)
def _env(monkeypatch):
    monkeypatch.setenv("PROMETHEUS_DB", "/tmp/test-stack.db")
    monkeypatch.setenv("PROMETHEUS_PROJECTS_ROOT", str(_ROOT))
    if os.path.exists("/tmp/test-stack.db"):
        os.remove("/tmp/test-stack.db")
    for mod in ("prometheus_db", "tech_profile"):
        importlib.reload(importlib.import_module(mod))
    importlib.import_module("prometheus_db").init_schema()
    yield


def _reg():
    return importlib.import_module("tech_profile")


def test_s1_languages_percent():
    prof = _reg().scan_project("meuapp")
    langs = {l["language"]: l["percent"] for l in prof["languages"]}
    assert langs.get("Python", 0) > 50, f"Python deveria dominar: {langs}"
    assert "HTML" in langs
    total = sum(langs.values())
    assert abs(total - 100.0) < 1.5, f"soma dos percentuais ~100: {total}"
    assert prof["docs_bytes"] >= 500, "docs (README.md) deveriam ser contados separados"


def test_s2_frameworks_and_dbs():
    prof = _reg().scan_project("meuapp")
    fw = {f["name"] for f in prof["frameworks"]}
    assert {"FastAPI", "Next.js", "Prisma"} <= fw, f"frameworks esperados: {fw}"
    assert {"PostgreSQL", "Redis"} <= set(prof["databases"]), prof["databases"]


def test_s3_git_tracked():
    if not GIT_OK:
        pytest.skip("git indisponível no ambiente")
    prof = _reg().scan_project("meuapp")
    assert prof["git"]["tracked"] is True
    assert prof["git"]["branch"]
    assert prof["git"]["commits"], "deveria ter ao menos 1 commit"
    assert isinstance(prof["git"]["dirty_count"], int)


def test_s4_not_a_repo():
    plain = _ROOT / "semgit"
    plain.mkdir(exist_ok=True)
    (plain / "x.py").write_text("# x")
    prof = _reg().scan_project("semgit")
    assert prof["git"]["tracked"] is False


def test_s5_cache_and_get():
    _reg().scan_project("meuapp")
    cached = _reg().get_profile("meuapp")
    assert cached and cached["languages"] and cached["databases"]
    assert _reg().get_profile("nao-existe") is None
