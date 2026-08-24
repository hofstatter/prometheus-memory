# PLAN — Migração dos MCPs para FastMCP 3.x

- **Data:** 23/08/2026 (~23:57)
- **Classificação:** MEDIUM (5) — 3 arquivos Python + requirements + deploy em produção (VM 101) + reinício de serviços + risco de indisponibilidade dos MCPs de memória
- **Status:** ✅ EXECUTADO E VERDE (ver `RELATORIO_IMPLEMENTACAO_MIGRACAO_FASTMCP3_23AGO2026.md`)
- **Aprovado por:** Herbert (decisões D2/D6 via question no plan mode)

## Objetivo

Eliminar a pendência crônica "migrar servidores p/ `fastmcp.FastMCP` 3.x (SDK legado em deprecação)" dos MCPs Atlas (:8768), Docs (:8767) e PM (stdio local). Os 3 servidores usavam a classe legada `mcp.server.fastmcp.FastMCP` do SDK oficial `mcp` 1.28/1.29 (deprecada; causa raiz do antigo bug 421 anti-DNS-rebinding).

## Decisões técnicas (travadas com o Herbert)

| # | Decisão | Justificativa |
|---|---|---|
| D1 | Usar pacote standalone `fastmcp` (prefecthq), não o SDK oficial `mcp` | Sucessor mantido do `mcp.server.fastmcp` deprecado |
| D2 | **Manter transport `sse`** | `opencode.jsonc` já aponta `/sse` nos remotos → zero mudança de config, menor superfície de risco. Streamable-http fica como evolução futura |
| D3 | Pinar `fastmcp==3.4.7` | Já instalado e validado no `atlas-venv` da VM 101; reproduzibilidade idêntica nos 2 ambientes |
| D4 | **NÃO remover** `mnemosyne-memory[mcp]` do requirements | O MCP do Mnemosyne (:8765) é servidor separado que usa o SDK oficial |
| D5 | Converter `mcp.tool()(fn)` → `mcp.tool(fn)` e `@mcp.prompt()` → `@mcp.prompt` | A forma com parênteses vazios é padrão do SDK 1.x; o fastmcp 3.x usa chamada direta/decorador |
| D6 | **NÃO misturar** com a pendência Bearer auth dos MCPs | Escopo separado (superfície de segurança) — vira PLAN próprio |

## Passos executados

| Passo | Ação | Resultado |
|---|---|---|
| 0 | Backup `backup-before-edit.sh` (4 arquivos) | `~/backups/herbert/migracao-fastmcp3/20260823-210127/` ✅ |
| 0b | Backup remoto VM 101 | `~/atlas-scripts/*.bak.fastmcp3-20260823-210234` ✅ |
| 1 | `requirements.txt` += `fastmcp==3.4.7` | ✅ |
| 2 | `atlas_memory_agent.py` → `main()` migrado | ✅ |
| 3 | `docs_mcp_server.py` → `main()` migrado | ✅ |
| 4 | `pm_mcp_server.py` → `main()` migrado | ✅ |
| 5 | `pip install --user --break-system-packages fastmcp==3.4.7` (NB02) | ✅ (`mcp` 1.28.1 coexistindo) |
| 6 | scp para `~/atlas-scripts/` na VM | ✅ |
| 7 | Restart: atlas PID **69809** (:8768) · docs PID **69815** (:8767) | ✅ LISTEN 0.0.0.0 |
| 8 | Smoke: curl `/sse` 200 · handshake MCP via curl (initialize + tools/list) | ✅ VERDE |

## Critério de aceite

| Critério | Resultado |
|---|---|
| `python3 -m py_compile` dos 3 scripts | ✅ sem erro |
| `grep -rn "mcp.server.fastmcp" web/scripts/` | ✅ zero ocorrências |
| `import fastmcp` = 3.4.7 (NB02 e VM) | ✅ 3.4.7 nos dois |
| `curl :8768/sse` e `:8767/sse` | ✅ HTTP 200 |
| Handshake MCP completo (initialize + tools/list) | ✅ 5+5 tools, protocol 2024-11-05 |
| Sem `Invalid Host header` / 421 | ✅ zero (proteção anti-DNS-rebinding do SDK 1.29 removida) |
| Tools via MCP do OpenCode (`atlas_diario`/`docs_read`) | ⏳ **PENDENTE: re-toggle manual** dos MCPs `atlas` e `prometheus-docs` no painel `/mcp` (sessão SSE stale do OpenCode — sintoma conhecido pós-restart, não é falha da migração) |

## Rollback (se necessário)

```bash
# VM: restaurar backups e reiniciar
cp ~/atlas-scripts/atlas_memory_agent.py.bak.fastmcp3-20260823-210234 ~/atlas-scripts/atlas_memory_agent.py
cp ~/atlas-scripts/docs_mcp_server.py.bak.fastmcp3-20260823-210234 ~/atlas-scripts/docs_mcp_server.py
sudo bash ~/atlas-scripts/start_atlas.sh   # + relançar docs nohup
# Local: restaurar de ~/backups/herbert/migracao-fastmcp3/20260823-210127/ + reverter requirements.txt
```

## Arquivos alterados (backup obrigatório)

- `web/scripts/atlas_memory_agent.py`
- `web/scripts/docs_mcp_server.py`
- `web/scripts/pm_mcp_server.py`
- `requirements.txt`

**Não tocados:** `opencode.jsonc` (mantém SSE), `.env`, `mnemosyne-memory[mcp]`.

## Pendências que NÃO são desta tarefa

- 🔐 Bearer auth nos MCPs atlas/docs (o `docs_mcp_server.py` lê `PROMETHEUS_TOKEN` mas não verifica) — PLAN próprio futuro
- Evolução p/ streamable-http (`/mcp`) — opcional, fase futura
