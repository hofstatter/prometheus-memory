# PLAN F1 — PostgreSQL + pgvector + pgBouncer na VM 101 (24/08/2026)

**Fase do:** `PLAN_POSTGRES_MULTITENANT_ATLAS.md` · **Executor:** 🧱 Pedreiro · **Aprovado:** Herbert

## Objetivo

Subir a infraestrutura de banco relacional na VM 101 (o "cubo mágico") — **PostgreSQL 16 + pgvector + pgBouncer** em container, com **backup lógico diário**. Base para a migração do Mnemosyne (F2+) e multi-tenant (F5).

## Execução

| Item | Detalhe |
|---|---|
| **Container PG** | `prometheus-pg` — imagem `pgvector/pgvector:pg16`, `restart=unless-stopped`, porta **5432**, volume `prometheus-pg-data`, DB `prometheus_memory`, user `prometheus` |
| **Senha** | gerada na VM (`openssl rand -hex 24`) → `PROMETHEUS_PG_PASSWORD` no `/opt/prometheus/.env` (+ `.env.bak.<ts>` antes) |
| **pgBouncer** | `prometheus-pgbouncer` — `edoburu/pgbouncer`, porta **6432**, `POOL_MODE=transaction`, `MAX_CLIENT_CONN=200`, `DEFAULT_POOL_SIZE=20` |
| **Backup diário** | `/usr/local/bin/backup-pg.sh` (`docker exec pg_dump -F c`) + cron **02:30** → `/data/pg-backups/` (retenção 7) |

## Critérios de aceite (F1)

1. `psql` OK → **PostgreSQL 16.15** · `CREATE EXTENSION vector` → **pgvector 0.8.6** ✅
2. Container `prometheus-pg` **Up** (restart unless-stopped — sobe no boot) ✅
3. pgBouncer **Up** na 6432 ✅
4. Backup diário roda (teste 1x → `BACKUP_PG_OK`, 4KB — DB ainda vazio, sem dados migrados) ✅

## Próxima fase

**F2 — Backend PG do Mnemosyne core** (recall/store/sleep/graph sobre PG; a interface "PostgreSQL-ready" do roadmap).
