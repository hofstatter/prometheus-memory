# PLAN_TELEMETRIA_PUSH_MCP — Telemetria Push via MCP + Fixes do Painel Projetos (pós-migração Docker)

- **Autor:** 🏛️ Arquiteto (desenho) + 🧱 Pedreiro (execução) · **Data:** 09/08/2026 · **Projeto-alvo:** `prometheus-memory` (repo público) + config OpenCode
- **Classificação:** MEDIUM (novo MCP + config + socket + multi-arquivo → Inspetor na fronteira)
- **Status:** ✅ APROVADO (Herbert, 09/08/2026) · **EXECUÇÃO INICIADA 09/08/2026 ~18:52** · **EXECUÇÃO CONCLUÍDA 09/08/2026 ~22:05 (F1–F7; F2/F3 aguardam restart do OpenCode p/ tools `prometheus-pm_*` visíveis)**

## Resultado da execução (resumo)

- **F1 ✅** `web/scripts/pm_mcp_server.py` criado; selftest → 201 (evento `ed8a2e44fd4a` + idempotência `duplicate: true` em re-run; timeout cliente ajustado 10→30s pois ingest_event faz refresh+memória).
- **F2 ⏳** `opencode.jsonc` com bloco `prometheus-pm` (10 MCPs, parse OK) + GUARDRAILS regra 19 → v5 + CONTEXT.md atualizado. **Restart do OpenCode pendente (Herbert)** para carregar o MCP.
- **F3 ✅ (config)** skills `workflow` (pm_event em handoff) + `auto-memory` (pm_session start/close) gravadas. Validação por agente só pós-restart.
- **F4 ✅** `telemetry_collector.py` paths env-first (`OPENCODE_CONFIG_DIR`/`OPENCODE_DATA_DIR`/`MNEMOSYNE_HOME`) + log de boot + sync cópia `Projetos/web/`; rebuild → coletor roda **sem erro** (`db=/data/mnemosyne/data/mnemosyne.db`); loop supervisord ingeriu 10 workflow + 18 opencode. Sessões com cwd fora de projeto (`~/`) não mapeiam (comportamento esperado — push MCP cobre com slug explícito).
- **F5 ✅** `resolve_repo_path()` em `prometheus_db.py` aplicado em `pm_project_mcps`, `pm_git_log`, `tech_profile._project_dir`. `GET /api/pm/projects/evscar/mcps` → 8 docker services; bytex → 3; git log prometheus-memory → commits reais. (evscar/provador sem `.git` = correto.)
- **F6 ✅** socket `:ro` no compose + entrypoint garante grupo do gid do socket (116) p/ herbert + `_containers()` via Engine API unix socket. Scans: prometheus-memory 1 container, evscar 8, bytex 3, provador 0 (systemd). UI validada (Playwright): Containers/Git/MCPs/Kanban com dados reais.
- **F7 ⏳→✅** STATE Bytex_AgentOS (sessão 56) + CONTEXT atualizados; Mnemosyne gravado via API :8766 (MCP SSE da sessão invalidado pelo rebuild — restart do OpenCode reestabelece). **Achado extra:** mnemosyne-memory resolveu p/ **3.16.0** no rebuild (release swap monitorado atingido) — modelo embeddings `bge-small-en-v1.5`; cache em `/data/cache/fastembed` (efêmero) → **persistido via `MNEMOSYNE_FASTEMBED_CACHE_DIR=/data/mnemosyne/fastembed-cache`** (65MB no volume; recall 30s→2s).
- **⚠️ PENDENTE (pós-restart do OpenCode pelo Herbert):** validar tools `prometheus-pm_*` no agente + 1 `pm_event` real de sessão aparecendo no Kanban <5s + sessão SSE do Mnemosyne restabelecida.

## 1. Diagnóstico (3 bugs, mesma família — gap de migração pro Docker)

1. **Kanban/Timeline congelados:** `telemetry_collector.py` no container usa paths hardcoded do host (`Path.home()/.config/opencode`, `Path.home()/.hermes/mnemosyne`) → `unable to open database file` a cada 5 min desde ago/08 ~20:21 (supervisord loop). Zero eventos novos.
2. **"MCPs & Serviços" vazio (+ git log/info idem):** `prometheus_projects.repo_path` tem paths do host (`~/Projetos/*`) inexistentes no container (projetos montados em `/data/projetos` via bind ro). `Path(rp).exists()` → False → mcps/docker/git vazios.
3. **"Containers (runtime)" vazio:** `_containers()` roda `docker ps` e `_systemd_services()` roda `systemctl --user` — nenhum existe no container; sem socket docker montado.

**Fatos verificados:** container `prometheus-memory` Up 21h healthy · `/app/telemetry_collector.py` md5 == repo `web/` · binds `/telemetry/config` + `/telemetry/share` + `/data/projetos` existem · env `OPENCODE_CONFIG_DIR`/`OPENCODE_DATA_DIR`/`MNEMOSYNE_HOME` definidos mas não lidos pelo script · DB volume: 165 events/166 tasks antigos (migrados) · 4 projetos com repo_path do host · git presente no container (`/usr/bin/git`), socket docker ausente · POST `/api/pm/events` exige Bearer (container roda `PROMETHEUS_HOST=0.0.0.0` → auth ativa).

## 2. Decisões (D1–D10)

| # | Decisão | Porquê |
|---|---|---|
| **D1** | Micro-MCP stdio `prometheus-pm` (`web/scripts/pm_mcp_server.py`) | MCP do Mnemosyne vem de upstream (`mnemosyne-oss/mnemosyne@c4344f2d`) — sem fork; micro-MCP próprio fala HTTP com :8777 |
| **D2** | 3 tools: `pm_event`, `pm_session` (start/heartbeat/close), `pm_tasks` | pm_event = Kanban/Timeline real-time; pm_session = presença (aprovado na v1); pm_tasks = agentes leem o board |
| **D3** | Token lido do `web/.env` pelo script (env `PROMETHEUS_TOKEN` override) | Zero duplicação de segredo; script público-safe |
| **D4** | `client_event_id` = sha1(session:type:title:minuto)[:20] · `session_key` = `opencode:`+sha1(cwd:data)[:12] | Idempotência de retry no minuto; sessão coarse (OpenCode não injeta session id no env MCP) |
| **D5** | Wiring via skills (`workflow` → pm_event em handoff; `auto-memory` → pm_session start/close) | Ponto único de instrução; não tocar personas |
| **D6** | Push (tempo real) + coletor (rede de segurança) coexistem | Complementares; dupla contagem aceitável (fontes distintas, documentado) |
| **D7** | Ordem: push primeiro, fixes depois | Pedido do Herbert |
| **D8** | PLAN no repo `prometheus-memory/docs/` | REGRA_DOC; repo público, plano sem segredos |
| **D9** | `resolve_repo_path(rp)`: tenta rp → senão `PROMETHEUS_PROJECTS_ROOT/basename(rp)` com `is_relative_to` | Sem migração de dados; DB mantém paths do host; helper resolve em runtime |
| **D10** | Docker socket montado `:ro` + helper Python puro (HTTP sobre unix socket) para `_containers()` | Aprovado pelo Herbert ciente do tradeoff (socket = controle Docker; local, bind 127.0.0.1). systemd section fica `[]` documentado (irrecuperável por design) |

## 3. Arquitetura

```
Agente (arquiteto/pedreiro/inspetor)
  │ chama prometheus-pm (instruído pelas skills)
  ▼
pm_mcp_server.py (stdio MCP, host)  ──HTTP + Bearer (web/.env)──►  :8777
  pm_event  → POST /api/pm/events              (Kanban/Timeline real-time)
  pm_session→ POST /api/pm/sessions/{start,heartbeat,close}  (presença)
  pm_tasks  → GET  /api/pm/projects/<slug>/tasks   (read)

Rede de segurança (após F4):
telemetry_collector (container, loop 5min) → workflow-state/opencode.db/git → mesma tabela
```

## 4. Contratos das tools

```python
pm_event(event_type, title, summary="", status_hint="", progress_delta=0.0,
         project_slug="", cwd="") -> dict
# envelope: harness="opencode", harness_session_id=sha1(cwd:data)[:12], agent_id,
# event_type, title, summary, status_hint, progress_delta, project_slug, cwd,
# client_event_id=sha1(session:type:title:minuto)[:20]

pm_session(action: "start"|"heartbeat"|"close", current_action="", project_slug="", cwd="") -> dict

pm_tasks(project_slug) -> dict
```

**Mapeamento stage→event (skill workflow):** arquiteto→planning · pedreiro→implementation · inspetor/visionario→review · status_hint: work→doing, review/docs/fix/decision→done (mesma regra do coletor).

## 5. Arquivos

| Arquivo | Ação |
|---|---|
| `prometheus-memory/docs/PLAN_TELEMETRIA_PUSH_MCP.md` | CRIAR (este) |
| `prometheus-memory/web/scripts/pm_mcp_server.py` | CRIAR — FastMCP stdio, 3 tools, `_load_token()` (lê web/.env, nunca imprime), `--selftest` |
| `~/.config/opencode/opencode.jsonc` | ALTERAR — bloco `prometheus-pm` local stdio |
| `~/.config/opencode/skills/workflow/SKILL.md` | ALTERAR — regra de push em handoff |
| `~/.config/opencode/skills/auto-memory/SKILL.md` | ALTERAR — pm_session start/close |
| `~/.config/opencode/docs/GUARDRAILS.md` | ALTERAR — regra 19 → v5 (10 MCPs) |
| `prometheus-memory/web/telemetry_collector.py` | ALTERAR — paths env-first (F4) |
| `Projetos/web/telemetry_collector.py` | ALTERAR — sync (F4) |
| `prometheus-memory/web/prometheus_db.py` ou `tech_profile.py` | ALTERAR — `resolve_repo_path()` (F5) |
| `prometheus-memory/web/pm_routes.py` | ALTERAR — usar helper em mcps/git (F5) |
| `prometheus-memory/web/tech_profile.py` | ALTERAR — helper + `_containers()` via socket (F5/F6) |
| `prometheus-memory/docker-compose.yml` | ALTERAR — socket mount (F6) |
| `Bytex_AgentOS/CONTEXT.md` + `STATE.md` | ALTERAR — 10º MCP + resultado (F7) |

## 6. Fases + aceites

| Fase | Conteúdo | Aceite |
|---|---|---|
| **F1** | pm_mcp_server.py | `python3 pm_mcp_server.py --selftest` → 201 + evento em `GET /api/pm/projects/<slug>/events` |
| **F2** | opencode.jsonc + GUARDRAILS v5 + CONTEXT | Parse node OK (10 MCPs) · restart OpenCode (Herbert) → tools `prometheus-pm_*` visíveis |
| **F3** | Skills workflow + auto-memory | Sessão real gera evento push <5s no Kanban |
| **F4** | Coletor env-first + sync + rebuild | `docker exec ... telemetry_collector.py` → 0 erros; log para; count events ↑; backlog 21h ingerido |
| **F5** | resolve_repo_path em mcps/git/tech_profile | `GET /api/pm/projects/evscar/mcps` → mcps+docker não-vazios · `/git/log` → commits reais |
| **F6** | Socket mount + `_containers()` via unix socket + rebuild | `GET /api/pm/projects/prometheus-memory/runtime` → containers reais; demais projetos idem |
| **F7** | STATE + Mnemosyne + status PLAN | Checkpoint + memórias |

## 7. Riscos

| Risco | Mitigação |
|---|---|
| `mcp` SDK ausente no host | Check F1; `pip3 install --user mcp` |
| 401 no push (token) | Selftest falha explícito → relê web/.env; env override |
| Agente não chamar a tool | Coletor (F4) é rede de segurança |
| Dupla contagem push+coletor | Documentado (D6) |
| Socket docker no container | Bind 127.0.0.1 + `:ro` + auth Bearer; decisão Herbert (D10) |
| Remap por basename colide (2 repos homônimos) | Hoje 4/4 são filhos diretos de ~/Projetos; check is_relative_to |
| Rebuild quebra serviço | Imagem anterior preservada (docker tag); volume intocado; restart policy |

## 8. Rollback

- MCP: `"enabled": false` no bloco prometheus-pm.
- Skills/GUARDRAILS/compose/scripts: restore dos backups `telemetria-push-mcp/20260809-185151`.
- Container: rebuild da imagem anterior; volume `prometheus-data` intocado em toda a lane.
- Coletor: reverter paths para hardcoded (backup) — comportamento pré-fix.
