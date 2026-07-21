#!/usr/bin/env python3
"""
Prometheus Memory — Memory Aggregator (L1->L2)
Consolida fatos L1 em cenas L2 por projeto + gera Mermaid Canvas.
Executado via cron a cada 6h.
"""
import subprocess
import os
import re
import json
import requests as http
from datetime import datetime
from collections import defaultdict
from pathlib import Path

DEEPSEEK_KEY = os.environ.get("DEEPSEEK_API_KEY", "")
LOG_DIR = Path.home() / ".local" / "log"
CANVAS_DIR = Path.home() / ".hermes" / "mnemosyne"
CANVAS_FILE = CANVAS_DIR / "canvas.mmd"

def run_mnemosyne(*args, timeout=30):
    result = subprocess.run(
        ["mnemosyne"] + list(args),
        capture_output=True, text=True, timeout=timeout
    )
    return result.stdout

def get_recent_memories(limit: int = 50) -> list:
    output = run_mnemosyne("recall", "implementacao decisao config sessao instalacao correcao plano", str(limit))
    memories = []
    current = None
    for line in output.split("\n"):
        if line.startswith("  ID:"):
            current = {"id": line.split(":")[1].strip()}
        elif current and "Content:" in line:
            current["content"] = line.split("Content:")[1].strip()
        elif current and "Score:" in line:
            try:
                current["score"] = float(line.split(":")[1].strip())
            except ValueError:
                current["score"] = 0.0
            if current.get("content"):
                memories.append(current)
            current = None
    return memories

def group_by_project(memories: list) -> dict:
    groups = defaultdict(list)
    for m in memories:
        content = m.get("content", "")
        matches = re.findall(r'\[(\w+)\]', content)
        project = next((pm for pm in matches if pm.lower() not in ("unknown", "unk")), os.environ.get("PROMETHEUS_PROJECT", "default"))
        groups[project].append(m)
    return dict(groups)

def synthesize_scene_with_llm(project: str, memories: list) -> str:
    if len(memories) < 2:
        return None
    if not DEEPSEEK_KEY:
        facts_str = "; ".join(m["content"][:80] for m in memories[:5])
        return f"[{project}] cena-sessao {len(memories)} fatos-recentes: {facts_str[:400]}"
    facts = "\n".join(f"- {m['content'][:300]}" for m in memories[:10])
    prompt = f"""Resuma estes fatos em uma cena tematica concisa (max 100 palavras).
Use portugues brasileiro. Formato: "[{project}] cena [tema-resumido]: [descricao]"

Fatos:
{facts}
"""
    try:
        resp = http.post(
            "https://api.deepseek.com/chat/completions",
            headers={"Authorization": f"Bearer {DEEPSEEK_KEY}"},
            json={
                "model": "deepseek-chat",
                "messages": [{"role": "user", "content": prompt}],
                "max_tokens": 200,
                "temperature": 0.3
            },
            timeout=30
        )
        scene = resp.json()["choices"][0]["message"]["content"].strip()
        return scene
    except Exception as e:
        facts_str = "; ".join(m["content"][:80] for m in memories[:5])
        return f"[{project}] cena-sessao {len(memories)} fatos-recentes: {facts_str[:400]}"

def create_scene(project: str, memories: list):
    if len(memories) < 2:
        return None
    scene = synthesize_scene_with_llm(project, memories)
    if not scene:
        return None
    full_text = f"{scene} — {datetime.now().strftime('%d/%m/%Y')}"
    r = subprocess.run(
        ["mnemosyne", "remember", full_text, "--importance", "0.7", "--source", "memory-aggregator"],
        capture_output=True, text=True, timeout=15
    )
    return full_text if r.returncode == 0 else None

def generate_mermaid_canvas():
    output = run_mnemosyne("recall", "tool execution result web_search web_scrape", "30")
    transitions = []
    current_id = None
    current_content = None
    for line in output.split("\n"):
        if line.startswith("  ID:"):
            current_id = line.split(":")[1].strip()
        elif current_id and "Content:" in line:
            current_content = line.split("Content:")[1].strip()
            if current_content:
                transitions.append({"id": current_id, "content": current_content})
            current_id = None

    if not transitions:
        mmd = f"stateDiagram-v2\n    [*] --> Idle\n    note right of Idle: Nenhuma atividade recente\n    Idle --> [*]\n"
        CANVAS_FILE.write_text(mmd)
        return mmd

    mmd = "stateDiagram-v2\n    [*] --> Start\n"
    prev_state = "Start"
    count = 0
    for t in transitions[:15]:
        tid = t["id"][:6]
        content = t["content"][:120].replace('"', "'").replace('(', '[').replace(')', ']').replace('#', '').replace('{', '[').replace('}', ']')
        action = extract_action(content)
        state = f"S{count}"
        mmd += f"    {prev_state} --> {state}: {action}\n"
        if len(content) > 40:
            short = content[:80]
            mmd += f"    note right of {state}: {short}\n"
        prev_state = state
        count += 1
    mmd += f"    {prev_state} --> [*]: Concluido\n"

    CANVAS_DIR.mkdir(parents=True, exist_ok=True)
    CANVAS_FILE.write_text(mmd)
    return mmd

def extract_action(content: str) -> str:
    actions = {
        "web_search": "buscar", "web_scrape": "extrair", "web_crawl": "varrer",
        "search_drive": "drive", "upload_to_drive": "upload",
        "slack_read": "slack", "implementacao": "implementar",
        "correcao": "corrigir", "config": "configurar", "decisao": "decidir"
    }
    for key, label in actions.items():
        if key in content.lower():
            return label
    return "processar"

if __name__ == "__main__":
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    log_path = LOG_DIR / "prometheus-aggregator.log"
    ts = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    print(f"[{ts}] Aggregator running...")

    memories = get_recent_memories()
    if not memories:
        msg = f"[{ts}] Nenhuma memoria recente encontrada."
        print(msg)
        with open(log_path, "a") as f:
            f.write(msg + "\n")
        exit(0)

    groups = group_by_project(memories)
    total_scenes = 0
    for project, mems in groups.items():
        scene = create_scene(project, mems)
        if scene:
            total_scenes += 1
            print(f"  [{project}] {len(mems)} fatos -> cena criada")

    canvas = generate_mermaid_canvas()
    print(f"  Canvas Mermaid gerado ({len(canvas)} chars)")

    msg = f"[{ts}] {total_scenes} cenas criadas de {len(groups)} projetos, canvas atualizado."
    print(f"Done: {total_scenes} scenes, {len(groups)} projects")
    with open(log_path, "a") as f:
        f.write(msg + "\n")
