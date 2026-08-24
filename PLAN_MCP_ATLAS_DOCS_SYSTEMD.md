# PLAN — Migrar Atlas MCP (:8768) + Docs MCP (:8767) para systemd (24/08/2026)

**Data:** 24/08/2026 ~16:54 · **Executor:** 🧱 Pedreiro · **Aprovado:** Herbert

## Objetivo

Fazer o **Atlas MCP** (:8768) e o **docs MCP** (:8767) subirem **automaticamente no boot da VM 101** (antes rodavam via `nohup` manual — morriam a cada reboot do R620 e exigiam restart manual).

## Contexto

- Após o reboot do R620 (recuperação do pool dados-hdd), os serviços `nohup` do Atlas/docs **morreram**; VMs (onboot=1), Mnemosyne (docker unless-stopped) e atlas-loop (systemd) subiram sozinhos — mas Atlas MCP/docs não.
- Verificação confirmou: 3 camadas de auto-start já existentes (Proxmox onboot / docker / systemd) + lacuna no Atlas MCP/docs.

## Execução

| Passo | Detalhe |
|---|---|
| Units criadas | `atlas-mcp.service` (ATLAS_MCP_PORT=8768, ATLAS_DIARIO_DB=/data/atlas) + `docs-mcp.service` (DOCS_MCP_PORT=8767, DOCS_DIR=/data/docs) — `EnvironmentFile=/opt/prometheus/.env`, `User=root`, `Restart=on-failure` |
| Deploy | scp → `/etc/systemd/system/` → `daemon-reload` → `enable` → `start` |
| Limpeza | mortos os processos `nohup` antigos (padrão seguro `[a]tlas`/`[d]ocs` — o `pkill -f` com string literal matava o próprio shell do ssh) |
| Teste | `systemctl restart` → `active` + HTTP 200 nas 2 portas |

## Critérios de aceite

1. `atlas-mcp.service` e `docs-mcp.service` → **enabled + active**.
2. `:8768` e `:8767` → **HTTP 200** (após restart).
3. No próximo boot da VM, os 4 serviços sobem sozinhos (docker, atlas-loop, atlas-mcp, docs-mcp).
4. Sem processos `nohup` duplicados.
