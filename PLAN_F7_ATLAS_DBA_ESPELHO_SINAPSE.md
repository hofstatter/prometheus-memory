# PLAN F7 — Atlas DBA + Neurônios-Espelho + Sinapse (24/08/2026)

**Fase do:** `PLAN_POSTGRES_MULTITENANT_ATLAS.md` · **Executor:** 🧱 Pedreiro · **Aprovado:** Herbert

## Objetivo

O Atlas vira **engenheiro de dados (DBA)** + **neurônio-espelho** (modelagem de comportamento) + **sinapse** (grafo agente↔memória↔entidade) — tudo no loop, assíncrono.

## Execução

| Item | Detalhe |
|---|---|
| **`atlas_dba.py`** | `dba_report()` (counts, dead tuples, last analyze/vacuum por tabela) · `dba_maintain()` (ANALYZE 12 tabelas + VACUUM — autocommit, pois VACUUM não roda em transação) |
| **`atlas_synapse.py`** | `mirror_patterns()` — **neurônios-espelho**: eventos por agente → padrão dominante → triples `(agent:<id>, costuma_fazer, <tipo>:em:<projeto>)` · `sync_synapse()` — arestas `(agent:<id>, atuou_em, proj:<slug>)` · `query_synapse(tema)` — quem sabe o quê |
| **`atlas_loop.py`** | `_disparar_ciclo_longo()` — DBA + espelho + sinapse a cada **24h** (state `last_ciclo_longo`), em **thread** (assíncrono) + registro no diário (kind `dba`) |
| **Deploy** | `atlas_loop.py` + `atlas_dba.py` + `atlas_synapse.py` → `~/atlas-scripts/` + **psycopg2 no atlas-venv** + `PROMETHEUS_PG_URL` corrigida no `.env` (senha 48 chars) + restart |

## Critérios de aceite (F7)

1. DBA roda (ANALYZE 12 tabelas + VACUUM) ✅
2. **Espelho:** 13 padrões de comportamento de 8 agentes (ex: `agent:opencode costuma_fazer implementation:em:prometheus-memory`) ✅
3. **Sinapse:** 18 arestas agentes↔projetos + `query_synapse("opencode")` retorna os padrões ✅
4. Ciclo-longo roda no serviço, assíncrono (reflexo continua 1.5ms) ✅

## Próxima fase

**F8 — L3 persona + observabilidade** (persona por tenant + painel de uso).
