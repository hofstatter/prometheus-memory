# ROADMAP — Prometheus Memory

> 📋 **Plano detalhado de implementação dos padrões Mem0 V3:** ver `docs/PLAN_MEM0_PATTERNS.md` (aprovado 03/08/2026 — fases M0-M5, prioridade P0=M1 extração+dedup).
> 📋 **Plano da Aba Projetos + Multi-Sessão/Multi-Harness:** ver `docs/PLAN_PROJETOS_MULTI_SESSAO.md` (criado 03/08/2026 — fases A0→D; A0 identidade/sessões é pré-requisito da aba).
> 📋 **Execução da Fase A0 (arquivo-a-arquivo):** ver `docs/PLAN_FASE_A0_EXECUCAO.md` (criado 03/08/2026 — lanes, `/api/pm/*`, Project Resolver v1, testes T1-T7, pronto para sessão Pedreiro).

## v0.1.0 (atual) ✅
Pipeline L0→L3 · Web UI 5 abas + editor · RAG multimodal + OCR · Notes · Offloading · Skills · Hardening pré-release

## v0.2 — Multi-agente & API
- [x] **Fase A0 — identidade/sessões** (executada 03/08, branch `feat/pm-projetos-a0`): lanes `sess:*`/`proj:*`/`agent:*`, envelope de contexto, idempotência `client_event_id`, Project Resolver v1, `/api/pm/*` (sessions/events/projects/report/presence), tabelas sidecar `prometheus_*` — ver `docs/PLAN_FASE_A0_EXECUCAO.md`
- [x] **Fase A — aba Projetos na UI** (executada 03/08): botão `🗂️ Projetos`, `#projects-view`, `web/static/projects.js` (boards sidebar, kanban read-only, timeline, progresso, presença polling 10s, drawer de detalhes), i18n EN/PT/ES/ZH, `GET /api/pm/projects/<slug>/events`. 36 testes verdes. Produção sincronizada.
- [ ] **Aba Projetos** (kanban + timeline + barra de progresso + presença de agentes em tempo real) — `docs/PLAN_PROJETOS_MULTI_SESSAO.md`
- [x] **Fase A2 — Conexões & Custos** (executada 03/08): scan read-only do `.env` (só fingerprint SHA-256, nunca valor), exclusão de `~/Projetos/web`, alertas "pago e sem uso"/"expirando", chave compartilhada entre projetos, resumo financeiro global, endpoints `/api/pm/*/connections*` + `connections/summary`, curadoria na UI. 41 testes verdes. Produção sincronizada.
- [ ] **Conexões & Custos por projeto** (Fase A2): chaves mascaradas, MCPs, assinaturas, alertas "pago e sem uso"/"expirando", resumo financeiro global
- [x] **Fase A3 — Stack & Runtime** (executada 03/08): barra % linguagens por bytes (estilo GitHub, docs/config separados), frameworks monorepo (package.json/requirements/pyproject), DBs (compose/DATABASE_URL), containers (docker ps), git (branch/remote/commits/dirty ou "não versionado"); endpoints `/stack`, `/stack/scan`, `/git`, `/runtime`; cache em `prometheus_tech_profile`. 45 testes. Produção sincronizada.
- [ ] **Stack & Runtime por projeto** (Fase A3): barra % linguagens estilo GitHub, frameworks, DBs, containers, git ("não versionado" incluso)
- [ ] **Multi-sessão/multi-harness**: lanes `sess:*`/`proj:*`/`agent:*` (futuro `team:*`) + envelope de contexto + idempotência por `client_event_id` — Fase A0
- [ ] **MCP de eventos**: `prometheus_session_start/heartbeat/close`, `prometheus_project_event`, `prometheus_project_context` — OpenCode/Claude Code/Codex
- [ ] **Skills por projeto** (`project_slug`, `scope`, `status draft/active`, `evidence_json`) + Skill Builder com aprovação humana — Fase B
- [ ] **`agent_id`/`session_id`** em todo recall/write (isolamento entre agentes, padrão mem0)
- [ ] **MCP server** (padrão dominante 2026) + `POST /api/memory` (remember/recall via REST, matar subprocess+regex)
- [ ] **Backend PostgreSQL** completo via `web/storage.py` (`DATABASE_URL`) + pgvector (HNSW) para tabelas do Prometheus
- [ ] **sqlite-vec `vec0` KNN** no recall de memórias (RAG já usa; resta o caminho de memórias no Mnemosyne upstream)
- [ ] Fila assíncrona de indexing (upload → 202, worker processa)
- [ ] Retries + circuit breaker nas chamadas LLM; métricas `/metrics`
- [ ] FTS5 para busca de notas

## v0.3 — Escala & Inteligência
- [ ] Dedup semântico + retrieval híbrido FTS5/BM25 + semântico + threshold (Mem0 parity — P0c)
- [ ] Decay/eviction de memórias (políticas estilo Letta core/archival; persona imune)
- [ ] Consolidação orientada a eventos (fila) em vez de cron
- [ ] Sharding por agente; particionamento de rag_chunks
- [ ] Harness de eval (LongMemEval) no CI
- [ ] Decisão sobre Mnemosyne core: propor Postgres upstream ou engine própria

## Contexto da auditoria (25/07/2026)
Para o propósito declarado (single-user local-first), a arquitetura SQLite atual é coerente.
Cenário de 100k agentes exige os itens v0.2/v0.3 — não é tuning, é re-arquitetura planejada.
