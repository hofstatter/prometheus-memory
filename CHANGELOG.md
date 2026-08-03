# Changelog

## [0.2.0-dev] — 2026-08-03

### Implementado — Fase A0 (identidade de contexto e sessões)

- 🧩 **Lanes de memória** em `web/memory.py`: `sess:<harness>:<session_id>` (efêmera) · `proj:<slug>` (canônica) · `agent:<id>` (backward compat) — `session_id` por agente corrige a colisão de dedup exato entre agentes no Mnemosyne; API pública `remember`/`recall` preservada.
- 🗂️ **Tabelas sidecar** `prometheus_*` (projects, project_events, project_tasks, sessions, events_ingest, project_reports) em `web/prometheus_db.py` — sem ALTER no upstream Mnemosyne.
- 🧠 **Project Resolver v1** (`web/projects_registry.py`): sinais explicit → cwd → git_remote → sessão recente → texto → fallback; `confidence` + `needs_review` (< 0.6 não vira canônico).
- 📨 **Ingest idempotente**: `client_event_id` evita duplicação em retry; evento + memória canônica na lane `proj:<slug>`.
- 📊 **Relatório v1 materializado** (`prometheus_project_reports`): progresso heurístico por weights de event_type, open_issues, last_decision/last_implementation, active_sessions.
- 🟢 **Presença**: `active` < 30s · `idle` 30s-5min · `stale` > 5min · `closed` explícito (heartbeat).
- 🌐 **Blueprint `/api/pm`** (`web/pm_routes.py`): `POST /sessions/{start,heartbeat,close}`, `POST /events`, `GET /projects`, `GET /projects/<slug>/report`, `GET /presence`.
- ✅ **Testes**: `tests/test_session_lanes.py` (T1-T8) — isolamento multi-sessão, lane compartilhada entre harnesses, idempotência, presença/stale (incl. idle→stale), resolver, backward compat, relatório. **35 testes verdes** (27 existentes + 8 novos).
- 🔍 **Revisão Inspetor: APROVADO** — 2 correções MAJOR aplicadas: `slugify` no `_project_exists` (diretórios com maiúsculas) e `presence()` com cálculo temporal incondicional (idle→stale).
- 🚀 **Produção sincronizada** (`~/Projetos/web/`) + `prometheus-web` reiniciado (health 200).
- Docs: `PLAN_FASE_A0_EXECUCAO.md` (execução) · ROADMAP (A0 ✅).

### Planejamento
- 📋 `docs/PLAN_MEM0_PATTERNS.md` criado: plano detalhado (M0-M5) para absorver padrões Mem0 V3 (extração LLM single-pass, dedup hash, entity store, sqlite-vec `vec0` KNN, decay/eviction) preservando diferenciais L0→L3 + Canvas + Persona + Skills. Referenciado no `ROADMAP.md`. Aguarda sessão Pedreiro dedicada (P0 = M1).
- 🗂️ `docs/PLAN_PROJETOS_MULTI_SESSAO.md` criado: Aba Projetos (kanban/timeline/progresso) + multi-sessão/multi-harness via MCP (lanes `sess:*`/`proj:*`/`agent:*`/`team:*`, envelope de contexto, idempotência, presença de agentes em tempo real) + skills por projeto com aprovação humana + análise profunda Mem0 × Prometheus (correções C1-C5, gaps P0/P0b/P0c). Fases A0→D; A0 é pré-requisito.
- 📊 **A2 + A3 incorporados ao plano (03/08):** painel completo por projeto — **A2 Conexões & Custos** (chaves mascaradas com fingerprint, MCPs, assinaturas, alertas "pago e sem uso"/"expirando", resumo financeiro global) e **A3 Stack & Runtime** (barra % linguagens estilo GitHub, frameworks, DBs detectados do compose/DATABASE_URL, containers, git). Ordem: A0→A→A2→A3→B→C→D (~34-48h).
- 🚀 `docs/PLAN_FASE_A0_EXECUCAO.md` criado: plano arquivo-a-arquivo da **Fase A0** (identidade/sessões) — `web/prometheus_db.py` + `projects_registry.py` + `session_registry.py` + alterações em `web/memory.py` (lanes com backward compat) + `web/pm_routes.py` + testes T1-T7 + smoke/rollback. Pronto para sessão Pedreiro dedicada.

### Infra de desenvolvimento (sessão 18 — ecossistema NB02)
- 🏛️ **Fix model ID Arquiteto:** `kimi-for-coding/kimi-for-coding` era **Kimi K2.7 Code** (default do provider); model ID real do K3 é **`kimi-for-coding/k3`** — corrigido em `opencode.jsonc`, `agent/plan.md`, `command/arquiteto.md`, `execution-manifest.json`.
- 📸 **MCP ScreenshotAPI** adicionado ao OpenCode (`~/.config/opencode/mcp-servers/screenshotapi_mcp.py`): captura externa de screenshots/PDF via API paga ($9/mês, 1.000 shots) — alternativa ao Playwright local para o fluxo Visionário.
- 🗂️ **Backup de migração** do ambiente OpenCode: `/run/media/herbert/DADOS/backup-projetos/Opencode/20260803-full/` + guia `~/.config/opencode/docs/MIGRACAO_OPENCODE.md`.

## [0.1.0] — 2026-07-21

### Adicionado
- Pipeline L0→L3 completo (session logger, aggregator, persona synthesizer, skill generator, ref manager)
- Web UI unificada na porta 8777 com 6 abas: Timeline, Grafo (G6.js), Canvas (Mermaid), Documents (RAG), Notes, Editor
- RAG local multimodal: PDF/TXT/MD/DOCX/PNG/JPG com OCR (PyMuPDF + Tesseract)
- Notes: importação por URL com detecção de fonte (GitHub, X, web) e sanitização de Markdown
- Offloading de logs com `ref_manager.py` (refs/*.md + node_id)
- Skill auto-memory para agentes (gravação automática de sessões)
- Instalação em 1 comando via `setup.sh` (deps, cron, systemd)
- Configuração 100% por variáveis de ambiente

### Segurança
- Proteção contra path traversal nos endpoints de Notes
- Proteção SSRF na importação de URLs (apenas http/https públicos)
- Bind padrão em 127.0.0.1
- Nenhuma chave de API no código-fonte
- Escape de HTML na renderização (XSS) e Mermaid `securityLevel: 'strict'`
- Allowlist de extensões e limite de 50MB no upload RAG
