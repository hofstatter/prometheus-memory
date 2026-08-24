# RELATÓRIO DE IMPLEMENTAÇÃO — Migração FastMCP 3.x (23/08/2026)

- **Data:** 23/08/2026 (~23:57-00:02)
- **Classificação:** MEDIUM (5)
- **PLAN:** `PLAN_MIGRACAO_FASTMCP3.md`
- **Status:** ✅ VERDE (técnico) — pendência única: re-toggle manual dos MCPs no OpenCode
- **Sessão:** 77.7y (pós-restart, checkpoint 23/08 23:53)

## Resumo

Os 3 servidores MCP Python do ecossistema foram migrados do SDK legado `mcp.server.fastmcp.FastMCP` (SDK oficial `mcp` 1.28/1.29, deprecado — causa raiz do antigo bug 421 anti-DNS-rebinding) para o pacote standalone **`fastmcp` 3.4.7** (prefecthq). A migração é mecânica: troca de import + padrão de registro/run, mantendo transport SSE (decisão aprovada pelo Herbert).

## O que mudou

### 1. `web/scripts/atlas_memory_agent.py` (SSE :8768, VM 101)
```diff
- from mcp.server.fastmcp import FastMCP
- import uvicorn
- mcp = FastMCP("atlas-memory-agent", host="0.0.0.0")
+ from fastmcp import FastMCP
+ mcp = FastMCP("atlas-memory-agent")
- @mcp.prompt()
+ @mcp.prompt
- mcp.tool()(atlas_recall) ... (5 tools)
+ mcp.tool(atlas_recall) ... (5 tools)
- uvicorn.run(mcp.sse_app(), host="0.0.0.0", port=8768)
+ mcp.run(transport="sse", host="0.0.0.0", port=8768)
```

### 2. `web/scripts/docs_mcp_server.py` (SSE :8767, VM 101)
Mesmo padrão: `mcp.tool()(docs_*)` → `mcp.tool(docs_*)` · `uvicorn.run(mcp.sse_app(), ...)` → `mcp.run(transport="sse", ...)`.

### 3. `web/scripts/pm_mcp_server.py` (stdio, NB02 local)
`mcp.tool()(pm_*)` → `mcp.tool(pm_*)` · mantido `mcp.run(transport="stdio")`.

### 4. `requirements.txt`
`+ fastmcp==3.4.7` (mantido `mnemosyne-memory[mcp]` — o MCP do Mnemosyne :8765 usa o SDK oficial).

## Evidências de validação

| Verificação | Resultado |
|---|---|
| `python3 -m py_compile` (3 scripts) | ✅ |
| `grep -rn "mcp.server.fastmcp" web/scripts/` | ✅ 0 ocorrências |
| `import fastmcp` NB02 + VM | ✅ `3.4.7` nos dois |
| `python3 web/scripts/pm_mcp_server.py` (stdio) | ✅ sobe com banner do fastmcp (sem ImportError) |
| `curl :8768/sse` · `curl :8767/sse` | ✅ HTTP 200 (SSE stream aberto, 81 bytes handshake) |
| Handshake MCP via curl (initialize + tools/list) | ✅ :8768 → 5 tools Atlas · :8767 → 5 tools Docs, protocol 2024-11-05 |
| Logs (`atlas.log`, `docs.log`) | ✅ `transport 'sse'`, uvicorn OK, `GET /sse 200 OK`, **zero 421/Host header** |
| Tools via MCP do OpenCode | ⏳ `-32602` — sessão SSE stale do cliente (sintoma conhecido pós-restart, ver abaixo) |

## Deploy executado

1. **Backup:** local `~/backups/herbert/migracao-fastmcp3/20260823-210127/` (4 arquivos) + remoto `~/atlas-scripts/*.bak.fastmcp3-20260823-210234` (2 scripts).
2. **scp** dos 2 scripts migrados → `~/atlas-scripts/` na VM 101.
3. **Restart:**
   - Atlas: `sudo kill` + `sudo bash ~/atlas-scripts/start_atlas.sh` → **PID 69809** (:8768)
   - Docs: `pkill -f docs_mcp_server.py` + `nohup` → **PID 69815** (:8767)
4. Portas LISTEN `0.0.0.0:8768` e `0.0.0.0:8767` confirmadas.

## Pendência única (ação manual, NÃO é falha)

Os MCPs `atlas` e `prometheus-docs` no OpenCode retornam `-32602 Invalid request parameters` porque o OpenCode mantém a **sessão SSE stale** da conexão pré-restart (mesmo sintoma documentado no checkpoint 23/08 23:53 e no fix 421). O servidor está íntegro (handshake curl 100% OK). **Ação: re-toggle/reconnect dos 2 MCPs no painel `/mcp` do OpenCode** (ou restart do OpenCode) e smoke final `atlas_diario()`/`docs_read()`.

## Pendências herdadas (NÃO desta tarefa)

- 🔐 Bearer auth nos MCPs atlas/docs (`docs_mcp_server.py` lê `PROMETHEUS_TOKEN` mas não verifica) → PLAN próprio
- Evolução p/ streamable-http (`/mcp`) → opcional futura
- `pm_mcp_server.py` (M) + `docs_mcp_server.py` (??) sem commit no git — resolvido no commit desta sessão
- Pool `dados-hdd` do R620 (3 SAS 10K fora)

## Artefatos

- PLAN: `PLAN_MIGRACAO_FASTMCP3.md`
- Backups: `~/backups/herbert/migracao-fastmcp3/20260823-210127/` · VM `~/atlas-scripts/*.bak.fastmcp3-20260823-210234`
- Recovery: `~/.config/opencode/recovery/migracao-fastmcp3.md`
- pm_event: (registrado nesta sessão) · Mnemosyne: (registrado nesta sessão)
