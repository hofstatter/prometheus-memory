# Prometheus-Memory: PostgreSQL Multi-Tenant + Atlas Librarian

**Status:** ✅ COMPLETE (F-1 → F8) · **Date:** 24/08/2026 · **Repository:** prometheus-memory

## What was delivered

The Prometheus-Memory evolved into a **multi-tenant, PostgreSQL-backed memory bank** managed by **Atlas** — the librarian agent:

| Phase | Delivery |
|---|---|
| F-1 | Full backup + clone of VM 101 (vzdump 5.7GB + clone 901, stopped — restore point) |
| F0 | Storage audit (85 tables → `docs/SCHEMA_INVENTORY.md`) |
| F1 | PostgreSQL 16.15 + pgvector 0.8.6 + pgBouncer (container, daily backup) |
| F2 | Multi-tenant schema + `pg_backend.py` (D13: PG = Prometheus-Memory storage) |
| F3 | Sidecar `prometheus_*` in PG (14 tables, 733 records migrated) |
| F4 | `PGSQLiteCompat` adapter + mirror validation (cron 03:30) |
| F5 | **Auth Gateway** — unique API key per agent (SHA-256, revoke immediate) + RLS 18/18 |
| F6 | Atlas reflex arc — reflex 1.2ms + async deep analysis |
| F7 | Atlas DBA + mirror neurons (13 behavior patterns) + synapse (18 graph edges) |
| F8 | L3 persona per tenant (DeepSeek) + observability (`pm_usage.py`) |

## Key features

- **Multi-tenant:** `tenant_id` in all tables + RLS (18/18, FORCE) with role `prometheus_app`.
- **Auth:** every agent (Hermes, OpenClaw, OpenCode, Codex...) gets a unique API key via `pm-key`.
- **Atlas:** reflex arc (fast recall + async LLM), data engineer (ANALYZE/VACUUM), mirror neurons (behavior modeling), synapse (agent↔project graph), L3 persona.

## Not versioned (production-only)

`.env` (VM), `pg_config.json`, real systemd units, cron scripts (`backup-pg.sh`, `pg-mirror.sh`) — see `docs/SCHEMA_INVENTORY.md` §6.
