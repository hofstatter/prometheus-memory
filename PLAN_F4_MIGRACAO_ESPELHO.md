# PLAN F4 — Migração espelhada (Web UI DATABASE_URL=PG + espelho) (24/08/2026)

**Fase do:** `PLAN_POSTGRES_MULTITENANT_ATLAS.md` · **Executor:** 🧱 Pedreiro · **Aprovado:** Herbert

## Objetivo

Permitir que a **Web UI :8777** rode sobre o **PostgreSQL** (via `DATABASE_URL`/`PROMETHEUS_PG_URL`), com **espelho de validação** (SQLite vs PG) por 1 semana e rollback imediato.

## Execução

| Item | Detalhe |
|---|---|
| **Adapter** | `web/pg_adapter.py` — `PGSQLiteCompat`: emula a interface sqlite3 (placeholders `?`→`%s`, `row["col"]` via RealDictCursor, `PRAGMA table_info` via information_schema, `executescript` tolerante, PRAGMAs de config no-op) |
| **prometheus_db.py** | `get_conn()` → **PG se `PROMETHEUS_PG_URL`**; senão SQLite (fallback). `init_schema()` tolerante (try/finally) |
| **Testes** | smoke base (projetos/meta) + **smoke ampliado** (INSERT/SELECT/UPDATE/DELETE com `?`, row["col"], PRAGMA table_info) — ✅ |
| **Espelho** | `scripts/validate_mirror.py` + `/usr/local/bin/pg-mirror.sh` + **cron 03:30** — compara contagens SQLite vs PG (sidecar) · **1º run OK** (detectou divergência esperada: UI ainda escreve no SQLite) |

## Critérios de aceite (F4)

1. Adapter testado (INSERT/SELECT/UPDATE/DELETE/PRAGMA/row-by-name) ✅
2. `get_conn()` com switch PG/SQLite ✅ (smoke: `PGSQLiteCompat` retornado com URL)
3. Espelho rodando (cron 03:30, log `/var/log/pg-mirror.log`) ✅
4. **Troca da produção (passo final):** setar `PROMETHEUS_PG_URL` no ambiente da Web UI + restart — **aguarda aprovação do Herbert** (janela de manutenção) · rollback = remover o env → SQLite volta
5. SQLite **não é removido** (arquivo mantido — espelho + rollback) ✅

## Próxima fase

**F5 — Multi-tenant + Auth Gateway** (tenants/agents/API keys + RLS).
