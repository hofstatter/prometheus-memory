# PLAN P6 — Prometheus Memory em Docker (1 container all-in-one)

- **Classificação:** MEDIUM · **Estado:** ARTEFATOS PRONTOS (07/08/2026) — migração AGENDADA para o usuário
- **Aprovado por Herbert:** modelo B — dados em **volume Docker nomeado** (`prometheus-data`); harnesses
  (OpenCode/Claude/Cursor/Codex) conectam via **MCP :8765 / API :8777** (rede — igual hoje)
- **Decisões:** 1 container all-in-one (supervisord com 5 processos) · coletor de telemetria DENTRO do
  container (lê OpenCode do host via binds read-only) · cron L2/L3 dentro do container

---

## Arquitetura final

```
┌────────── container: prometheus-memory (all-in-one) ──────────┐
│  supervisord:                                                 │
│  ├─ prometheus-web   :8777 (gunicorn — UI + API)              │
│  ├─ mnemosyne-mcp    :8765 (MCP SSE, token bytex-memory-...)  │
│  ├─ mnemosyne-api    :8766 (REST + embeddings fastembed)      │
│  ├─ telemetry loop   (coletor P5.1, a cada 5 min)             │
│  └─ cron L2/L3       (memory_aggregator 6h, persona weekly)   │
│                                                               │
│  prometheus-data (VOLUME DOCKER NOMEADO — dono dos dados)     │
│   └─ /data/mnemosyne (DB, grafo, persona, refs, models, cfg)  │
│  binds read-only (host):                                      │
│   ├─ ${HOME}/Projetos        → /data/projetos (painel: git/compose) │
│   ├─ ~/.config/opencode → /telemetry/config (coletor)         │
│   └─ ~/.local/share/opencode → /telemetry/share (coletor)     │
└───────────────────────────────────────────────────────────────┘
        ▲ MCP SSE :8765 · API :8777 · Web :8777 (rede — sem mudança no OpenCode)
```

## Fases

| Fase | Ação | Aceite |
|---|---|---|
| P6.0 | Backup verificado (B1 já feito: tarball + sha256 DB `c298da…` no NVMe) | ✅ feito |
| P6.1 | `Dockerfile` multi-stage + `.dockerignore` | `docker build` verde |
| P6.2 | `docker-compose.yml` (volume nomeado + 3 binds + envs) + `supervisord.conf` | `docker compose config` válido |
| P6.3 | **Migração (a executar QUANDO o usuário decidir):** 1) backup do DB; 2) copiar `${HOME}/.hermes/mnemosyne` → volume (`docker run --rm -v prometheus-data:/data -v ${HOME}/.hermes/mnemosyne:/src alpine cp -a /src/. /data/`); 3) sha256 do DB no volume == `c298da…`; 4) `docker compose up -d`; 5) verificar `/health` 200 + grafo **232 nós/501 arestas** + painel personas + MCP com token; 6) `systemctl --user disable --now prometheus-web mnemosyne-mcp mnemosyne-api` (NÃO deletar); 7) manter `${HOME}/.hermes/mnemosyne` por 7 dias | integridade 100% |
| P6.4 | Rollback (se falhar): religar systemd → container para → tudo volta < 1 min | rollback testável |
| P6.5 | Após 7 dias estáveis: remover systemd + atualizar docs (README Docker) | decisão do usuário |

## Riscos / armadilhas

- **UID 1000:1000** no Dockerfile (herbert) — sem corrupção de permissão no SQLite (binds leem os repos do host)
- `sqlite-vec` precisa de libs nativas — instalar `libsqlite3-dev` na imagem
- `fastembed` baixa modelo na 1ª execução — pré-aquecer no build ou montar cache
- Coletor lê `opencode.db` (WAL) — bind read-only do `~/.local/share/opencode` é seguro (uri mode=ro)
- Cron no container: usar `crond` (debian) ou loop no supervisord — decidir: **supervisord + crond**
- Nunca `--delete` nos binds; volume nomeado é gerenciado pelo Docker
- .env do container: copiar de `~/.Projetos/web/.env` (nunca versionar)
