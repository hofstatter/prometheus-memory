# PLAN F6 — Atlas Arco Reflexo (2 velocidades sobre PG) (24/08/2026)

**Fase do:** `PLAN_POSTGRES_MULTITENANT_ATLAS.md` · **Executor:** 🧱 Pedreiro · **Aprovado:** Herbert

## Objetivo

Formalizar o Atlas como **arco reflexo**: (1) **REFLEXO** — resposta em milissegundos (percepção + recall + ações sem LLM, com cache) · (2) **PROFUNDO** — análise/consolidação LLM **assíncrona** (não bloqueia o reflexo). Tudo com o PG como fonte de recall rápido.

## Execução

| Item | Detalhe |
|---|---|
| **Medição PG** | count **2.58ms** · full-text (GIN) **4.44ms** · **vetorial (HNSW) 2.67ms** — todos < 5ms (alvo 50ms) ✅ |
| **`atlas_loop.py` refinado** | `_pg_recall()` (recall full-text PG multi-tenant, **cache TTL 30s**, sem LLM) · `_disparar_profundo()` (ações LLM — consolidar/insight/conectar — em **thread daemon**) · `_cache_get/_cache_set` |
| **main()** | reflexo síncrono (ações sem LLM) + profundo assíncrono + log do tempo do ciclo + amostra do `pg_recall` a cada 10 ciclos |
| **Deploy** | `atlas_loop.py` → `~/atlas-scripts/` + `PROMETHEUS_PG_URL` no `/opt/prometheus/.env` + `systemctl restart atlas-loop` |

## Critérios de aceite (F6)

1. Tempos do PG < 50ms (medidos: < 5ms) ✅
2. Reflexo do loop < 50ms (medido: **1.2-1.4ms**) ✅
3. Profundo assíncrono (consolidar em thread — não bloqueia o ciclo) ✅
4. Cache de recall ativo (TTL 30s) ✅

## Próxima fase

**F7 — Atlas DBA + neurônios-espelho + sinapse (grafo)** (antecipar padrões + conectar agentes).
