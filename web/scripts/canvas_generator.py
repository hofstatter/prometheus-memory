#!/usr/bin/env python3
"""Canvas Generator v2 — Mermaid multi-projeto (flowchart TD + subgraphs).

Fonte: prometheus_project_events (sidecar) agrupado por project_slug.
Fallback: mermaid v1 (cadeia atual) quando não houver eventos — o Canvas nunca
fica vazio. mode_of() distingue "projects" (com subgraph) de "legacy".
"""
import os
import re
import sys
from collections import defaultdict
from pathlib import Path

_WEB_CANDIDATES = [
    Path(__file__).resolve().parent / "web",                    # repo (scripts/canvas_generator.py)
    Path(__file__).resolve().parent.parent / "web",            # producao (web/scripts/canvas_generator.py)
    Path.home() / "Projetos" / "prometheus-memory" / "web",    # cron (~/bin) — fonte de verdade
]
for _wc in _WEB_CANDIDATES:
    if _wc.exists() and str(_wc) not in sys.path:
        sys.path.insert(0, str(_wc))
        break

from prometheus_db import get_conn, init_schema  # noqa: E402

MNEMOSYNE_HOME = Path(os.environ.get("MNEMOSYNE_HOME", Path.home() / ".hermes" / "mnemosyne"))
CANVAS_FILE = MNEMOSYNE_HOME / "canvas.mmd"

MAX_NODES_PER_PROJECT = 5

STATUS_CLASS = {"done": "done", "resolved": "done", "doing": "doing", "blocked": "blocked"}
TYPE_ICON = {"issue": "🚫", "decision": "🧭", "implementation": "⚙️", "research": "🔍", "plan": "📋"}


def _sanitize(text: str, limit: int = 40) -> str:
    s = re.sub(r'["{}()\[\]#*<>|]', ' ', str(text or ''))
    s = re.sub(r"\s+", " ", s).strip()
    return s[:limit] or "noop"


def _sid(slug: str) -> str:
    return re.sub(r"\W", "_", slug).upper()


def mode_of(mermaid: str) -> str:
    return "projects" if "subgraph" in (mermaid or "") else "legacy"


def _load_events() -> tuple:
    init_schema()
    con = get_conn()
    try:
        rows = con.execute(
            "SELECT project_slug, title, event_type, status_hint, agent_id, harness, created_at "
            "FROM prometheus_project_events ORDER BY created_at DESC, id DESC"
        ).fetchall()
        projects = con.execute("SELECT slug, name FROM prometheus_projects").fetchall()
    finally:
        con.close()
    by_slug: dict = defaultdict(list)
    for r in rows:
        by_slug[r["project_slug"]].append(dict(r))
    proj_map = {r["slug"]: (r["name"] or r["slug"]) for r in projects}
    return by_slug, proj_map


def generate(by_slug: dict, proj_map: dict, fallback: str = "") -> str:
    """Mermaid multi-projeto (flowchart TD + subgraphs). Fallback se sem eventos."""
    if not by_slug:
        return fallback

    lines = ["flowchart TD"]
    lines.append("  classDef backlog fill:#94a3b822,stroke:#94a3b8")
    lines.append("  classDef doing fill:#eab30822,stroke:#eab308")
    lines.append("  classDef done fill:#22c55e22,stroke:#22c55e")
    lines.append("  classDef blocked fill:#ef444422,stroke:#ef4444")

    agent_slugs: dict = defaultdict(set)
    for slug, events in sorted(by_slug.items()):
        sid = _sid(slug)
        name = _sanitize(proj_map.get(slug, slug), 30)
        lines.append(f'  subgraph {sid}["{name}"]')
        evs = sorted(events, key=lambda e: e.get("created_at") or "")[:MAX_NODES_PER_PROJECT]
        prev = None
        for i, ev in enumerate(evs):
            nid = f"{_sid(slug)[:8]}{i}"
            cls = STATUS_CLASS.get(ev.get("status_hint") or "", "backlog")
            icon = TYPE_ICON.get(ev.get("event_type"), "•")
            title = _sanitize(ev.get("title"), 40)
            lines.append(f'    {nid}["{icon} {title}"]:::{cls}')
            if prev:
                lines.append(f"    {prev} --> {nid}")
            prev = nid
            if ev.get("agent_id"):
                agent_slugs[ev["agent_id"]].add(slug)
        lines.append("  end")

    seen = set()
    for agent, slugs in agent_slugs.items():
        slugs = sorted(slugs)
        for a, b in zip(slugs, slugs[1:]):
            key = (a, b)
            if key in seen:
                continue
            seen.add(key)
            lines.append(f'  {_sid(a)} -. {_sanitize(agent, 16)} .-> {_sid(b)}')
    return "\n".join(lines)


def _legacy_canvas() -> str:
    try:
        from memory_aggregator import generate_mermaid_canvas
        return generate_mermaid_canvas()
    except Exception:
        return 'flowchart TD\n  Idle["sem eventos"]\n'


def main() -> str:
    """Gera e grava canvas.mmd. Standalone (chamado pelo aggregator e cron)."""
    try:
        by_slug, proj_map = _load_events()
    except Exception:
        by_slug, proj_map = {}, {}
    mmd = generate(by_slug, proj_map, fallback=_legacy_canvas())
    MNEMOSYNE_HOME.mkdir(parents=True, exist_ok=True)
    CANVAS_FILE.write_text(mmd)
    return mmd


if __name__ == "__main__":
    main()
