# Prometheus-Memory: PostgreSQL Multi-Tenant + Atlas Bibliotecario

**Estado:** ✅ COMPLETO (F-1 → F8) · **Fecha:** 24/08/2026 · **Repositorio:** prometheus-memory

## Lo entregado

Prometheus-Memory evolucionó a un **banco de memorias multi-tenant sobre PostgreSQL**, gestionado por **Atlas** — el agente bibliotecario:

| Fase | Entrega |
|---|---|
| F-1 | Backup total + clon de la VM 101 (vzdump 5,7GB + clon 901 apagado — punto de restauración) |
| F0 | Auditoría de storage (85 tablas → `docs/SCHEMA_INVENTORY.md`) |
| F1 | PostgreSQL 16.15 + pgvector 0.8.6 + pgBouncer (contenedor, backup diario) |
| F2 | Schema multi-tenant + `pg_backend.py` (D13: PG = storage de Prometheus-Memory) |
| F3 | Sidecar `prometheus_*` en PG (14 tablas, 733 registros migrados) |
| F4 | Adaptador `PGSQLiteCompat` + espejo de validación (cron 03:30) |
| F5 | **Auth Gateway** — API key única por agente (SHA-256, revocación inmediata) + RLS 18/18 |
| F6 | Arco reflejo de Atlas — reflejo 1,2ms + análisis profundo asíncrono |
| F7 | Atlas DBA + neuronas espejo (13 patrones) + sinapsis (18 aristas) |
| F8 | Persona L3 por tenant (DeepSeek) + observabilidad (`pm_usage.py`) |

## Características clave

- **Multi-tenant:** `tenant_id` en todas las tablas + RLS (18/18, FORCE) con rol `prometheus_app`.
- **Auth:** cada agente (Hermes, OpenClaw, OpenCode, Codex...) recibe API key única vía `pm-key`.
- **Atlas:** arco reflejo (recall rápido + LLM asíncrono), ingeniero de datos (ANALYZE/VACUUM), neuronas espejo (modelado de comportamiento), sinapsis (grafo agente↔proyecto), persona L3.

## No versionado (solo producción)

`.env` (VM), `pg_config.json`, units systemd reales, scripts de cron (`backup-pg.sh`, `pg-mirror.sh`) — ver `docs/SCHEMA_INVENTORY.md` §6.
