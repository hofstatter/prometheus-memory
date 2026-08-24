# RELATÓRIO — F-1 (Backup+Clone) + F0 (Auditoria) — Plano PG Multi-tenant Atlas (24/08/2026)

**Status:** ✅ F-1 e F0 **CONCLUÍDOS** · **Executor:** 🧱 Pedreiro · **Próxima fase:** F1 (PG na VM 101)

## F-1 — Ponto de restauração (backup total + clone) ✅

| Item | Resultado |
|---|---|
| **vzdump** (backup arquivo) | ✅ `vzdump-qemu-101-2026_08_24-17_32_09.vma.zst` (**5.73GB**, zstd) em `/dados-hdd/backups/dump/` (backup-hdd) · 20GB brutos, 51% zeros · "Backup job finished successfully" |
| **Clone full** | ✅ `qm clone 101 901 --full --name prometheus-clone-restore-20260824` → VM **901** · disco `local-zfs:vm-901-disk-0` (20G) |
| **Status do clone** | ✅ **stopped** (desligada/inativa — reserva de emergência) |
| **Espaço** | local-zfs 848GB livres · backup-hdd 2.23TB livres (verificado antes) |

> **Reserva:** VM **901** desligada (ponto de restauração vivo) + arquivo vzdump (para `qmrestore`). **NÃO ligar** a 901.

## F0 — Auditoria de storage ✅

- **85 tabelas** mapeadas (core Mnemosyne L0-L3 + sidecar `prometheus_*` + RAG + FTS5 + sqlite-vec) → `prometheus-memory/docs/SCHEMA_INVENTORY.md`.
- **Confirmações técnicas:**
  - `working_memory` (30 cols) e `episodic_memory` (31 cols) são as tabelas centrais (L1/L2) — ganharão `tenant_id`.
  - Vetores: sqlite-vec (`vec_working*`, `vec_episodes*`, `vec_facts*`, `vec_chunks*` — extensão `vec0`, erro "no such module: vec0" sem a extensão) → **pgvector (384d, HNSW)**.
  - Full-text: FTS5 (`fts_working*`, `fts_episodes*`, `fts_facts*`, `notes_fts*`) → **tsvector + GIN**.
  - Sidecar: 14 tabelas `prometheus_*` + 3 `rag_*` (definidas em `web/prometheus_db.py`, schema idempotente SQLite).
  - Grafo: `triples` + `graph_edges` → `tenant_id`.
  - Auth (novo): `tenants` + `agents` (api_key_hash, channel_id, revoked_at).

## Artefatos

- **PLAN:** `prometheus-memory/PLAN_POSTGRES_MULTITENANT_ATLAS.md`
- **Inventário:** `prometheus-memory/docs/SCHEMA_INVENTORY.md`
- **Backup rotina:** `~/backups/herbert/pg-multitenant-atlas-f1-f0/20260824-173206/`
- **Backup VM 101:** `/dados-hdd/backups/dump/vzdump-qemu-101-2026_08_24-17_32_09.vma.zst` · **Clone:** VM 901 (stopped)
- STATE/CONTEXT atualizados · pm_event + Mnemosyne registrados

## Próximas fases (aguardando nova sessão)

F1 (PG:16 + pgvector + pgBouncer) → F2 (backend PG core) → F3 (sidecar PG) → F4 (migração+espelho) → F5 (multi-tenant+auth) → F6-F8 (Atlas avançado).
