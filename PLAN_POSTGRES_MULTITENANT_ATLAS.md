# PLAN — Prometheus-Memory → PostgreSQL + Multi-tenant + Atlas Bibliotecário

**Data:** 24/08/2026 · **Executor:** 🧱 Pedreiro · **Aprovado:** Herbert (5 decisões + defaults)
**Status:** 🔄 EM EXECUÇÃO — F-1 (backup+clone) ✅ · F0 (auditoria) ✅ · F1-F8 pendentes

## 1. Decisões (fechadas)

| # | Decisão |
|---|---|
| 1 | PG em **container novo na VM 101** (postgres:16 + pgvector + pgBouncer) |
| 2 | Migrar **Mnemosyne core + sidecar `prometheus_*`** (os dois) |
| 3 | Multi-tenant: **tenants = usuários/clientes**; cada **agente tem perfil isolado** (channel); **Prometheus-Memory = banco principal**; **Atlas = bibliotecário** (loop paralelo); **API key única por agente/sessão** via MCP |
| 4 | Neurônios-espelho = **modelagem de comportamento** |
| 5 | **Migrar 100% para PG** (SQLite vira espelho de validação 1 semana, depois desligado — arquivo mantido no lugar) |

**Defaults:** (a) iniciar por F0→F2 · (b) SQLite desligado, arquivo mantido · (c) API key emitida pelo Herbert (CLI/painel) com revogação imediata.

## 2. Arquitetura alvo

```
VM 101 (cubo mágico)
├── 🗄️ PostgreSQL:16 + pgvector + pgBouncer (container, restart unless-stopped, backup lógico diário)
│     └── schema multi-tenant: tenant_id em TODAS as tabelas + RLS
├── 🔐 Auth Gateway — valida Bearer api_key → tenant_id + agent_id + channel_id (antes de toda query)
├── 🧠 ATLAS (bibliotecário) — chave admin (vê/gerencia cross-tenant)
│     · REFLEXO RÁPIDO (ms): recall + dedup + gravação (sem LLM)
│     · ANÁLISE PROFUNDA (batch 3min): consolidação L1→L2→L3 + conexões + lições
│     · ⚙️ engenheiro de dados: índices, VACUUM/ANALYZE, qualidade, Alembic
│     · 🪞 neurônio-espelho: modela comportamento por agente → antecipa
│     · 🔗 sinapse: grafo agente↔memória↔entidade (transferência de conhecimento)
└── 📚 Mnemosyne (L0-L3 sobre PG) + 🖥️ Web UI :8777 (sidecar em PG)
```

## 3. Modelo de dados (resumo — detalhe em `docs/SCHEMA_INVENTORY.md`)

- Core: `working_memory`, `episodic_memory`, `triples`, `graph_edges`, `vec_*` (pgvector 384d), `banks` — **+ tenant_id**.
- Sidecar: `prometheus_*`, `rag_*` — **+ tenant_id**.
- Auth: `tenants(id, name, master_key)` · `agents(id, tenant_id, api_key_hash, harness, channel_id, created_at, revoked_at)`.
- Substituições: sqlite-vec → **pgvector (HNSW)** · FTS5 → **tsvector + GIN** · lock SQLite → **MVCC**.

## 4. Modelo de auth

Cada agente/sessão tem **1 API key única** (Bearer) → gateway resolve tenant+agent+channel → **RLS** isola o canal. Atlas tem chave **admin** (cross-tenant). Revogação: `revoked_at` → bloqueio imediato.

## 5. Fases

| Fase | Objetivo | Critério de aceite |
|---|---|---|
| **F-1** | **Backup total + Clone da VM 101 (ponto de restauração)** | ✅ vzdump (5.73GB em backup-hdd) + clone **901** full **stopped** + verificado |
| **F0** | Auditoria de storage | ✅ `docs/SCHEMA_INVENTORY.md` (85 tabelas mapeadas) |
| **F1** | PG:16 + pgvector + pgBouncer na VM 101 + backup lógico | ✅ PostgreSQL **16.15** + pgvector **0.8.6** (container `prometheus-pg`, :5432) + pgBouncer (:6432) + backup diário 02:30 (`/data/pg-backups/`) — ver `PLAN_F1_PG_VM101.md` |
| **F2** | Backend PG do **Prometheus-Memory** (schema multi-tenant + pgvector/tsvector + `pg_backend.py`) | ✅ schema aplicado (8 tabelas + tenant_id + HNSW + GIN) + backend testado (store/stats) — **D13: Mnemosyne upstream sem backend PG → PG vira storage do Prometheus-Memory** · ver `PLAN_F2_PG_BACKEND.md` |
| **F3** | Sidecar `prometheus_*` em PG (schema + migração + backend) | ✅ 14 tabelas no PG (tenant_id + índices) + **733 registros migrados** + `pg_backend.py` ampliado (smoke OK) — ver `PLAN_F3_SIDECAR_PG.md` |
| **F4** | Migração espelhada (Web UI via adapter PG + espelho 1 semana) | ✅ adapter `PGSQLiteCompat` (smoke ampliado OK) + `get_conn` switch + espelho cron 03:30 · **troca de produção aguarda aprovação** — ver `PLAN_F4_MIGRACAO_ESPELHO.md` |
| **F5** | Multi-tenant + Auth Gateway (API keys + RLS) | ✅ Auth Gateway (issue/validate/revoke, hash SHA-256) + CLI `pm-key` + **RLS comprovado** (tenant 2 isolado, 999→0) + API :8766 valida API key (`/whoami`) — ver `PLAN_F5_MULTITENANT_AUTH.md` |
| **F6** | Atlas arco reflexo (2 velocidades) sobre PG | ✅ reflexo **1.2ms** + recall PG < 5ms (HNSW/GIN) + profundo LLM **assíncrono** (thread) + cache TTL — ver `PLAN_F6_ATLAS_ARCO_REFLEXO.md` |
| **F7** | Atlas DBA + neurônios-espelho + sinapse (grafo) | ✅ `atlas_dba.py` (ANALYZE/VACUUM) + `atlas_synapse.py` (**13 padrões de comportamento de 8 agentes** + **18 arestas**) + ciclo-longo 24h assíncrono no loop — ver `PLAN_F7_ATLAS_DBA_ESPELHO_SINAPSE.md` |
| **F8** | L3 persona + observabilidade | ✅ `persona_l3.py` (persona por tenant via DeepSeek, importance 0.95) + `pm_usage.py` (observabilidade) + ciclo-longo completo — ver `PLAN_F8_L3_PERSONA_OBSERVABILIDADE.md` |

> ## 🏁 PLANO 100% CONCLUÍDO (F-1 → F8, 24/08/2026) — Prometheus-Memory: PostgreSQL multi-tenant + API key por agente + RLS + Atlas bibliotecário (arco reflexo, DBA, neurônios-espelho, sinapse, persona).

## 6. Riscos & mitigação

| Risco | Mitigação |
|---|---|
| Migração grande | F0 auditoria + **F-1 clone/backup** + espelho 1 semana + rollback (SQLite intacto) |
| pgvector recalcular embeddings | manter 384d (fastembed); recalcular só se incompatível |
| Custo LLM do loop crescer | orçamento 20/dia + reflexo sem LLM |
| Concorrência multi-tenant | RLS + pgBouncer + teste de carga (F5) |
| SPOF PG (VM 101) | backup lógico diário + clone 901 reserva + réplica futura |

## 7. Ordem & rollback

**F-1 → F0 → F1 → F2 → F3 → F4 → F5 → F6 → F7 → F8** (gates do Inspetor na fronteira). **Rollback:** SQLite nunca é removido (apontar DATABASE_URL de volta) · clone **901** desligado como reserva · vzdump para `qmrestore`.
