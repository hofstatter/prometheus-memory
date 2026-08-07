# PLAN P5 — Projetos Vivo: painel com telemetria real das personas

- **Classificação:** MEDIUM · **Repo:** prometheus-memory · **Status:** EXECUTANDO (sessão 44/07-08)
- **Aprovado por Herbert:** 07/08/2026 — P5.0+P5.1 na 1ª sessão de build, depois P5.2→P5.5 sequenciais.
- **Causa-raiz (diagnóstico):** painel Projetos tem UI+API+tabelas prontas, mas `prometheus_sessions`=0,
  `prometheus_project_events`=9 (seed único 03/08), `prometheus_project_tasks`=0 → nenhuma instrumentação
  escreve em tempo real. As personas trabalham e nada vira evento.

---

## P5.0 — Sync divergência repo↔produção (MICRO)

**Problema:** `web/token_savings.py` e `web/scripts/` existem em produção (`~/Projetos/web`) mas NÃO no repo.

**Passos:**
1. `cp ~/Projetos/web/token_savings.py → web/token_savings.py` + `cp -r ~/Projetos/web/scripts → web/scripts`
2. `git add` + commit + push (GIT GATE)

**Aceite:** `diff` vazio entre repo e produção para esses arquivos.

## P5.1 — Coletor de telemetria (NÚCLEO)

**Novo `web/telemetry_collector.py`** + systemd user timer (5 min), roda standalone, escreve no
`prometheus_db` (mesmo DB da UI). **Fontes de verdade (mecânicas, sem depender de agente):**

| Fonte | Dado coletado | Persona? |
|---|---|---|
| `~/.config/opencode/workflow-state.json` | `history[]`: stage, model, handoff, ts, backup_manifest | ✅ stage (pedreiro/inspector/arquiteto/visionario) |
| `~/.local/share/opencode/opencode.db` | `session` (271), `message` (13562), `todo` (207) com timestamps | ✅ model no message.data → mapa model→persona |
| `git log` dos repos (projects_registry.repo_path) | commits (hash, msg, author, date) → eventos | derivado (convenção feat/fix/docs + author) |
| `STATE.md` (Bytex_AgentOS) | seções `## 🧠 SESSÃO` datadas → eventos de fechamento | sessão geral |

**Fluxo (idempotente, `client_event_id` = sha1(fonte+id)):**
1. `upsert_session()` — cria/atualiza `prometheus_sessions` (start/heartbeat com `current_action` do
   workflow-state atual, `agent_id`=persona, `harness`=opencode).
2. `ingest_event()` — de cada `history[]` novo (by ts): event_type mapeado (planejamento→planning,
   implementação→implementation, revisão→review), title = 1ª linha do handoff, summary = handoff, agent_id=stage.
3. `ingest_git_events()` — commits novos por repo → eventos `implementation`/`docs`/`fix` com data do commit.
4. `sync_tasks()` — fecha tasks antigas, cria tasks do kanban a partir de eventos (planning→todo,
   implementation em andamento→doing, review/commit→done).
5. Grava `last_collect_ts` (tabela nova `prometheus_meta` ou arquivo state) para incremental.

**Persona map (model→persona), extensível:**
```python
PERSONA_BY_MODEL = {
  "kimi-for-coding/k3": "arquiteto",
  "deepseek/deepseek-v4-flash": "pedreiro",
  "deepseek/deepseek-v4-pro": "inspector",
  "zai-coding-plan/glm-4.5v": "visionario",
}
```
Persona desconhecida → `agent_id` = slug do modelo (não quebra, aparece como nova persona).

**Systemd (user):** `~/.config/systemd/user/prometheus-telemetry.service` + `.timer` (OnCalendar=*:0/5).
Timer ativa imediatamente pós-instalação (uma execução).
> **Nota deploy (obs. Inspetor ce1ad2d):** units systemd NÃO são versionadas no repo — criadas
> manualmente no deploy (config local do usuário). Sempre que o coletor mudar, re-sincronizar
> `~/Projetos/web/telemetry_collector.py` (sha256) — o timer aponta para o caminho de produção.

**Aceite P5.1:** após 1 execução, `prometheus_sessions>0`, eventos do dia com `agent_id` das personas,
Kanban mostra itens de HOJE. `systemctl --user list-timers` mostra o timer ativo.

## P5.2 — Kanban vivo + Timeline clicável (UI)

- Kanban alimentado de `prometheus_project_tasks` (P5.1 já cria) — colunas Backlog/Em andamento/Concluído
  com **persona + tempo decorrido** por item.
- Timeline: itens clicáveis → modal detalhe (título, tipo, projeto, persona, data/hora exata,
  summary completo do handoff, memória vinculada via `memory_id`).
- Presença: sessões ativas mostram `current_action` (o que o agente faz AGORA).

**Aceite:** clique num item da Timeline abre modal com timestamp e persona; Kanban reflete 24h.

## P5.3 — Relatório por persona (24h)

- Endpoint `/api/pm/analytics/personas?window=24h`: por persona (agent_id) → counts por event_type
  (planning/implementation/review), %, lista detalhada. Extensível (vem do agent_id, sem hardcode).
- UI: card "📊 Personas (24h)" com barras + drill-down.

**Aceite:** `curl .../analytics/personas?window=24h` retorna JSON com personas reais do dia.

## P5.4 — Git por projeto (histórico)

- Estender `pm_git_get` → `/api/pm/projects/<slug>/git/log?n=20`: últimos commits (hash curto, msg,
  autor, data) do repo local (repo_path em projects_registry).
- UI: seção Git = timeline de commits.

**Aceite:** projeto prometheus-memory mostra commit `50c2fc7` com data de hoje.

## P5.5 — Notes por projeto + tokens + MCPs por projeto

- **Notes:** agrupar `~/notes/*.md` por projeto (frontmatter `project:` ou tag no título); mini-relatório
  por grupo (n docs, última atualização).
- **Tokens por projeto:** estender `token_savings.py` → breakdown por projeto (offloaded bytes por lane
  `proj:<slug>` + recalls): estimativa de gasto vs economia.
- **MCPs por projeto:** `connections_registry` detecta MCPs (lê `opencode.jsonc` do projeto +
  docker-compose) além das API keys.

**Aceite:** aba Notes com grupos por projeto + card de economia; projeto mostra "MCPs usados".

---

## Riscos / armadilhas

- Coletor roda como usuário `herbert` → acesso leitura a `~/.local/share/opencode` e `~/.hermes` OK.
- `opencode.db` em WAL (read-only uri ok). Nunca escrever nela.
- Idempotência via `client_event_id` (hash) — 2ª execução = 0 novos.
- Incremental: guardar `last_collect_ts` para não re-ingestar 273k eventos do histórico.
- Divergência: após P5.0, TODA alteração em web/ deve ser sincronizada repo↔produção (sha256) antes do push.
- GIT GATE em todo push (Inspetor + SIM Herbert) — hook pre-push já valida identidade.
