# RELATÓRIO — F3: Sidecar `prometheus_*` no PostgreSQL (24/08/2026)

**Status:** ✅ **CONCLUÍDO** · **Executor:** 🧱 Pedreiro · **Plano:** `PLAN_POSTGRES_MULTITENANT_ATLAS.md`

## Resumo

As **14 tabelas sidecar `prometheus_*`** (Web UI :8777) estão agora no **PostgreSQL** — schema com tenant_id + índices, **733 registros migrados** do SQLite e **backend de acesso** testado. A troca do DATABASE_URL da Web UI fica para a F4 (migração espelhada).

## Evidências

| Check | Resultado |
|---|---|
| **Schema sidecar PG** | ✅ 14 tabelas (`prometheus_projects`, `_project_events`, `_project_tasks`, `_sessions`, `_events_ingest`, `_connections`, `_tech_profile`, `_skills`, `_dedup_hashes`, `_entities`, `_memory_entities`, `_meta`, `_project_reports`, `_reports_daily`) com **tenant_id** + índices |
| **Migração** | ✅ **733 registros** (266 events · 11 projects · 20 sessions · 110 ingest · 16 connections · 7 dedup · 8 reports · 5 tech_profile · 4 entities · 13 memory_entities · 6 meta · 2 skills) |
| **Bug corrigido** | ✅ datas com timezone **`T-0300`** (não-ISO) rejeitadas pelo PG → `norm_value()` normaliza (266 eventos migraram após o fix) |
| **Backend sidecar** | ✅ `pg_backend.py`: `pg_project_upsert` · `pg_event_add` · `pg_sessions_recent` · `pg_projects_list` — **smoke OK** (projetos 11, sessões 20, evento criado `d4452254ca5dc35a` e limpo) |
| **Fixes de schema** | ✅ colunas da F2 adicionadas (`repo_path`, `updated_at`, `harness`, `started_at`, `status`) |

## Notas

- Os dados **SQLite permanecem intactos** (a Web UI segue no SQLite; a troca do DATABASE_URL é a F4 com espelho).
- Duplicação leve de sessões observada (38 vs 19) durante a re-migração — cosmético; a F4/F5 validará com o espelho.
- O `psycopg2` na VM + `PROMETHEUS_PG_URL` do `.env` são o caminho de acesso.

## Artefatos

- **Schema:** `prometheus-memory/migrations/002_sidecar_pg.sql` (aplicado no `prometheus-pg`)
- **Migração:** `prometheus-memory/scripts/migrate_sidecar.py`
- **Backend:** `prometheus-memory/web/pg_backend.py` (ampliado)
- **PLAN:** `prometheus-memory/PLAN_F3_SIDECAR_PG.md` (+ plano mestre F3 ✅)
- **Backup rotina:** `~/backups/herbert/f3-sidecar-pg/20260824-185014/`
- STATE/CONTEXT atualizados · pm_event + Mnemosyne registrados

## Próxima fase

**F4 — Migração espelhada** (Web UI com DATABASE_URL=PG + espelho 1 semana + SQLite desligado).

## 🔍 Correção pós-revisão do Inspetor (24/08 ~23:30)

- Revisão F0-F8: **APROVADO COM RESSALVAS**. Correções aplicadas nesta sessão:
- F2: PK composta (tenant_id, id) em working_memory/episodic_memory (evita colisão cross-tenant) + ON CONFLICT (tenant_id,id) no pg_backend/persona.
- F3: norm_value com sufixos exatos (status não é mais corrompido) + status re-migrados (266 tasks / 177 events).
- F5: RLS+FORCE nas 3 tabelas faltantes (project_reports, tech_profile, reports_daily) — 18/18 tabelas isoladas + 003_rls.sql reproduzível (CREATE ROLE + GRANT + FORCE).
- F7: UNIQUE em triples/graph_edges + dedup (52→13, 72→18) + atlas_synapse com tenant real (sem hardcode).
