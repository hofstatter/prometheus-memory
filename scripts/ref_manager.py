#!/usr/bin/env python3
"""
Prometheus Memory — Reference Manager (Offloading de Logs)
Salva outputs grandes de ferramentas em refs/*.md com node_id.
Permite recuperacao por node_id sem poluir o contexto do agente.
Inspirado no TencentDB-Agent-Memory (refs/*.md + node_id tracing).
Uso:
  python3 ref_manager.py save <tool_name> <project> "<content>"
  python3 ref_manager.py load <node_id> [date]
  python3 ref_manager.py format <node_id> <tool_name> "<query>" <char_count>
"""
import sys
import hashlib
from datetime import datetime
from pathlib import Path

REFS_DIR = Path.home() / ".hermes" / "mnemosyne" / "refs"
THRESHOLD_CHARS = 500

def save_ref(tool_name: str, content: str, project: str = "unknown") -> str | None:
    if len(content) <= THRESHOLD_CHARS:
        return None

    node_id = hashlib.blake2b(content.encode(), digest_size=6).hexdigest()
    date_dir = REFS_DIR / datetime.now().strftime("%Y-%m-%d")
    date_dir.mkdir(parents=True, exist_ok=True)

    path = date_dir / f"{tool_name}_{node_id}.md"
    path.write_text(
        f"# {tool_name}\n\n"
        f"**Project:** {project}\n"
        f"**Date:** {datetime.now().isoformat()}\n"
        f"**Node ID:** {node_id}\n"
        f"**Chars:** {len(content)}\n\n"
        f"{content}"
    )
    return node_id

def load_ref(node_id: str, date: str = None) -> str | None:
    if date:
        paths = [REFS_DIR / date]
    else:
        paths = sorted(REFS_DIR.glob("????-??-??"), reverse=True)

    for dir_path in paths:
        if not dir_path.is_dir():
            continue
        for f in dir_path.glob(f"*_{node_id}.md"):
            return f.read_text()
    return None

def format_context_ref(node_id: str, tool_name: str, query: str, char_count: int) -> str:
    kb = char_count / 1024
    short_query = query[:80]
    return f"[ref:{node_id}] {tool_name}: \"{short_query}\" — {kb:.1f}KB offloaded"

if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "help"

    if cmd == "save":
        tool = sys.argv[2]
        project = sys.argv[3] if len(sys.argv) > 3 else "unknown"
        content = sys.argv[4] if len(sys.argv) > 4 else sys.stdin.read()
        nid = save_ref(tool, content, project)
        if nid:
            ref = format_context_ref(nid, tool, project, len(content))
            print(f"NODE_ID={nid}")
            print(f"REF={ref}")
        else:
            print("NODE_ID=none")

    elif cmd == "load":
        nid = sys.argv[2]
        date = sys.argv[3] if len(sys.argv) > 3 else None
        content = load_ref(nid, date)
        if content:
            print(content)
        else:
            print(f"[ref_manager] Node {nid} nao encontrado", file=sys.stderr)
            sys.exit(1)

    elif cmd == "format":
        nid = sys.argv[2]
        tool = sys.argv[3]
        query = sys.argv[4]
        chars = int(sys.argv[5]) if len(sys.argv) > 5 else 0
        print(format_context_ref(nid, tool, query, chars))

    else:
        print("Prometheus Memory — Ref Manager")
        print("  python3 ref_manager.py save <tool_name> <project> '<content>'")
        print("  python3 ref_manager.py load <node_id> [date]")
        print("  echo '<content>' | python3 ref_manager.py save <tool_name> <project>")
