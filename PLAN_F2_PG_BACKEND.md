# PLAN F2 — Backend PostgreSQL do Prometheus-Memory (24/08/2026)

**Fase do:** `PLAN_POSTGRES_MULTITENANT_ATLAS.md` · **Executor:** 🧱 Pedreiro · **Aprovado:** Herbert

## Objetivo

Criar o **storage PostgreSQL do Prometheus-Memory** (nosso produto) — schema + módulo de acesso — como base para multi-tenant (F5) e migração (F4).

## Descoberta técnica (registrada em DECISIONS.md D13)

O **Mnemosyne upstream 3.16.0 NÃO tem backend PG** (sqlite3/vec0/FTS5 direto em dezenas de módulos, sem `DATABASE_URL`/abstração). **Fork completo = inviável.** Ajuste: o **PG vira o storage do Prometheus-Memory**, e o Mnemosyne core permanece como motor local de embeddings/recall.

## Execução

| Item | Detalhe |
|---|---|
| **Schema PG** | `migrations/001_schema_pg.sql` — tabelas: `tenants`, `agents`, `working_memory`, `episodic_memory`, `triples`, `graph_edges`, `prometheus_projects`, `prometheus_sessions` · **tenant_id** em todas · **pgvector(384) HNSW** (idx_wm/idx_ep_embedding) · **tsvector GIN** (content_tsv) · seed tenant `default` (id 1) |
| **Aplicação** | `docker exec prometheus-pg psql` (tabelas + índices criados) |
| **Módulo backend** | `web/pg_backend.py` — `pg_conn()` (PROMETHEUS_PG_URL, psycopg2) · `pg_store()` (upsert + tsvector) · `pg_recall()` (vetorial ou fts) · `pg_add_triple()` · `pg_add_edge()` · `pg_stats()` |
| **Dependência** | `psycopg2-binary` instalado na VM (pip --user) |

## Critérios de aceite (F2)

1. Schema aplicado no PG (8 tabelas + índices + tsvector + tenant default) ✅
2. Smoke via psql: insert + select + busca vetorial (pgvector) ✅
3. `pg_backend.py` testado: `store` OK + `stats` OK (recall fts vazio por tokenização — vetorial é o caminho principal) ✅
4. DECISIONS.md com D13 (ajuste de escopo) ✅

## Próxima fase

**F3 — Sidecar `prometheus_*` em PG** (Web UI :8777 lendo/gravando PG via `pg_backend.py`).
