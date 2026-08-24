# RELATÓRIO — F5: Multi-tenant + Auth Gateway (24/08/2026)

**Status:** ✅ **CONCLUÍDO E TESTADO** · **Executor:** 🧱 Pedreiro

## Resumo

Isolamento multi-tenant real (RLS) + **API key única por agente** com emissão manual, validação e revogação imediata — integrado à API REST :8766.

## Evidências

| Check | Resultado |
|---|---|
| **Auth Gateway** | ✅ `issue_key` → `pm_1_7YRi0...` (hermes-01) e `pm_2_QBqT...` (opencode-02, tenant 2) · `validate_key` retorna {tenant, agent, channel, harness} · **revoke imediato** (key revogada → `INVALIDO`) · `list` (2 agentes, status) |
| **CLI pm-key** | ✅ `~/.local/bin/pm-key` (issue/validate/revoke/list) |
| **RLS** | ✅ 15 tabelas com `ENABLE + FORCE ROW LEVEL SECURITY` (policy por `app.tenant_id`, default '1') · **role `prometheus_app`** criado (sem BYPASSRLS) + GRANT · **isolamento comprovado:** tenant 2 → só `proj-cliente2` · tenant 999 → **0** · tenant 1 → 11 |
| **API :8766** | ✅ `_check_auth()` aceita token global **OU** API key de agente · rota `/whoami` → `{"identity":{"role":"agent","tenant_id":2,"agent_id":"opencode-02","channel_id":"opencode-02","harness":"opencode"}}` |
| **Container** | ✅ `mnemosyne_api.py` + `auth_gateway.py` + `pg_config.json` (URL PG via <IP_DOCKER>) + **psycopg2-binary** instalado |

## Notas técnicas

- O RLS **não filtrava** no role `prometheus` (tem `BYPASSRLS`) → criado `prometheus_app` (sem bypass) como role de aplicação.
- O container acessa o PG via **<IP_DOCKER>** (gateway docker), não 127.0.0.1 — config via `pg_config.json`.
- Emissão manual (default aprovado): o Herbert usa `pm-key issue <agent_id> --tenant N --harness <nome>`.

## Artefatos

- **Gateway:** `prometheus-memory/web/scripts/auth_gateway.py` · **CLI:** `scripts/pm_key.py` → `pm-key` · **RLS:** `migrations/003_rls.sql`
- **API:** `web/scripts/mnemosyne_api.py` (auth + /whoami)
- **PLAN:** `prometheus-memory/PLAN_F5_MULTITENANT_AUTH.md` (+ plano mestre F5 ✅)
- **Backup rotina:** `~/backups/herbert/f5-multitenant-auth/20260824-190908/`
- STATE/CONTEXT atualizados · pm_event + Mnemosyne registrados

## Próxima fase

**F6 — Atlas arco reflexo (2 velocidades) sobre PG** (recall <50ms + consolidação assíncrona).

## 🔍 Correção pós-revisão do Inspetor (24/08 ~23:30)

- Revisão F0-F8: **APROVADO COM RESSALVAS**. Correções aplicadas nesta sessão:
- F2: PK composta (tenant_id, id) em working_memory/episodic_memory (evita colisão cross-tenant) + ON CONFLICT (tenant_id,id) no pg_backend/persona.
- F3: norm_value com sufixos exatos (status não é mais corrompido) + status re-migrados (266 tasks / 177 events).
- F5: RLS+FORCE nas 3 tabelas faltantes (project_reports, tech_profile, reports_daily) — 18/18 tabelas isoladas + 003_rls.sql reproduzível (CREATE ROLE + GRANT + FORCE).
- F7: UNIQUE em triples/graph_edges + dedup (52→13, 72→18) + atlas_synapse com tenant real (sem hardcode).
