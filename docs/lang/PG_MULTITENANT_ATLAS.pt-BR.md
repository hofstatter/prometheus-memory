# Prometheus-Memory: PostgreSQL Multi-Tenant + Atlas Bibliotecário

**Status:** ✅ COMPLETO (F-1 → F8) · **Data:** 24/08/2026 · **Repositório:** prometheus-memory

## O que foi entregue

O Prometheus-Memory evoluiu para um **banco de memórias multi-tenant sobre PostgreSQL**, gerenciado pelo **Atlas** — o agente bibliotecário:

| Fase | Entrega |
|---|---|
| F-1 | Backup total + clone da VM 101 (vzdump 5,7GB + clone 901 desligado — ponto de restauração) |
| F0 | Auditoria de storage (85 tabelas → `docs/SCHEMA_INVENTORY.md`) |
| F1 | PostgreSQL 16.15 + pgvector 0.8.6 + pgBouncer (container, backup diário) |
| F2 | Schema multi-tenant + `pg_backend.py` (D13: PG = storage do Prometheus-Memory) |
| F3 | Sidecar `prometheus_*` no PG (14 tabelas, 733 registros migrados) |
| F4 | Adapter `PGSQLiteCompat` + espelho de validação (cron 03:30) |
| F5 | **Auth Gateway** — API key única por agente (SHA-256, revogação imediata) + RLS 18/18 |
| F6 | Arco reflexo do Atlas — reflexo 1,2ms + análise profunda assíncrona |
| F7 | Atlas DBA + neurônios-espelho (13 padrões) + sinapse (18 arestas) |
| F8 | Persona L3 por tenant (DeepSeek) + observabilidade (`pm_usage.py`) |

## Recursos principais

- **Multi-tenant:** `tenant_id` em todas as tabelas + RLS (18/18, FORCE) com role `prometheus_app`.
- **Auth:** cada agente (Hermes, OpenClaw, OpenCode, Codex...) recebe API key única via `pm-key`.
- **Atlas:** arco reflexo (recall rápido + LLM assíncrono), engenheiro de dados (ANALYZE/VACUUM), neurônios-espelho (modelagem de comportamento), sinapse (grafo agente↔projeto), persona L3.

## Não versionado (somente produção)

`.env` (VM), `pg_config.json`, units systemd reais, scripts de cron (`backup-pg.sh`, `pg-mirror.sh`) — ver `docs/SCHEMA_INVENTORY.md` §6.
