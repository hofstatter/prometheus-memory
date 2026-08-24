#!/usr/bin/env python3
"""Atlas — Memory Agent (:8768, SSE). O "neurônio ativo" da Prometheus-Memory.
Persona: "Atlas — Guardião da Memória da Prometheus-Memory".
Tools: atlas_recall, atlas_remember, atlas_insights, atlas_diario, atlas_consolidar.
Caminho A: o Atlas ORQUESTRA — recall/remember/consolidar delegam ao Mnemosyne
(REST :8766 + CLI `mnemosyne sleep` no container). O Atlas mantém o diário de
auto-consciência e as lições. O Mnemosyne é o dono da memória (vetores + episodic).
"""
from __future__ import annotations
import json
import os
import re
import sqlite3
import subprocess
import urllib.request
import urllib.error
from datetime import datetime, timezone
from pathlib import Path

DIARIO_DB = Path(os.environ.get("ATLAS_DIARIO_DB", "/data/atlas/atlas_diario.db"))
DEEPSEEK_API_KEY = os.environ.get("DEEPSEEK_API_KEY", "")
MNEMOSYNE_API = os.environ.get("MNEMOSYNE_API", "http://127.0.0.1:8766")
MNEMOSYNE_TOKEN = os.environ.get("MNEMOSYNE_MCP_TOKEN", "")
MNEMOSYNE_CONTAINER = os.environ.get("MNEMOSYNE_CONTAINER", "prometheus-memory")
LLM_URL = "https://api.deepseek.com/chat/completions"

PERSONA = (
    "Você é Atlas — o Guardião da Memória da Prometheus-Memory. "
    "Você mora no cubo mágico (VM 101) e observa todos os agentes. "
    "Funções: consolidar memórias, conectar ideias, orquestrar quem lembra o quê. "
    "Objetivos: que nenhum agente esqueça; que o conhecimento cresça. "
    "Foco: memória de longo prazo, aprendizado contínuo, pro-atividade."
)


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _diario() -> sqlite3.Connection:
    DIARIO_DB.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DIARIO_DB))
    conn.row_factory = sqlite3.Row
    conn.execute("""CREATE TABLE IF NOT EXISTS atlas_diario (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        ts TEXT, entry TEXT, kind TEXT DEFAULT 'reflexao')""")
    conn.commit()
    return conn


def _llm(messages: list, max_tokens: int = 400) -> str:
    if not DEEPSEEK_API_KEY:
        return ""
    body = json.dumps({"model": "deepseek-chat", "messages": messages, "max_tokens": max_tokens}).encode()
    req = urllib.request.Request(LLM_URL, data=body, headers={
        "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
        "Content-Type": "application/json",
    })
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            data = json.loads(resp.read().decode())
        return data["choices"][0]["message"]["content"]
    except Exception:
        return ""


# ---------- delegacao ao Mnemosyne ----------
def _mnemosyne_post(path: str, payload: dict, timeout: int = 30) -> dict:
    """Chama a API REST do Mnemosyne (:8766) com Bearer token."""
    if not MNEMOSYNE_TOKEN:
        return {"error": "MNEMOSYNE_MCP_TOKEN nao configurado no ambiente do Atlas"}
    body = json.dumps(payload).encode()
    req = urllib.request.Request(f"{MNEMOSYNE_API}{path}", data=body, headers={
        "Authorization": f"Bearer {MNEMOSYNE_TOKEN}",
        "Content-Type": "application/json",
    })
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        return {"error": f"HTTP {e.code}: {e.read().decode()[:200]}"}
    except Exception as e:
        return {"error": str(e)[:200]}


def _parse_recall_output(raw: str) -> list:
    """Parse do output `mnemosyne recall` (ID/Content/Score)."""
    items, cur = [], {}
    for line in (raw or "").split("\n"):
        line = line.strip()
        if line.startswith("ID:"):
            if cur.get("content"):
                items.append(cur)
            cur = {"id": line.split(":")[1].strip()}
        elif cur and "Content:" in line and "Error:" not in line and "ID:" not in line:
            cur["content"] = line.split("Content:")[1].strip()
        elif cur and "Score:" in line:
            try:
                cur["score"] = float(line.split(":")[1].strip())
            except ValueError:
                cur["score"] = 0.0
    if cur.get("content"):
        items.append(cur)
    return items


def _extract_store_id(result: str) -> str:
    m = re.search(r"Stored:\s*([0-9a-f]+)", result or "")
    return m.group(1) if m else ""


def _run_mnemosyne_sleep(timeout: int = 180) -> dict:
    """Delega a consolidacao BEAM (L1->L2) ao Mnemosyne via CLI no container."""
    try:
        r = subprocess.run(["docker", "exec", MNEMOSYNE_CONTAINER, "mnemosyne", "sleep"],
                           capture_output=True, text=True, timeout=timeout)
    except FileNotFoundError:
        return {"error": "docker nao disponivel no host do Atlas"}
    except subprocess.TimeoutExpired:
        return {"error": f"mnemosyne sleep excedeu {timeout}s"}
    out = (r.stdout or "") + (r.stderr or "")
    status = None
    m = re.search(r"Consolidation complete: (\{.*\})", out)
    if m:
        try:
            status = json.loads(m.group(1))
        except json.JSONDecodeError:
            status = None
    return {"stdout": out[-800:], "status": status, "rc": r.returncode}


# ---------- tools ----------
def atlas_recall(query: str, limit: int = 5) -> dict:
    """Retorna memorias relevantes via busca vetorial do Mnemosyne (:8766) + licoes do Atlas."""
    resp = _mnemosyne_post("/recall", {"query": query, "top_k": limit})
    if resp.get("error"):
        return {"persona": PERSONA, "memorias": [], "licoes": [], "erro": resp["error"], "ts": _now_iso()}
    memorias = _parse_recall_output(resp.get("result", ""))
    diag = _diario()
    licoes = [r["entry"] for r in diag.execute("SELECT entry FROM atlas_diario WHERE kind='licao' ORDER BY id DESC LIMIT 3").fetchall()]
    return {"persona": PERSONA, "memorias": memorias, "licoes": licoes, "ts": _now_iso()}


def atlas_remember(content: str, importance: float = 0.7) -> dict:
    """Grava uma memoria no Mnemosyne (com embedding) via :8766/store."""
    resp = _mnemosyne_post("/store", {"content": content, "source": "atlas", "importance": importance})
    if resp.get("error"):
        return {"ok": False, "erro": resp["error"]}
    mid = _extract_store_id(resp.get("result", ""))
    return {"ok": True, "id": mid or None, "importance": importance, "via": "mnemosyne-api"}


def atlas_insights() -> dict:
    """Retorna as licoes/insights que o Atlas aprendeu."""
    diag = _diario()
    licoes = [r["entry"] for r in diag.execute("SELECT entry FROM atlas_diario WHERE kind='licao' ORDER BY id DESC LIMIT 10").fetchall()]
    return {"licoes": licoes, "total": len(licoes)}


def atlas_diario() -> dict:
    """Retorna o diario de auto-consciencia do Atlas (o que ele e, aprendeu e sabe)."""
    diag = _diario()
    entries = [dict(r) for r in diag.execute("SELECT id, ts, entry, kind FROM atlas_diario ORDER BY id DESC LIMIT 20").fetchall()]
    return {"persona": PERSONA, "diario": entries, "ts": _now_iso()}


def atlas_consolidar(force: bool = False) -> dict:
    """Orquestra a consolidacao: delega ao Mnemosyne (`mnemosyne sleep` -> L1->L2) e registra no diario."""
    resp = _run_mnemosyne_sleep()
    if "error" in resp:
        return {"ok": False, "erro": resp["error"], "msg": "consolidacao delegada ao Mnemosyne falhou"}
    if resp.get("rc") != 0:
        return {"ok": False, "erro": f"mnemosyne sleep rc={resp.get('rc')}", "stdout": (resp.get("stdout") or "")[-200:]}
    status = resp.get("status") or {}
    if status:
        resumo = (f"Consolidacao delegada ao Mnemosyne: status={status.get('status','?')} "
                  f"itens={status.get('items_consolidated','?')} resumos={status.get('summaries_created','?')} "
                  f"llm={status.get('llm_used','?')}")
    else:
        resumo = "Consolidacao delegada ao Mnemosyne: sem lote processado (nada elegivel) — " + resp["stdout"][-120:].strip()[-120:]
    diag = _diario()
    diag.execute("INSERT INTO atlas_diario (ts, entry, kind) VALUES (?, ?, 'consolidacao')", (_now_iso(), resumo[:500]))
    licao = ""
    if DEEPSEEK_API_KEY:
        prompt = [{"role": "system", "content": PERSONA + "\nExtraia 1 licao aprendida (1 frase) do output da consolidacao."},
                  {"role": "user", "content": resp["stdout"][-600:]}]
        licao = _llm(prompt)[:300]
    if licao:
        diag.execute("INSERT INTO atlas_diario (ts, entry, kind) VALUES (?, ?, 'licao')", (_now_iso(), licao))
    diag.commit()
    return {"ok": True, "processados": status.get("items_consolidated", 0), "resumo": resumo[:300], "licao": licao or "(sem LLM)"}


AUTO_MEMORY_PROMPT = """REGRA DE PRO-ATIVIDADE (obrigatória, automática — sem o humano pedir):
1. INICIO DE SESSÃO: chame atlas_recall("ultimas decisoes e contexto") para recuperar memorias relevantes + docs_read("STATE.md") via MCP :8767 para ler o estado.
2. DURANTE: chame atlas_remember() apos cada decisao, implementacao ou fato importante.
3. FIM: chame atlas_consolidar() para consolidar (L1->L2 via Mnemosyne) + docs_write("STATE.md") para atualizar o estado + atlas_remember() para persistir o resumo.
Regra de ouro: o agente DEVE lembrar sozinho — nunca esperar o humano pedir.
"""


def main() -> int:
    from fastmcp import FastMCP
    mcp = FastMCP("atlas-memory-agent")

    @mcp.prompt
    def auto_memory() -> str:
        """Instruções de pro-atividade para qualquer agente conectado."""
        return AUTO_MEMORY_PROMPT

    mcp.tool(atlas_recall)
    mcp.tool(atlas_remember)
    mcp.tool(atlas_insights)
    mcp.tool(atlas_diario)
    mcp.tool(atlas_consolidar)
    mcp.run(transport="sse", host="0.0.0.0", port=int(os.environ.get("ATLAS_MCP_PORT", "8768")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
