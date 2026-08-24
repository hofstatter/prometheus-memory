# RELATÓRIO DE IMPLEMENTAÇÃO — Atlas lê/organiza docs .md + gera insights (24/08/2026)

- **Data:** 24/08/2026 (~00:30)
- **Classificação:** MEDIUM (5)
- **PLAN:** `PLAN_ATLAS_DOCS_INSIGHTS.md`
- **Status:** ✅ VERDE — implementado, deployado e smoke-testado com insights reais
- **Sessão:** 77.7z (sequência: 77.7y = migração fastmcp3)

## Resumo

O Atlas (VM 101, :8768) ganhou 2 tools novas que fecham a lacuna "docs → insights": `atlas_docs_index` (varre/indexa `/data/docs` via filesystem direto, idempotente, persiste no diário) e `atlas_docs_insights` (roda DeepSeek em batelada sobre docs filtrados → resumo por doc + temas + links + flags). Sem tocar no `prometheus-docs`, `opencode.jsonc` ou Mnemosyne.

## O que mudou (`web/scripts/atlas_memory_agent.py`, +~95 linhas)

1. **Constantes/helpers:** `DOCS_DIR` (env `DOCS_DIR`, default `/data/docs`), `_DOC_TIPOS` (regex de classificação), `_doc_tipo()`, `_docs_scan()` (rglob + extração path/projeto/tipo/size/first_line/mtime).
2. **`atlas_docs_index()`** — upsert em tabela nova `atlas_docs_index` no diário; retorna contagem por projeto/tipo.
3. **`atlas_docs_insights(projeto="", tipo="", max_docs=10)`** — 1 chamada LLM batelada (truncamento 80 linhas + 4000 chars/doc), parse JSON robusto (`re.search` + fallback), grava entry `kind='insight-docs'` no diário.
4. **`main()`** — registradas as 2 tools (7 tools totais).

## Evidências de validação (smoke via handshake MCP curl)

| Verificação | Resultado |
|---|---|
| `python3 -m py_compile` | ✅ |
| `tools/list` | ✅ **7 tools** (5 antigas + 2 novas) |
| `atlas_docs_index()` | ✅ `total: 137` · `Bytex_AgentOS: 114` · `Documentos: 23` |
| `atlas_docs_insights(projeto="Bytex_AgentOS", max_docs=3)` | ✅ `ok:true, analisados:3` |
| Qualidade dos insights | ✅ 3 resumos precisos (ADMIN_CONSOLE_PLAN, AGENTS, BDI_CHECKLIST) · 5 temas coerentes · 2 links semânticos reais · 2 flags de inconsistência (schema `agentos` sem doc; BDI operacional vs política técnica) |

Exemplo de link gerado: `ADMIN_CONSOLE_PLAN.md ↔ AGENTS.md` — "AGENTS.md define as regras de segurança que devem ser seguidas ao modificar o código do Admin Console."

## Deploy executado

1. **Backup:** local `~/backups/herbert/atlas-docs-insights/20260823-213409/` + remoto `~/atlas-scripts/atlas_memory_agent.py.bak.atlasdocs-20260823-213410`.
2. **scp** → `~/atlas-scripts/`.
3. **Restart:** `sudo kill` + `sudo bash start_atlas.sh` → **PID 71360** (:8768 LISTEN, log limpo, `GET /sse 200 OK`).

## Custo LLM

1 chamada `deepseek-chat` com `max_tokens=3000` → centavos. `atlas_docs_index` é 100% local (zero LLM).

## Pendências herdadas (NÃO desta tarefa)

- 🔐 Bearer auth nos MCPs atlas/docs (docs lê `PROMETHEUS_TOKEN` mas não verifica) → PLAN próprio
- Re-toggle manual dos MCPs `atlas`/`prometheus-docs` no painel `/mcp` do OpenCode (sessão SSE stale pós-restart — sintoma conhecido; servidores íntegros)
- Streamable-http como evolução futura

## Artefatos

- PLAN: `PLAN_ATLAS_DOCS_INSIGHTS.md`
- Backups: `~/backups/herbert/atlas-docs-insights/20260823-213409/` · VM `*.bak.atlasdocs-20260823-213410`
- Recovery: `~/.config/opencode/recovery/atlas-docs-insights.md`
- pm_event: (registrado nesta sessão) · Mnemosyne: (registrado nesta sessão)
