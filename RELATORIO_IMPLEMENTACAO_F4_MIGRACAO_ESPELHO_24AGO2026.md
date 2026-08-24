# RELATÓRIO — F4: Migração espelhada (Web UI → PG via adapter + espelho) (24/08/2026)

**Status:** ✅ **CONCLUÍDO** (adapter + espelho; troca de produção aguarda aprovação) · **Executor:** 🧱 Pedreiro

## Resumo

A **Web UI :8777** agora suporta o **PostgreSQL** como storage (via `PROMETHEUS_PG_URL`) sem reescrever as queries — através do adapter **`PGSQLiteCompat`** que emula a interface sqlite3 sobre psycopg2. Espelho de validação (SQLite vs PG) configurado por 1 semana.

## Evidências

| Check | Resultado |
|---|---|
| **Adapter `web/pg_adapter.py`** | ✅ `?`→`%s` (ignorando strings) · RealDictCursor (`row["col"]`) · `PRAGMA table_info` via information_schema · `executescript` tolerante · PRAGMAs de config no-op |
| **`prometheus_db.py`** | ✅ `get_conn()` → PG se `PROMETHEUS_PG_URL`, senão SQLite · `init_schema()` com try/finally |
| **Smoke base** | ✅ `PGSQLiteCompat` retornado · init_schema OK · leitura (3 projetos) · escrita/leitura meta |
| **Smoke ampliado** | ✅ INSERT/SELECT/UPDATE/DELETE com `?` + `row["col"]` + `PRAGMA table_info` (8 cols) — **tudo OK** |
| **Espelho** | ✅ `validate_mirror.py` + `pg-mirror.sh` + **cron 03:30** · **1º run: OK na maioria; divergência esperada em 4 tabelas** (UI ainda escreve no SQLite — o PG está na foto da F3; o espelho detecta exatamente isso) |
| **SQLite** | ✅ intacto (espelho + rollback) |

## Notas

- A **divergência no espelho** (events/sessions/ingest/tasks) é o comportamento **esperado**: a produção ainda grava no SQLite; quando a UI trocar para o PG, a divergência estabiliza e o espelho valida.
- **Troca de produção (passo final da F4):** setar `PROMETHEUS_PG_URL` no ambiente do Flask + restart — **aguarda aprovação do Herbert** (janela de manutenção). Rollback: remover o env → SQLite volta (instantâneo).

## Artefatos

- **Adapter:** `prometheus-memory/web/pg_adapter.py` · **db:** `web/prometheus_db.py` (switch) · **espelho:** `scripts/validate_mirror.py` + `/usr/local/bin/pg-mirror.sh` + cron 03:30
- **PLAN:** `prometheus-memory/PLAN_F4_MIGRACAO_ESPELHO.md` (+ plano mestre F4 ✅)
- **Backup rotina:** `~/backups/herbert/f4-migracao-espelho/20260824-190021/`
- STATE/CONTEXT atualizados · pm_event + Mnemosyne registrados

## Próxima fase

**F5 — Multi-tenant + Auth Gateway** (tenants/agents/API keys + RLS).
