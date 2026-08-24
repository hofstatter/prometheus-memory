# PLAN F3 — Sidecar `prometheus_*` no PostgreSQL (24/08/2026)

**Fase do:** `PLAN_POSTGRES_MULTITENANT_ATLAS.md` · **Executor:** 🧱 Pedreiro · **Aprovado:** Herbert

## Objetivo

Levar as tabelas **sidecar `prometheus_*`** (Web UI :8777, projetos/eventos/sessões/conexões) para o PostgreSQL — schema + migração + acesso, preparando a troca do DATABASE_URL (F4) e o multi-tenant (F5).

## Execução

| Item | Detalhe |
|---|---|
| **Schema sidecar PG** | `migrations/002_sidecar_pg.sql` — **14 tabelas** `prometheus_*` com **tenant_id** + índices (events por tenant/ts, tasks por status, sessions por seen, connections por fingerprint, skills por status) |
| **Migração de dados** | `scripts/migrate_sidecar.py` — SQLite → PG (tenant_id=1) com **normalização de datas** (corrige o formato `T-0300` não-ISO que o PG rejeita) · **733 registros migrados** |
| **Backend sidecar** | `web/pg_backend.py` ampliado: `pg_project_upsert` · `pg_event_add` · `pg_sessions_recent` · `pg_projects_list` |
| **Fixes de schema** | colunas faltantes da F2 adicionadas: `prometheus_projects.repo_path/updated_at` · `prometheus_sessions.harness/started_at/status` |

## Critérios de aceite (F3)

1. Schema sidecar aplicado (14 tabelas + índices) ✅
2. Migração completa (733 registros: 266 eventos, 11 projetos, 20 sessões, 110 ingest, 16 conexões...) ✅
3. Backend sidecar testado (projetos/sessões/eventos — smoke OK, evento criado e limpo) ✅
4. Dados SQLite intactos (a troca do DATABASE_URL da Web UI é a F4) ✅

## Próxima fase

**F4 — Migração espelhada** (troca do DATABASE_URL da Web UI para PG + espelho 1 semana + SQLite desligado).
