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
   - ✅ **CONCLUÍDA (25/08 ~01:40, aprovada pelo Herbert):** `prometheus_db.py` c/ switch (PGSQLiteCompat) + `pg_adapter.py` copiados para `/app` do container · `environment=PROMETHEUS_PG_URL` (<IP_DOCKER>) injetado no `[program:prometheus-web]` do supervisord · `docker restart prometheus-memory` · **validado:** health 200, página 200, `get_conn()`→PGSQLiteCompat, COUNT=4285 via PG, escrita+leitura+delete OK, espelho mostra divergência esperada (UI escreve no PG, SQLite parou de receber escritas) · **rollback:** remover a linha `environment=PROMETHEUS_PG_URL` do conf do supervisord + restart (SQLite volta) · ⚠️ conf do supervisord e `/app` vêm da IMAGEM → rebuild reverte (documentado em DECISIONS/relatório) · backup do flip: `~/backups/herbert/flip-f4-web-pg/20260825-013819/`
5. SQLite **não é removido** (arquivo mantido — espelho + rollback) ✅

## Próxima fase

**F5 — Multi-tenant + Auth Gateway** (tenants/agents/API keys + RLS).

- ✅ **Painel alinhado ao PG (25/08 ~02:20):** UNIQUEs puros criados (slug, project_slug×2, key, name, session_key) + colunas do painel adicionadas (last_event_at, session_key, harness_session_id, cwd, current_action) + adapter traduz `INSERT OR IGNORE` + canvas usa `get_conn()` com `row["latest_ts"]` (compat sqlite3.Row/RealDictRow) + env via `command=env PROMETHEUS_PG_URL=...` (o `environment=` do supervisord não aplicava) · **pm_event/canvas/telemetry validados no PG** (Inspetor APROVADO c/ ressalvas, 2 rodadas) · commits: 41d46df, 06d0731 (repo).
