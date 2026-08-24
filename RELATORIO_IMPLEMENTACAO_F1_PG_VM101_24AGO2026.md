# RELATÓRIO — F1: PostgreSQL + pgvector + pgBouncer na VM 101 (24/08/2026)

**Status:** ✅ **CONCLUÍDO** · **Executor:** 🧱 Pedreiro · **Plano:** `PLAN_POSTGRES_MULTITENANT_ATLAS.md`

## Resumo

Infraestrutura de banco relacional da VM 101 criada: **PostgreSQL 16.15 + pgvector 0.8.6 + pgBouncer** em containers, com backup lógico diário. Base para as fases F2+ (migração Mnemosyne e multi-tenant).

## Evidências

| Check | Resultado |
|---|---|
| **Container `prometheus-pg`** | ✅ **Up** — imagem `pgvector/pgvector:pg16` · `restart=unless-stopped` (sobe no boot) · porta **5432** · volume `prometheus-pg-data` |
| **PostgreSQL** | ✅ **16.15 (Debian)** via `psql` |
| **pgvector** | ✅ **0.8.6** (`CREATE EXTENSION vector` OK) |
| **pgBouncer** | ✅ **Up** na porta **6432** (`POOL_MODE=transaction`, 200 conns máx, pool 20) |
| **Backup diário** | ✅ `/usr/local/bin/backup-pg.sh` (`docker exec pg_dump -F c`) + **cron 02:30** → `/data/pg-backups/` (retenção 7) · **teste 1x OK** (`BACKUP_PG_OK`, 4KB — DB vazio, esperado) |
| **Credenciais** | ✅ `PROMETHEUS_PG_PASSWORD` (gerada na VM, não exposta) + `PROMETHEUS_PG_DB/USER` no `/opt/prometheus/.env` · backup do `.env` em `.env.bak.<ts>` |
| **Restart no boot** | ✅ containers com `restart=unless-stopped` |

## Notas

- O `pg_dump` não existe no host → o script usa `docker exec prometheus-pg pg_dump` (corrigido no 1º teste).
- O DB `prometheus_memory` está **vazio** (nenhum dado migrado — a migração é a F4, após o backend PG do F2/F3).

## Re-verificação (24/08 ~20:42 — sessão seguinte)

✅ **Idempotente confirmado:** containers `prometheus-pg` e `prometheus-pgbouncer` **Up** (sobreviveram) · psql PostgreSQL 16.15 · pgvector 0.8.6 · cron backup 02:30 ativo · portas 5432/6432 escutando · **backup fresco OK** (`prometheus_memory_20260824-204235.dump`).

## Artefatos

- **PLAN:** `prometheus-memory/PLAN_F1_PG_VM101.md` (+ plano mestre atualizado: F1 ✅)
- **Script:** `/usr/local/bin/backup-pg.sh` (VM 101) · cron 02:30
- **Backup rotina:** `~/backups/herbert/f1-pg-vm101/20260824-173923/`
- **Backup do .env da VM:** `/opt/prometheus/.env.bak.*`
- STATE/CONTEXT atualizados · pm_event + Mnemosyne registrados

## Próxima fase

**F2 — Backend PG do Mnemosyne core** (recall/store/sleep/graph/triples sobre PG + pgvector/tsvector).
