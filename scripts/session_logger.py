#!/usr/bin/env python3
"""
Mnemosyne Memory Palace — Session Logger (L0)
Salva log da sessão OpenCode como Markdown.
Chamado pela auto-memory skill ao final de cada sessão.
"""
import os
from datetime import datetime
from pathlib import Path

SESSION_DIR = Path.home() / ".local/share/opencode/sessions"

def save_session(project: str, summary: str, actions: str, tokens: int = 0):
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    sid = f"session_{ts}"
    path = SESSION_DIR / f"{project}_{sid}.md"
    path.parent.mkdir(parents=True, exist_ok=True)

    actions_list = [a.strip() for a in actions.split(",") if a.strip()]

    path.write_text(f"""# Sessão {project} — {datetime.now().strftime('%d/%m/%Y %H:%M')}

**ID:** {sid}
**Resumo:** {summary}
**Tokens:** {tokens}
**Ações:** {len(actions_list)}

{chr(10).join(f'- {a}' for a in actions_list)}

---
*Sessão capturada automaticamente pelo Mnemosyne Auto-Memory*
""")
    print(f"SID: {sid}")
    return sid

if __name__ == "__main__":
    import sys
    if len(sys.argv) < 3:
        print("Uso: python3 session_logger.py <projeto> <resumo> [ações,separadas,por,virgula] [tokens]")
        sys.exit(1)
    project = sys.argv[1]
    summary = sys.argv[2]
    actions = sys.argv[3] if len(sys.argv) > 3 else ""
    tokens = int(sys.argv[4]) if len(sys.argv) > 4 else 0
    sid = save_session(project, summary, actions, tokens)
    print(sid)
