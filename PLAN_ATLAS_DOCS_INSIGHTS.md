# PLAN — Atlas lê/organiza docs `.md` + gera insights

- **Data:** 24/08/2026 (~00:30)
- **Classificação:** MEDIUM (5)
- **Status:** ✅ EXECUTADO E VERDE (ver `RELATORIO_IMPLEMENTACAO_ATLAS_DOCS_INSIGHTS_23AGO2026.md`)
- **Aprovado por:** Herbert (decisões D1/D2 via question no plan mode)

## Objetivo

Fechar a lacuna: o Atlas não lia `/data/docs` (quem lia era o `prometheus-docs` :8767). Adicionar ao Atlas 2 tools novas que varrem, indexam e geram insights dos `.md` — **sem tocar** no `prometheus-docs`, `opencode.jsonc` ou Mnemosyne.

## Decisões técnicas (travadas com o Herbert)

| # | Decisão | Justificativa |
|---|---|---|
| D1 | **Filesystem direto** `/data/docs` (rglob) | Atlas e docs rodam na **mesma VM 101**; Atlas já usa `Path`/`sqlite3` direto (diário). Sem HTTP, sem acoplar ao protocolo MCP do docs |
| D2 | **Resumo + temas + links** (1 chamada LLM batelada) | Custo ~centavos por chamada; cobre o pedido sem ler 150 docs individualmente |
| D3 | Persistir no **diário do Atlas** (tabela nova `atlas_docs_index` + entries `kind='insight-docs'`) | O diário já é a memória de auto-consciência do Atlas; sem dependência nova |
| D4 | **Truncar conteúdo** (80 linhas + 4000 chars/doc, `max_docs` default 10) | `/data/docs` tem ~137 docs; evita estourar contexto do DeepSeek |
| D5 | DeepSeek via `_llm()` **já existente** (`deepseek-chat`, `max_tokens=3000`) | Reusa helper atual; zero dependência nova no requirements |

## Tools novas (em `atlas_memory_agent.py`)

### `atlas_docs_index()`
Varre `DOCS_DIR` (rglob `*.md`) → para cada doc extrai `path`, `projeto` (1º segmento do path), `tipo` (regex no nome: plano/relatorio/checkpoint/estado/contexto/decisao/doc), `size`, `first_line` (1ª linha não-#), `mtime`. Faz **upsert** idempotente na tabela `atlas_docs_index` do diário. Retorna `{total, por_projeto, por_tipo, ts}`.

### `atlas_docs_insights(projeto="", tipo="", max_docs=10)`
Filtra o scan por projeto/tipo, trunca cada doc (80 linhas + 4000 chars), monta **1 prompt batelada** para o DeepSeek pedindo JSON: `{resumo_por_doc[], temas[], links[], flags[]}`. Parse com `re.search(r"\{.*\}", raw, re.S)` + fallback seguro. Grava entry `kind='insight-docs'` no diário. Retorna `{ok, analisados, insights, ts}`.

## Passos executados

| Passo | Ação | Resultado |
|---|---|---|
| 0 | Backup local `backup-before-edit.sh` + remoto | `~/backups/herbert/atlas-docs-insights/20260823-213409/` + VM `*.bak.atlasdocs-20260823-213410` ✅ |
| 1 | Constantes `DOCS_DIR`/`_DOC_TIPOS` + helpers `_doc_tipo`/`_docs_scan` | ✅ |
| 2 | `atlas_docs_index()` | ✅ |
| 3 | `atlas_docs_insights()` | ✅ |
| 4 | Registro no `main()` (2 `mcp.tool`) + `py_compile` | ✅ (6 ocorrências `atlas_docs`) |
| 5 | scp → `~/atlas-scripts/` + restart | ✅ atlas **PID 71360**, :8768 LISTEN |
| 6 | Smoke via handshake MCP curl | ✅ VERDE (abaixo) |

## Critério de aceite — resultado

| Critério | Resultado |
|---|---|
| `py_compile` | ✅ sem erro |
| `tools/list` via handshake curl | ✅ **7 tools** (5 + `atlas_docs_index` + `atlas_docs_insights`) |
| `atlas_docs_index()` | ✅ `total: 137` · `Bytex_AgentOS: 114` · `Documentos: 23` |
| `atlas_docs_insights(projeto="Bytex_AgentOS", max_docs=3)` | ✅ `ok:true, analisados:3` — 3 resumos, 5 temas, 2 links, 2 flags reais |
| Entry `insight-docs` no diário | ✅ gravada (código executou completo) |

## Arquivos alterados (backup obrigatório)

- **`web/scripts/atlas_memory_agent.py`** (único código) — +~95 linhas
- VM: `~/atlas-scripts/atlas_memory_agent.py`

**Não tocados:** `docs_mcp_server.py`, `opencode.jsonc`, `requirements.txt`, Mnemosyne.

## Rollback

```bash
# VM
cp ~/atlas-scripts/atlas_memory_agent.py.bak.atlasdocs-20260823-213410 ~/atlas-scripts/atlas_memory_agent.py
sudo bash ~/atlas-scripts/start_atlas.sh
# local: restaurar de ~/backups/herbert/atlas-docs-insights/20260823-213409/
```

## Evolução futura (fora de escopo)

Gerar insights dos docs automaticamente dentro do `atlas_consolidar()` (além da consolidação de memórias, analisar os `.md` na mesma batelada).
