#!/usr/bin/env python3
"""prometheus-skills — CLI para sincronizar skills do registry Prometheus p/ IDEs."""
import argparse
import json
import os
import sys
import urllib.request
from pathlib import Path

API = os.getenv("PROMETHEUS_API", "http://localhost:8777")
TOKEN = os.getenv("PROMETHEUS_TOKEN", "")
SKILLS_DIR = Path.home() / ".config" / "opencode" / "skills"


def _req(path, method="GET", data=None):
    req = urllib.request.Request(
        API + path,
        data=json.dumps(data).encode() if data else None,
        headers={"Authorization": f"Bearer {TOKEN}", "Content-Type": "application/json"},
        method=method,
    )
    with urllib.request.urlopen(req, timeout=15) as r:
        body = r.read().decode()
        try:
            return json.loads(body) if body else {}
        except json.JSONDecodeError:
            return body


def cmd_sync(ide="opencode"):
    skills = _req("/api/skills")["skills"]
    if not skills:
        print("registry vazio")
        return
    dest = {"opencode": SKILLS_DIR, "cursor": Path.home() / ".cursor" / "rules", "vscode": Path.home() / ".vscode" / "skills"}[ide]
    dest.mkdir(parents=True, exist_ok=True)
    n = 0
    for sk in skills:
        raw = _req(f"/api/skills/{sk['name']}/raw")
        f = dest / f"{sk['name']}.md"
        new = raw if isinstance(raw, str) else (raw.get("content") or json.dumps(raw))
        if f.exists() and f.read_text() == new:
            continue
        f.write_text(new)
        n += 1
    print(f"sync: {n} skills atualizadas em {dest} (de {len(skills)} no registry)")


def cmd_list():
    skills = _req("/api/skills")["skills"]
    for sk in skills:
        print(f"  {sk['name']} v{sk['version']} ({sk['source']}) — {sk['description'][:50]}")


def cmd_pull():
    print("pull do GitHub (Camada 2) — implementado via git clone do repo prometheus-memory/skills/")
    print("Use: git clone https://github.com/hofstatter/prometheus-memory /tmp/pm && cp -r /tmp/pm/skills/* ~/.config/opencode/skills/")


def main():
    p = argparse.ArgumentParser(prog="prometheus-skills")
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("sync").add_argument("--ide", default="opencode", choices=["opencode", "cursor", "vscode"])
    sub.add_parser("list")
    sub.add_parser("pull")
    a = p.parse_args()
    if a.cmd == "sync":
        cmd_sync(a.ide)
    elif a.cmd == "list":
        cmd_list()
    elif a.cmd == "pull":
        cmd_pull()


if __name__ == "__main__":
    main()
