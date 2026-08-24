# PLAN F8 — L3 Persona por Tenant + Observabilidade (24/08/2026) — FASE FINAL

**Fase do:** `PLAN_POSTGRES_MULTITENANT_ATLAS.md` · **Executor:** 🧱 Pedreiro · **Aprovado:** Herbert

## Objetivo

Fechar o plano: **persona L3 por tenant** (perfil de cada usuário/cliente) + **observabilidade** (painel/relatório de uso multi-tenant).

## Execução

| Item | Detalhe |
|---|---|
| **`persona_l3.py`** | `synthesize_tenant`/`synthesize_all` — coleta do PG (projetos, agentes, eventos, memórias) → sintetiza persona (DeepSeek se `DEEPSEEK_API_KEY`, fallback estatístico) → grava em `working_memory` (source=`persona_l3`, importance **0.95**, tsvector) · upsert por tenant |
| **`pm_usage.py`** | relatório de observabilidade: por tenant → agentes (ativos/total), projetos, memórias, eventos, sinapses, última atividade |
| **`atlas_loop.py`** | ciclo-longo agora inclui **persona** (DBA + espelho + sinapse + persona) a cada 24h |

## Critérios de aceite (F8)

1. Persona L3 gerada por tenant (2 tenants no teste — via **DeepSeek** no serviço: "Tenant default: forte viés técnico..." / "cliente-teste: ambiente minimalista") ✅
2. Observabilidade: relatório `pm_usage` (2 tenants com agentes/projetos/memórias/eventos/sinapses/atividade) ✅
3. Ciclo-longo completo no serviço: `DBA ok | espelho 13 | sinapse 18 | persona 2 tenants` — reflexo 1.4ms ✅

## Resultado final

**PLANO PG MULTI-TENANT + ATLAS BIBLIOTECÁRIO 100% CONCLUÍDO (F-1 → F8).**
