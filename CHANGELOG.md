# Changelog

## [0.3.0-dev] — 2026-08-03

### GIT GATE (Regra 20 — fluxo de confirmação)
- 🔒 **GIT GATE ativo**: nenhum `git push` sem revisão do Inspetor + **confirmação SIM/NÃO do Inspetor** (identificado "🔍 Inspetor"), 1 por push. `pre-push` hook bloqueia sem `.git/PUSH_APPROVED`. Docs/features não implementadas não sobem ao git. Nunca apagar plano sem ordem explícita.

### Implementado — Canvas v2 por projeto

- 🧭 **`scripts/canvas_generator.py`** (novo): Mermaid **multi-projeto** (`flowchart TD` + `subgraph` por `project_slug`) — nós por evento (`event_type`/`status_hint` → classes done/doing/blocked/backlog, máx 5/projeto), arestas pontilhadas entre projetos pelo mesmo agente, sanitização de títulos, **fallback v1** (`memory_aggregator.generate_mermaid_canvas`) quando sem eventos, `mode_of()` (projects/legacy), `_WEB_CANDIDATES` p/ repo/prod/cron.
- 🌐 **API**: `/api/canvas` adiciona `mode` (backward compat `{mermaid, age}`) + novo `GET /api/canvas/projects` (boards com progresso).
- 🖥️ **UI**: `web/static/canvas.js` (novo) + `index.html` — **chips de projeto** (nome + % + "Todos"), **legenda** done/doing/blocked/backlog, **highlight de subgraph** (dim 0.15), **cross-link** "🗂️ ver painel do projeto" (nó → aba Projetos com projeto selecionado); zoom mantido; `data-*`+delegação; `escapeHtml`.
- 🔌 **Hook** no `memory_aggregator.py` (2 pontos → `canvas_generator.main()`); v1 preservado como fallback.
- 🔍 **Revisão Inspetor: APROVADO** (62 testes) — 4 fixes: id único de nó (`_sid[:8]`), comentários de path, match bidirecional de label (truncamento 30 chars), teste de integração T5 do `/api/canvas`.
- ✅ **Testes**: `tests/test_canvas_generator.py` T1-T5 — **62 passed, 1 skip**. Smoke: 2 projetos → subgraphs EVSCAR/PROVADOR renderizados no navegador com chips+legenda.
- 🚀 **Produção sincronizada** (`app.py`, `index.html`, `canvas.js`, `canvas_generator.py` → `web/scripts` + `~/bin`) + `prometheus-web` reiniciado (health 200). Produção em `mode: legacy` (fallback v1) até eventos reais.

### Planejamento
- 📋 `docs/PLAN_CANVAS_V2_POR_PROJETO.md` criado: **Canvas v2 por projeto** — `scripts/canvas_generator.py` (subgraphs por `project_slug` via `flowchart TD`, fallback v1), `/api/canvas` com `mode`, `/api/canvas/projects`, `static/canvas.js` (chips/legenda/detalhe/cross-link para a aba Projetos), hook no aggregator, testes T1-T4. Aprovado por Herbert — aguarda sessão Pedreiro.

## [0.2.0-dev] — 2026-08-03

### Ativado — Mem0 na produção (03/08)

- ⚡ **`LLM_BACKEND=deepseek`** no `.env` da produção (mesma chave `DEEPSEEK_API_KEY`) — a extração Mem0 agora roda de verdade: `infer=true` → **`degraded:false`, fatos extraídos pelo DeepSeek** (smoke: 2 fatos de 1 frase), **dedup por hash funcionando** (repetição → `skipped_duplicates:2`), **entidades gravadas**.
- 🐛 **Fix deploy**: `web/extractor.py` resolve o diretório `scripts/` em 2 candidatos (`parent/scripts` p/ produção `~/Projetos/web/scripts` + `parent.parent/scripts` p/ repo) — antes a produção importava `~/Projetos/scripts` (inexistente) e degradava sempre.
- 🔧 `scripts/llm_backend.py`: modelo parametrizado via `DEEPSEEK_MODEL` (default `deepseek-chat`) — permite apontar a V4 Flash por extenso sem mexer em código.
- ⚠️ Entidades v1 são heurísticas (ex.: "Mini" em vez de "MiniMax") — NER via LLM fica para v1.1.

### Implementado — Fase D (docs 4 idiomas + release)

- 📚 **Docs atualizados**: `README.md` EN (features v0.2, diagrama 7 abas, API REST expandida, screenshots) + espelho `docs/lang/README.pt-BR.md` + `docs/lang/README.zh-CN.md` + resumo `docs/lang/README.es.md` · `docs/QUICKSTART.md` (7 abas) · `ARCHITECTURE.md` (módulos novos + lanes) · `COMPARISON.md` (7 abas).
- 🎨 `docs/DESIGN_PROJECTS.md` (novo) — design tokens/read do painel Projetos (super-designer).
- 📸 `docs/SCREENSHOTS/projetos.png` capturado (varredura Playwright 03/08).
- 🐛 **Fix (varredura visual)**: `start_session` agora recalcula o relatório do projeto → `active_sessions`/presença no board corretos (era 0 com sessão ativa).
- 🚀 Release: merge `feat/pm-projetos-a0` → `main` + tag `v0.2.0-projetos` + push GitHub (chave nova).

### Implementado — Fase C (Mem0 parity essencial)

- 🧠 **`web/extractor.py`** (novo): extração LLM **single-pass** estilo Mem0 V3 — prompt com "Recently Extracted"/"Existing Memories" (contexto real do canal, fix Inspetor), **grounding temporal** ("hoje/ontem/amanhã/há N dias/semana passada" → datas absolutas, também pós-extração), parsing JSON tolerante + fallback por linhas, retry 2x; usa `scripts/llm_backend.call_llm` (correção C4 — função real, respeita `LLM_BACKEND`).
- 🔁 **`web/dedup.py`** (novo): SHA-256 normalizado (128 bits, doc de propósito não-cripto), **scoped por channel** (`prometheus_dedup_hashes`, PK channel+hash), batch `record_hashes` (1 conexão).
- 🏷️ **`web/entity_store.py`** (novo): entidades heurísticas (capitalizadas) + linkage `prometheus_entities`/`prometheus_memory_entities` (v1; NER LLM em v1.1).
- 🧬 **`web/memory.py`**: `remember_inferred` (extração → dedup → storage; **fallback degraded** grava raw se LLM off — nunca perde write) + `apply_threshold` (P0c — recall híbrido com threshold). Backward compat `remember`/`recall` intactos.
- 🌐 **API**: `POST /api/memory/remember` com `infer` + `project_slug` (lane `proj:<slug>`) → resposta `{ids, stored, skipped_duplicates, degraded}`; `POST /api/memory/recall` com `threshold` (top_k inválido → 400); `GET /api/pm/entities` + `GET /api/pm/entities/<name>/memories`.
- 🔍 **Revisão Inspetor: APROVADO** (57 testes) — M1 corrigido (contexto real no prompt, não hashes), M2 (top_k 400), M3 (batch record_hashes), N1/N2 (doc truncamento + re-grounding pós-extração).
- ✅ **Testes**: `tests/test_mem0_patterns.py` C1-C7 — **57 passed, 1 skip**. Smoke: infer sem LLM → degraded raw + project_slug; backward compat; threshold 0.9 filtra recall.
- 🚀 **Produção sincronizada** (7 arquivos) + `prometheus-web` reiniciado (health 200).

### Implementado — Fase B (Skills por projeto)

- 🧩 **`web/skills_builder.py`** (novo): detecção de padrões em eventos do projeto (MIN_EVIDENCE=3, stoplist de verbos comuns, janela 30d) → **skill DRAFT** com `evidence_json` + confidence escalonada 0.5→0.8; **aprovação humana obrigatória** (`draft→active`, re-aprovação rejeitada); **promoção p/ global** (active com mesmo nome em 2+ projetos); `mark_used` (use_count/last_used_at).
- 🗄️ Tabela sidecar `prometheus_skills` (id PK, **UNIQUE (project_slug, name)** — idempotência em concorrência; fix Inspetor) — NÃO altera o registry global `skills` (name PK).
- 🌐 Endpoints: `POST /api/pm/projects/<slug>/skills/suggest` · `GET .../skills` · `POST /api/pm/skills/<id>/approve` · `POST /api/pm/skills/<id>/mark-used` · `GET /api/pm/skills/promotions`.
- 🖥️ **UI**: seção "🧩 Skills do projeto" — cards draft (amarelo, botão Aprovar) / active (verde), evidências, confiança, candidatas a promoção; botões via `data-pm-action`/`data-sid` + delegação; **fix XSS no cardHTML** (onclick → `data-eid` + delegação).
- 🔍 **Revisão Inspetor: APROVADO** (50 testes) — 3 correções: UNIQUE INDEX, XSS cardHTML, rota mark-used + import json no topo.
- ✅ **Testes**: `tests/test_skills_builder.py` B1-B5 — **50 passed, 1 skip**. Smoke: padrão "osm sync" → draft `estacao` (4 evidências) → approve → active.
- 🚀 **Produção sincronizada** (`skills_builder.py`, `pm_routes.py`, `prometheus_db.py`, `projects.js`, `i18n.js`) + `prometheus-web` reiniciado (health 200).

### Implementado — Fase A3 (Stack & Runtime)

- 🧱 **`web/tech_profile.py`** (novo): análise por **bytes** estilo GitHub linguist (exclui node_modules/.next/dist/__pycache__/volumes; docs e config contados separados do % de código); **frameworks monorepo-aware** (package.json/requirements.txt/pyproject.toml na raiz + subdirs de 1º nível); **DBs** de docker-compose + `DATABASE_URL`; **containers** via `docker ps` (timeout 6s, falha silenciosa); **git** read-only (branch/remote/5 commits/dirty ou `tracked:false` → badge "não versionado").
- 🗄️ Tabela `prometheus_tech_profile` (cache) + upsert idempotente + `scan_duration_ms`.
- 🌐 Endpoints: `GET /api/pm/projects/<slug>/stack` (cache) · `POST .../stack/scan` (re-análise) · `GET .../git` · `GET .../runtime`.
- 🖥️ **UI**: seção "🧱 Stack & Runtime" — barra de linguagens colorida (estilo GitHub) + legenda, chips de frameworks/DBs, bloco de containers (nome/status/portas), bloco git (branch, remote, dirty, commits ou "⚠ Não versionado"); botões via event delegation `data-pm-action` (fix Inspetor — sem slug no onclick).
- 🔍 **Revisão Inspetor: APROVADO** (45 testes) — 3 MENOR corrigidos: delegação de clique (data-slug), código morto (`void c`), `_project_dir` com `.resolve()` + containment.
- ✅ **Testes**: `tests/test_tech_profile.py` S1-S5 — **45 passed, 1 skip** (git no CI). Smoke real EVSCAR: TypeScript 90.9% · Next 16/React 19/Prisma/Tailwind + FastAPI · PostgreSQL/Redis/Meilisearch/MinIO · 5 containers · git "não versionado".
- 🚀 **Produção sincronizada** (`tech_profile.py`, `pm_routes.py`, `prometheus_db.py`, `projects.js`, `i18n.js`) + `prometheus-web` reiniciado (health 200).

### Implementado — Fase A2 (Conexões & Custos)

- 🔑 **`web/connections_registry.py`** (novo): scan read-only do `.env` (só NOMES + fingerprint SHA-256 de 16 hex — **valor nunca armazenado/exposto**); exclusão automática de `~/Projetos/web` (produção); detecção de **chave compartilhada** entre projetos (mesmo fingerprint); alertas **"pago e sem uso"** (>30d) e **"expirando"** (<30d); resumo financeiro global (custo/mês, unused, expiring).
- 🗄️ Tabela `prometheus_connections` no schema sidecar (kind, fingerprint, billing_type, cost_usd_month, expires_at, last_used_at, status, source).
- 🌐 Endpoints: `GET/POST /api/pm/projects/<slug>/connections`, `POST .../connections/scan`, `POST /api/pm/connections`, `PUT /api/pm/connections/<id>`, `GET /api/pm/connections/summary`.
- 🖥️ **UI**: seção "🔑 Conexões & Custos" na aba Projetos — tabela com fingerprint mascarado, badges de billing/alertas, re-scan, formulário de nova conexão e edição de billing (PUT não muta fingerprint/env_var — fix Inspetor).
- 🔍 **Revisão Inspetor: APROVADO** (41 testes) — 1 MAJOR corrigido (whitelist do PUT sem fingerprint/env_var) + 2 MENOR (esc() no cost; N+1 no summary) + validação de projeto órfão no POST.
- ✅ **Testes**: `tests/test_connections.py` C1-C5 — **41 testes verdes** (36 + 5). `node --check` OK.
- 🚀 **Produção sincronizada** (`connections_registry.py`, `pm_routes.py`, `prometheus_db.py`, `projects.js`, `i18n.js`) + `prometheus-web` reiniciado (health 200).

### Implementado — Fase A (aba Projetos na UI)

- 🗂️ **Aba `🗂️ Projetos`** na UI (`web/templates/index.html`): botão no nav, `#projects-view` (sidebar boards + main + drawer), integrada ao `resetViews()`/deep-link `#projects`.
- 📊 **`web/static/projects.js`** (novo): sidebar de boards com barra de progresso, kanban read-only (Backlog/Em andamento/Concluído + badge BLOQUEADO), timeline horizontal, KPIs, **presença em tempo real** (polling 10s, dots active/idle/stale), drawer de detalhes com memória canônica.
- 🌐 **i18n** EN/PT/ES/ZH para a nova aba (`web/static/i18n.js`).
- 📨 **`GET /api/pm/projects/<slug>/events`** (novo) + `list_events()` — alimenta kanban/timeline; timestamps com microssegundos (ordem correta mesmo no mesmo segundo).
- ✅ **Testes**: `test_t9_list_events` — **36 testes verdes** (35 + 1). `node --check` no projects.js OK.
- 🚀 **Produção sincronizada** (`~/Projetos/web/`: templates, static, pm_routes, projects_registry, session_registry) + `prometheus-web` reiniciado (health 200, `#projects` e `/static/projects.js` OK).

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
