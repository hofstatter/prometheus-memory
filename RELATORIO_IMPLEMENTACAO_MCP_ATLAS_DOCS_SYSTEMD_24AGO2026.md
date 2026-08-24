# RELATÓRIO — Atlas MCP + Docs MCP migrados para systemd (24/08/2026)

**Status:** ✅ **CONCLUÍDO E TESTADO** · **Executor:** 🧱 Pedreiro

## Resumo

O **Atlas MCP (:8768)** e o **docs MCP (:8767)** saíram do `nohup` manual e agora rodam como **serviços systemd `enabled`** na VM 101 — sobem **automaticamente no boot**, como já acontecia com Mnemosyne (docker) e o Atlas loop.

## Por que

Após o reboot do R620 (recuperação do pool dados-hdd), os MCPs Atlas/docs **morreram** (nohup não sobrevive a reboot). VMs, Mnemosyne e o loop subiram sozinhos; Atlas MCP/docs não — exigiam restart manual.

## O que foi feito

1. **Units criadas** (versionadas em `prometheus-memory/web/scripts/`):
   - `atlas-mcp.service` — `ATLAS_MCP_PORT=8768`, `ATLAS_DIARIO_DB=/data/atlas`, `EnvironmentFile=/opt/prometheus/.env`, `User=root`, `Restart=on-failure`.
   - `docs-mcp.service` — `DOCS_MCP_PORT=8767`, `DOCS_DIR=/data/docs`, mesmo padrão.
2. **Deploy na VM 101:** scp → `/etc/systemd/system/` → `daemon-reload` → `enable` (symlinks criados) → `start`.
3. **Limpeza:** processos `nohup` antigos mortos (zero restantes).
4. **Teste de restart** (simula boot): `systemctl restart` → **`active active`** + **HTTP 200** em `:8768` e `:8767`.

## Evidências

- `systemctl is-active atlas-mcp docs-mcp` → **active active**
- `systemctl is-enabled atlas-mcp docs-mcp atlas-loop docker` → **enabled enabled enabled enabled** (os 4 sobem no boot)
- `curl :8768/sse` → **200** · `curl :8767/sse` → **200** (após restart)
- Zero processos `nohup` duplicados

## Lições

- **`pkill -f` com string literal mata o próprio shell do ssh remoto** (o comando contém a string no cmdline) → usar padrão regex seguro `[a]tlas`/`[d]ocs`. Foi a causa dos travamentos de ssh na sessão.
- `EnvironmentFile=/opt/prometheus/.env` funcionou sem problema (linhas inválidas são ignoradas pelo systemd).

## Artefatos

- Units: `prometheus-memory/web/scripts/atlas-mcp.service` + `docs-mcp.service` · instaladas em `/etc/systemd/system/` na VM 101
- PLAN: `prometheus-memory/PLAN_MCP_ATLAS_DOCS_SYSTEMD.md`
- Backup: `~/backups/herbert/mcp-atlas-docs-systemd/20260824-165406/`
- STATE/CONTEXT atualizados · pm_event + Mnemosyne registrados

## Próximos passos

- Próximo reboot do R620: confirmar que os 4 serviços da VM 101 sobem sozinhos (docker → Mnemosyne, atlas-loop, atlas-mcp, docs-mcp).
- Pendências: Bearer auth MCPs atlas/docs · streamable-http · DIMM #0x1b · wait do memtest-run.sh (v2).
