# PLAN F5 — Multi-tenant + Auth Gateway (24/08/2026)

**Fase do:** `PLAN_POSTGRES_MULTITENANT_ATLAS.md` · **Executor:** 🧱 Pedreiro · **Aprovado:** Herbert

## Objetivo

Isolamento multi-tenant real + **API key única por agente/sessão** para conexão ao Prometheus-Memory (MCP/REST), com emissão manual, validação e revogação imediata.

## Execução

| Item | Detalhe |
|---|---|
| **Auth Gateway** | `web/scripts/auth_gateway.py` — `issue_key` (gera `pm_<tenant>_<token>`, armazena **hash SHA-256**) · `validate_key` → {tenant_id, agent_id, channel_id, harness} · `revoke_agent` (revoked_at → bloqueio imediato) · `list_agents` |
| **CLI** | `scripts/pm_key.py` → `~/.local/bin/pm-key` (issue/validate/revoke/list) |
| **RLS** | `migrations/003_rls.sql` — `ENABLE ROW LEVEL SECURITY` + `FORCE` em 15 tabelas (core + sidecar) com policy `tenant_id = current_setting('app.tenant_id', default '1')` · role **`prometheus_app`** (sem BYPASSRLS — o `prometheus` tem bypass, por isso o RLS não filtrava nele) |
| **API :8766** | `mnemosyne_api.py` `_check_auth()` aceita **token global** (admin) OU **API key de agente** (via auth_gateway) + rota `/whoami` · container atualizado (mnemosyne_api + auth_gateway + `pg_config.json` + psycopg2) |

## Critérios de aceite (F5)

1. Auth Gateway testado: issue (2 tenants) · validate · **revoke imediato** (key revogada → INVALIDO) · list ✅
2. **RLS comprovado:** tenant 2 vê **só o dele** (`proj-cliente2`) · tenant 999 vê **0** · tenant 1 vê 11 ✅
3. API :8766 valida API key de agente (`/whoami` → `{role: agent, tenant_id: 2, agent_id: opencode-02, channel_id, harness}`) ✅
4. CLI pm-key instalado ✅

## Próxima fase

**F6 — Atlas arco reflexo (2 velocidades) sobre PG** (recall <50ms + consolidação assíncrona).
