# PLAN — Push GitHub + Reconciliação de Produção (24/08/2026)

**Executor:** 🧱 Pedreiro · **Aprovado:** Herbert ("Execute 1,2,3 + git") · **GIT GATE:** 🔍 Inspetor ✅ APROVADO + confirmação SIM/NÃO

## Objetivo

Publicar o plano PostgreSQL multi-tenant + Atlas bibliotecário (F-1→F8) no GitHub, reconciliar produção ↔ repo, e documentar em 4 idiomas.

## Passos

| # | Ação | Resultado |
|---|---|---|
| 1 | **Corrigir drift de produção** — redeploy dos 4 scripts stale (`atlas_synapse`, `auth_gateway`, `persona_l3`, `pm_key`) | ✅ **md5 BATEM** (repo = VM/container) · `pm-key list` OK |
| 2 | **Push para o GitHub** (GIT GATE) | ✅ Inspetor ✅ APROVADO + pergunta SIM/NÃO → `git push origin main` → **`5d58965..0f3a0c3`** (6 commits, 64 arquivos, +4536/−70) · marcador criado/removido |
| 3 | **Ressalva B documentada** | ✅ `SCHEMA_INVENTORY.md` §6 — itens não versionados (.env, pg_config.json, units systemd, cron) |
| — | **Docs em 4 idiomas** | ✅ `docs/PG_MULTITENANT_ATLAS.md` (EN) + `docs/lang/*.pt-BR.md`, `*.zh-CN.md`, `*.es.md` |

## Critérios de aceite

1. Produção = repo (4 scripts batem) ✅
2. Push verde (GIT GATE: revisão + confirmação) ✅ · 0 commits à frente ✅
3. Docs em 4 idiomas versionados ✅
4. Sem secrets no push (scan limpo) ✅
