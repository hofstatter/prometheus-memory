# RELATÓRIO — F2: Backend PostgreSQL do Prometheus-Memory (24/08/2026)

**Status:** ✅ **CONCLUÍDO** · **Executor:** 🧱 Pedreiro · **Plano:** `PLAN_POSTGRES_MULTITENANT_ATLAS.md`

## Resumo

Storage PostgreSQL do Prometheus-Memory criado: **schema multi-tenant no PG** (tenant_id + pgvector + tsvector) + **módulo `pg_backend.py`** (store/recall/grafo/stats). O Mnemosyne upstream **não foi forkado** (decisão técnica D13 — sem backend PG no upstream 3.16).

## Descoberta crítica

`mnemosyne-memory 3.16.0` (pin `c4344f2d`) usa **sqlite3/vec0/FTS5 direto** em dezenas de módulos — **sem DATABASE_URL nem camada de abstração** (só `db_path`). Fork para PG = inviável. → **D13 (DECISIONS.md): PG vira o storage do Prometheus-Memory; Mnemosyne core permanece motor local.**

## Evidências

| Check | Resultado |
|---|---|
| **Schema PG aplicado** | ✅ 8 tabelas (`tenants`, `agents`, `working_memory`, `episodic_memory`, `triples`, `graph_edges`, `prometheus_projects`, `prometheus_sessions`) + **HNSW** (pgvector) + **GIN** (tsvector) + seed tenant `default` |
| **Smoke psql** | ✅ insert 2 memórias + select + **busca vetorial OK** (pgvector); fts vazio por tokenização ("postgresql"≠"postgres") |
| **`pg_backend.py`** | ✅ `store` (id `864d674cf511bdd5`) + `stats` OK via psycopg2 (`PROMETHEUS_PG_URL`) |
| **psycopg2** | ✅ instalado na VM (2.9.12, pip --user) |
| **DECISIONS.md** | ✅ D13 registrada |

## Notas

- A conexão por URL DSN funciona; o recall full-text (tsvector) depende de query compatível com a tokenização — o **recall vetorial (pgvector) é o caminho principal**.
- Dados de smoke removidos (0 memórias residuais — banco limpo para a migração F4).

## Artefatos

- **Schema:** `prometheus-memory/migrations/001_schema_pg.sql` (aplicado no container `prometheus-pg`)
- **Backend:** `prometheus-memory/web/pg_backend.py` (+ cópia `/tmp/pg_backend.py` na VM)
- **PLAN:** `prometheus-memory/PLAN_F2_PG_BACKEND.md` (+ plano mestre F2 ✅) · **DECISIONS:** D13
- **Backup rotina:** `~/backups/herbert/f1-pg-vm101/20260824-173923/` (estado pré-F2: SQLite + PG vazio)
- STATE/CONTEXT atualizados · pm_event + Mnemosyne registrados

## Próxima fase

**F3 — Sidecar `prometheus_*` em PG** (Web UI :8777 lendo/gravando PG).

## 🔍 Correção pós-revisão do Inspetor (24/08 ~23:30)

- Revisão F0-F8: **APROVADO COM RESSALVAS**. Correções aplicadas nesta sessão:
- F2: PK composta (tenant_id, id) em working_memory/episodic_memory (evita colisão cross-tenant) + ON CONFLICT (tenant_id,id) no pg_backend/persona.
- F3: norm_value com sufixos exatos (status não é mais corrompido) + status re-migrados (266 tasks / 177 events).
- F5: RLS+FORCE nas 3 tabelas faltantes (project_reports, tech_profile, reports_daily) — 18/18 tabelas isoladas + 003_rls.sql reproduzível (CREATE ROLE + GRANT + FORCE).
- F7: UNIQUE em triples/graph_edges + dedup (52→13, 72→18) + atlas_synapse com tenant real (sem hardcode).
