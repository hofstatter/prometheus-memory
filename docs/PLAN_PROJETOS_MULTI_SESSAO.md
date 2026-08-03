# PLAN — Aba Projetos + Multi-Sessão/Multi-Harness (Prometheus Memory v0.2)

> **Data:** 03/08/2026
> **Autor:** Arquiteto (Kimi K3) + Pedreiro (DeepSeek V4 Flash)
> **Aprovado por:** Herbert (pedido direto — defaults assumidos, ver §13)
> **Classificação:** MEDIUM (floor de segurança: UI + DB + MCP + release/GitHub)
> **Status:** Plano criado — aguarda execução faseada (A0 → A → B → C → D)
> **Dependências:** Prometheus v0.1.0+ · Mnemosyne 3.12.2+ · OpenCode restart (Tavily) · chave GitHub rotacionada
> **Backup pré-implementação:** `~/backups/prometheus-memory/plan-projetos-multi-sessao/20260803-154529/`

---

## 1. Objetivo

Transformar o Prometheus Memory em um **sistema operacional de múltiplos projetos simultâneos**:

1. **Nova aba "Projetos"** na Web UI (:8777) com relatório visual por projeto (kanban, timeline, barra de progresso, presença de agentes em tempo real) gerado automaticamente a partir das memórias/eventos dos agentes.
2. **Multi-sessão e multi-projeto**: o usuário pode abrir várias sessões do mesmo harness (ex.: 2 janelas do OpenCode) ou harnesses diferentes (OpenCode + Claude Code + Codex) trabalhando em projetos diferentes, **sem que os agentes confundam ou esqueçam** o projeto em que estão.
3. **Memórias sempre atualizadas e consistentes** entre harnesses via MCP.
4. **Skills por projeto**: algoritmo que analisa o contexto de trabalho (regras de negócio, padrões, pesquisas) e constrói skills automaticamente por projeto, com aprovação humana no início.
5. **Base para times** (futuro): identidade e isolamento já modelados.
6. **Análise profunda Mem0 × Prometheus** absorvida no plano de evolução (extração, dedup, retrieval híbrido, entities, grounding temporal).
7. **Painel completo por projeto** na UI: stack (linguagens %, frameworks, DBs), runtime (containers, onde roda), git e **conexões & custos** (chaves mascaradas, MCPs, assinaturas, alertas de uso).

---

## 2. Contexto e motivação

- Usuário trabalha em **vários projetos simultâneos** (EVSCAR, Provador Digital, Prometheus, etc.) em **várias sessões** e **vários harnesses**.
- Hoje `web/memory.py` fixa `session_id="prometheus"` e só isola por `channel_id=agent-<id>`; não há noção formal de sessão/harness/projeto → risco de contaminação entre projetos.
- A UI atual lê memória via subprocess `mnemosyne recall` + regex `extract_project()` — frágil e global.
- O `PLAN_MEM0_PATTERNS.md` (aprovado) trata extração/dedup, mas **não** cobre multi-sessão, aba Projetos, skills por projeto nem presença em tempo real.

---

## 3. Diagnóstico (o que existe hoje)

| Área | Estado | Local |
|---|---|---|
| Isolamento multi-agente | ✅ `channel_id=agent-<id>` | `web/memory.py:16-25` |
| Sessão fixa | ⚠️ `session_id="prometheus"` para todos | `web/memory.py:21` |
| API remember/recall | ✅ `/api/memory/remember` + `/recall` | `web/app.py:402-429` |
| Projetos (tags) | ⚠️ regex heurístico `[PROJETO]` | `web/app.py:75-88, 492-503` |
| UI 6 abas | ✅ SPA monolítica | `web/templates/index.html` (1080 linhas) |
| Skills registry | ✅ CRUD sem coluna project | `web/skills_registry.py` |
| MCP | ✅ Mnemosyne MCP :8765 (não expõe eventos de projeto) | ecossistema NB02 |
| RAG vec0 | ✅ já usa `vec0` KNN | `web/rag_engine.py:68,168-184` |
| Mem0 patterns | 📋 plano M0-M5 aprovado, não executado | `docs/PLAN_MEM0_PATTERNS.md` |

---

## 4. Arquitetura — 4 lanes de memória

Modelo de contexto em camadas (não é banco separado por projeto):

| Lane | `channel_id` | `scope` | Uso | TTL |
|---|---|---|---|---|
| Sessão efêmera | `sess:<harness>:<session_id>` | `session` | raciocínio vivo, scratch, contexto da janela | curto (janitor) |
| Projeto canônico | `proj:<project_slug>` | `global` | decisões, implementações, issues, relatórios, skills, estado | permanente |
| Agente/pessoa | `agent:<agent_id>` | `global` | preferências e estilo do agente | permanente |
| Time (futuro) | `team:<team_id>` (bank) | `global` | multiusuário, shared surface, validator | permanente |

Regras:

- `proj:*` é a fonte de verdade da aba **Projetos**.
- Sessões escrevem em `sess:*`; eventos canônicos são promovidos para `proj:*` pelo worker.
- `MNEMOSYNE_CROSS_SESSION=1` **NÃO** deve ser usado como solução (abre tudo). Isolamento por lane/canal.

---

## 5. Identidade obrigatória (envelope de contexto)

Todo write (MCP ou REST) precisa carregar:

```json
{
  "harness": "opencode",
  "harness_session_id": "oc_123",
  "project_slug": "evscar",
  "agent_id": "pedreiro",
  "author_id": "herbert",
  "cwd": "/home/herbert/Projetos/evscar",
  "git_remote": "github.com/hofstatter/evscar",
  "client_event_id": "oc_123:2026-08-03T04:12:33Z:abc"
}
```

Regras:

1. `project_slug` explícito sempre vence.
2. Sem `project_slug`: **Project Resolver** infere por `cwd` → `git_remote` → sessão recente → texto.
3. `confidence < 0.6` → não vira canônico; vai para `needs_review`.
4. `client_event_id` é a chave de **idempotência** (retry não duplica).
5. `session_key = <harness>:<harness_session_id>`.

---

## 6. Modelo de dados (sidecar `prometheus_*` — sem ALTER no upstream)

```sql
CREATE TABLE IF NOT EXISTS prometheus_projects (
  slug TEXT PRIMARY KEY,
  name TEXT NOT NULL,
  repo_path TEXT,
  git_remote TEXT,
  color TEXT,
  status TEXT DEFAULT 'active',
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  last_event_at TIMESTAMP
);

CREATE TABLE IF NOT EXISTS prometheus_project_events (
  id TEXT PRIMARY KEY,
  project_slug TEXT NOT NULL,
  session_key TEXT,
  harness TEXT,          -- opencode | claude-code | codex | manual | unknown
  agent_id TEXT,
  event_type TEXT,       -- plan | decision | implementation | issue | research | skill | note
  title TEXT,
  summary TEXT,
  memory_id TEXT,
  status_hint TEXT,      -- todo | doing | done | blocked
  progress_delta REAL DEFAULT 0,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS prometheus_project_tasks (
  id TEXT PRIMARY KEY,
  project_slug TEXT NOT NULL,
  title TEXT NOT NULL,
  status TEXT DEFAULT 'todo',     -- todo | doing | done | blocked
  source_event_id TEXT,
  confidence REAL DEFAULT 0.5,
  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS prometheus_sessions (
  session_key TEXT PRIMARY KEY,  -- harness:harness_session_id
  harness TEXT NOT NULL,
  harness_session_id TEXT NOT NULL,
  project_slug TEXT,
  agent_id TEXT,
  author_id TEXT,
  cwd TEXT,
  git_remote TEXT,
  current_action TEXT,
  started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  last_seen_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  status TEXT DEFAULT 'active'   -- active | idle | stale | closed
);

CREATE TABLE IF NOT EXISTS prometheus_events_ingest (
  client_event_id TEXT PRIMARY KEY,
  session_key TEXT,
  project_slug TEXT,
  memory_id TEXT,
  processed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS prometheus_project_reports (
  project_slug TEXT PRIMARY KEY,
  summary TEXT,
  progress REAL,
  open_issues INTEGER,
  last_decision TEXT,
  last_implementation TEXT,
  active_sessions INTEGER,
  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS prometheus_connections (
  id TEXT PRIMARY KEY,
  project_slug TEXT NOT NULL,
  kind TEXT NOT NULL,          -- api_key | mcp | service | saas
  name TEXT NOT NULL,          -- DEEPSEEK_API_KEY, OpenChargeMap, tavily...
  provider TEXT,               -- DeepSeek, OpenChargeMap, FASHN, MiniMax...
  env_var TEXT,                -- nome da variável (auto-detectado)
  fingerprint TEXT,            -- hash da chave (detecta MESMA chave em 2 projetos)
  billing_type TEXT,           -- subscription | paygo | free | unknown
  cost_usd_month REAL,
  expires_at TEXT,             -- rotação/vencimento
  last_used_at TEXT,
  status TEXT DEFAULT 'active',-- active | unused | expired | revoked
  source TEXT DEFAULT 'manual',-- auto-env | auto-mcp | manual
  notes TEXT,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS prometheus_tech_profile (
  project_slug TEXT PRIMARY KEY,
  repo_path TEXT,
  languages_json TEXT,        -- {"TypeScript": 52.1, "Python": 18.3, ...}
  frameworks_json TEXT,       -- [{"name":"Next.js","version":"16.2.10"}, ...]
  databases_json TEXT,        -- ["PostgreSQL 16", "Redis 7", "Meilisearch", "MinIO"]
  containers_json TEXT,       -- snapshot do docker ps do projeto
  git_json TEXT,              -- branch, remote, últimos commits, dirty
  analyzed_at TIMESTAMP,
  scan_duration_ms INTEGER
);
```

Índices: `project_events(project_slug, created_at)`, `sessions(project_slug, last_seen_at)`, `tasks(project_slug, status)`, `connections(project_slug, kind)`.

---

## 7. API REST (novo namespace `/api/pm` — sem quebrar `/api/projects` legado)

```http
POST /api/pm/sessions/start       # envelope + session_key
POST /api/pm/sessions/heartbeat   # atualiza last_seen_at / current_action
POST /api/pm/sessions/close
GET  /api/pm/presence?project=<slug>          # sessões ativas (v1 polling)

POST /api/pm/events               # evento canônico (envelope)
GET  /api/pm/projects
GET  /api/pm/projects/<slug>/report
GET  /api/pm/projects/<slug>/timeline
GET  /api/pm/projects/<slug>/kanban
GET  /api/pm/projects/<slug>/skills

GET  /api/pm/projects/<slug>/connections          # A2 — chaves/MCPs/assinaturas
GET  /api/pm/connections/summary                  # A2 — visão financeira global
POST /api/pm/connections                          # A2 — curadoria manual
PUT  /api/pm/connections/<id>                     # A2 — billing/expiry/status
POST /api/pm/projects/<slug>/connections/scan     # A2 — re-varredura .env (read-only)
GET  /api/pm/projects/<slug>/stack                # A3 — painel completo (cache)
POST /api/pm/projects/<slug>/stack/scan           # A3 — re-análise sob demanda
GET  /api/pm/projects/<slug>/git                  # A3 — branch/remote/commits/dirty
GET  /api/pm/projects/<slug>/runtime              # A3 — containers/portas/status
```

Auth: o gate global (`_auth_gate`/`require_token_if_exposed`) cobre automaticamente. Tokens por **harness + usuário** (escopo).

---

## 8. MCP multi-harness

Ferramentas a expor (servidor MCP do Prometheus, ou extensão do Mnemosyne MCP :8765):

```text
prometheus_session_start
prometheus_session_heartbeat
prometheus_project_event
prometheus_project_context
prometheus_remember
prometheus_recall
prometheus_skill_suggest
```

Contrato mínimo de evento (exemplo Claude Code no Provador Digital):

```json
{
  "tool": "prometheus_project_event",
  "arguments": {
    "harness": "claude-code",
    "harness_session_id": "cl_777",
    "project_slug": "provador-digital",
    "agent_id": "backend-agent",
    "event_type": "implementation",
    "title": "Caddy ajustado para provador",
    "status_hint": "done",
    "client_event_id": "cl_777:abc123"
  }
}
```

Mesmo projeto + harnesses diferentes → mesma lane `proj:<slug>`. Projetos diferentes → lanes isoladas.

---

## 9. Presença em tempo real (na UI)

Estado de presença por heartbeat (default 15–30s):

| Estado | Condição | UI |
|---|---|---|
| `active` | heartbeat < 30s | bolinha verde |
| `idle` | 30s–5min | bolinha amarela |
| `stale` | > 5min sem heartbeat | cinza, some do "agora" |
| `closed` | close explícito | sai da lista |

UI (v1):

```text
EVSCAR — 37% concluído
● 2 sessões ativas agora
  [opencode · pedreiro · frontend]   [claude-code · reviewer · api]
Última atividade: há 42s
```

- V1: polling `/api/pm/presence` 5–10s.
- V1.1: SSE/WebSocket em `/api/pm/stream` (sessão iniciou, ficou idle, evento novo, task mudou, skill draft).
- Conflito: 2 agentes ativos na mesma task → badge de alerta.
- Hardening: presença expõe só metadado operacional (harness, agente, projeto, cwd, status, ação curta sanitizada). Nunca tokens/secrets/conteúdo bruto.
- Fallback: harness sem heartbeat → atividade inferida por eventos recentes (menor confiança, sinalizado).

---

## 10. Aba Projetos — UI

### Design Read (super-designer)

```text
Page: Dashboard de projetos / kanban operacional
Audience: dev operando múltiplos projetos simultâneos
Lane: product
VARIANCE: 4 | MOTION: 3 | DENSITY: 8
Palette: herdar tokens atuais (Linear dark); NÃO introduzir nova cor de destaque
Display: system-ui | Body: system-ui
```

### Layout

```text
[sidebar boards]  [header do projeto com barra de progresso]
                  [presença de sessões ativas]
                  [KPIs: última atividade | agentes | decisões | issues | skills]
                  [stack: barra % linguagens + frameworks + DBs]        (A3)
                  [runtime: containers/portas + git + onde roda]        (A3)
                  [conexões & custos: chaves mascaradas + MCPs + $]     (A2)
                  [kanban: Backlog | Em andamento | Concluído]
                  [timeline horizontal]
                  [drawer de detalhes (memória/evento/task de origem)]
```

### Implementação (padrão da UI atual)

- Botão no `<nav>`: `🗂️ Projetos` (`btn-projects`).
- Container `#projects-view` (padrão `showSkills()`).
- `resetViews()`: adicionar `projects-view` e `btn-projects` nas duas listas.
- Deep-link: `#projects`.
- Extrair JS para `web/static/projects.js` (evita inchar o monólito de 1080 linhas; CSP `'self'` permite).
- Reusar tokens CSS (`--surface-*`, `--hairline`, `--accent`, `resBar()`/`score-bar`).
- Drag-and-drop nativo HTML5 (como na dropzone RAG) na v1.1; v1 read-only auto-gerado.
- i18n: chaves novas em `web/static/i18n.js` (PT default + EN/ES/ZH).

### Progresso (heurística explicável)

```text
progresso = done_weight / total_weight

plan = 1 · decision = 2 · implementation = 4
issue_resolved = 3 · skill_created = 2 · research = 1 · issue_open = -2
```

Tooltip obrigatório: "37% — 14 eventos concluídos, 8 em aberto, última atividade há 2h".

## 10.1 — Painel: Conexões & Custos (Fase A2)

Cada projeto ganha o bloco **"Conexões & Custos"** com 4 grupos:

```text
🔑 Chaves API      — nome, provider, fingerprint mascarado, billing, expira, último uso, status
🔌 MCPs & Conexões — MCPs usados + serviços internos (postgres, redis, minio...)
💰 Assinaturas     — recorrente vs pay-as-you-go vs grátis; custo/mês; alerta "pago e sem uso"
🌿 Git + Runtime   — ver §10.2
```

### Detecção automática (2 tiers + curadoria)

| Tier | Fonte | O que detecta |
|---|---|---|
| auto-env | `.env`/`.env.example` do projeto | nomes `*_API_KEY`/`*_TOKEN`/`*_SECRET` + fingerprint (SHA-256 de prefixo — **nunca o valor**) |
| auto-mcp | `opencode.jsonc` (global do harness) | MCPs disponíveis — vínculo projeto↔MCP é **curado** (config é global, sem inferência confiável) |
| manual | UI (ou YAML opcional) | billing_type, cost_usd_month, expires_at, provider, notas |

### Regras de negócio

- **Nunca renderizar valor de chave** — só fingerprint mascarado (`sk-a8a••••`); endpoint nunca retorna o valor; scan é read-only.
- **Mesma chave em 2 projetos** → fingerprint igual → badge "compartilhada com \<projeto\>" (ex.: DeepSeek em EVSCAR + Provador).
- **Pago e sem uso** (`subscription|paygo` + `last_used_at > 30d` ou nunca) → badge vermelho + card no resumo global.
- **Expirando** (`expires_at < 30d`) → badge amarelo "rotacionar até DD/MM".
- **Custo consolidado**: soma de `cost_usd_month` por projeto e total global.

### Modelo

Tabela `prometheus_connections` (ver §6) — `kind`, `fingerprint`, `billing_type`, `cost_usd_month`, `expires_at`, `last_used_at`, `status`, `source`.

### Endpoints

```http
GET  /api/pm/projects/<slug>/connections
GET  /api/pm/connections/summary
POST /api/pm/connections
PUT  /api/pm/connections/<id>
POST /api/pm/projects/<slug>/connections/scan
```

## 10.2 — Painel: Stack & Runtime (Fase A3)

Bloco com **barra de linguagens estilo GitHub**, frameworks, bancos, containers, git e onde roda.

### Detecção

| Dado | Fonte | Método |
|---|---|---|
| % linguagens | árvore do projeto | contagem **por bytes** (estilo linguist), excluindo `node_modules`/`.next`/`dist`/volumes/`__pycache__`; docs/config separados do código |
| Frameworks | `package.json`, `requirements.txt`, `pyproject.toml` | parse de deps principais → chips com versão |
| Bancos | `docker-compose.yml` + `DATABASE_URL` + `.env` | imagem/schema → chip (Postgres 16, Redis 7, Meilisearch, MinIO...) |
| Containers | `docker ps` + compose | match por prefixo (`evscar-*`) → nome, porta, status, uptime |
| Git | `git log/status/remote` (read-only) | últimos 5 commits, branch, remote, dirty; "⚠ não versionado" se sem repo |
| Onde roda | registro + detecção | Local NB02 · Docker / VPS Contabo |

### Modelo (cache — análise é cara)

Tabela `prometheus_tech_profile` (ver §6) — `languages_json`, `frameworks_json`, `databases_json`, `containers_json`, `git_json`, `analyzed_at`, `scan_duration_ms`.

### Endpoints

```http
GET  /api/pm/projects/<slug>/stack
POST /api/pm/projects/<slug>/stack/scan
GET  /api/pm/projects/<slug>/git
GET  /api/pm/projects/<slug>/runtime
```

### Regras

- **Cache + re-scan manual** (botão na UI ou a cada N dias) — nunca análise por page load.
- **Docs (`.md`) contam como categoria separada** — não distorcem o % de código (EVSCAR tem 50 `.md`; sem esse corte Markdown apareceria como "linguagem principal").
- **Monorepo**: barra agregada + breakdown por diretório principal (EVSCAR: `03-frontend` TS + `04-ia-consultor` Python).
- **Projeto sem git** = badge de alerta ("não versionado"), não erro silencioso.

---

## 11. Skills por projeto — algoritmo (3 motores)

### A. Project Resolver
Decide o projeto de cada evento/memória (sinais em ordem de força):
1. `project_slug` explícito
2. `cwd`/repo path
3. `git_remote` normalizado
4. sessão recente do mesmo agente
5. conteúdo (`[PROJETO]`, nomes conhecidos, RAG docs)
6. fallback `geral`
Saída com `confidence`; `< 0.6` → `needs_review`.

### B. Project Reporter
Gera resumo executivo, estado, decisões, implementações, issues, skills, timeline e progresso a partir de **eventos estruturados + memórias referenciadas**. LLM só resume o que já é estruturado (nunca alucina estado).

### C. Skill Builder (fluxo seguro)

```text
detecta padrão no projeto
  → coleta evidências (3+ eventos/memórias)
  → pesquisa externa opcional (Tavily/Context7 com allowlist de domínios)
  → gera skill draft com fontes/evidências
  → salva scope='project' status='draft'
  → humano aprova → status='active'
  → reutilizada em 2+ projetos → candidata a global
```

Hardening:

- nunca gravar secrets;
- skill draft cita evidências (`evidence_json`);
- skill ativa exige checksum/version bump;
- decisões do algoritmo gravam `reason_json`;
- autonomia total só depois de avaliação (start com aprovação humana).

### Evolução da tabela `skills`

```sql
ALTER TABLE skills ADD COLUMN project_slug TEXT;
ALTER TABLE skills ADD COLUMN scope TEXT DEFAULT 'global';   -- project | global
ALTER TABLE skills ADD COLUMN status TEXT DEFAULT 'active';  -- draft | active | archived
ALTER TABLE skills ADD COLUMN confidence REAL DEFAULT 0.5;
ALTER TABLE skills ADD COLUMN evidence_json TEXT;
ALTER TABLE skills ADD COLUMN last_used_at TIMESTAMP;
ALTER TABLE skills ADD COLUMN use_count INTEGER DEFAULT 0;
```

> ⚠️ `skills` é tabela do Prometheus (não upstream Mnemosyne) — ALTER é seguro aqui. Se `skills` passar a ser de responsabilidade upstream no futuro, migrar para sidecar `prometheus_skills`.

---

## 12. Mem0 × Prometheus — análise profunda (resumo executivo)

Fonte: `docs/PLAN_MEM0_PATTERNS.md` + fonte oficial `mem0ai/mem0` (V3) + código local.

### Correções factuais ao plano anterior

| # | O plano dizia | Realidade |
|---|---|---|
| C1 | recall de memórias é brute-force | RAG já usa `vec0`; o recall de memórias vive no Mnemosyne upstream (já tem `vec_working` + fallback) — M2 é menor |
| C2 | `retention.py` é esboço de decay | é limpeza/backup — M3 é código novo |
| C3 | `eval_pipeline.py` é LongMemEval | é eval de cenas L1→L2 — M5 começa do zero |
| C4 | `llm_complete(model="deepseek-v4-flash")` | não existe; o real é `scripts/llm_backend.py::call_llm()` com backend global e modelo hardcoded `deepseek-chat`; default `ollama` (desligado no NB02) |
| C5 | API `POST /api/memory` | real: `/api/memory/remember` e `/api/memory/recall` |

### O que absorver (prioridade)

| Pri | Item | Fase |
|---|---|---|
| P0 | Extração LLM single-pass ADD-only | M1 |
| P0 | Dedup por hash (sidecar `prometheus_*`, scoped por channel) | M1 |
| P0b | Prompt V3 real: grounding temporal + "contextually rich, not atomic" + anti-eco | M1 |
| P0c | **Retrieval híbrido: FTS5/BM25 + semântico + threshold** (maior gap não coberto) | P1 (antes de M2) |
| P1 | Entity store + linking memória↔entidade e memória↔memória | M2 |
| P1 | Grounding temporal ("hoje/ontem" → data absoluta) | M1/M2 |
| P1 | Decay/eviction com persona imune + audit log (diferencial, não cópia) | M3 |
| P2 | Async queue + Postgres/pgvector | M4 |
| P2 | LongMemEval subset PT-BR no CI | M5 |

### O que NÃO copiar

- vector store externo como default (contradiz local-first);
- spaCy/NER inglês-cêntrico;
- prompt consumer (restaurantes/filmes) — copiar mecânica, não conteúdo;
- ADD-only puro sem decay/retrieval híbrido;
- churn de API do V3;
- `user_id` consumer redundante (já temos `agent_id`/`channel_id`).

---

## 13. Decisões assumidas (defaults — revisar com Herbert se divergir)

1. **Memória**: híbrida — DB global único + `project_slug`/lanes (não criar DB por projeto). ✅
2. **Skills**: `scope=project` com promoção para `global`; auto-geradas entram como `draft` e exigem aprovação humana no início. ✅
3. **Aba Projetos v1**: read-only auto-gerada; kanban manual/drag na v1.1. ✅
4. **Pesquisa na internet (Skill Builder)**: permitida via Tavily/Context7 com allowlist de domínios. ✅
5. **Presença em tempo real**: v1 polling 5–10s; SSE na v1.1. ✅
6. **Lanes**: `sess:*` efêmera · `proj:*` canônica · `agent:*` · futuro `team:*`. ✅
7. **Projeto compartilhado entre agentes do mesmo usuário**: sim por padrão. ✅
8. **Auth MCP**: token por harness + usuário com escopo. ✅
9. **Espanhol**: mantém resumo (convenção atual). ✅
10. **Hash dedup**: SHA-256 normalizado (evita discussão MD5; swap trivial se quiser parity exata). ✅
11. **API**: `infer` default `false` (backward compat); auto-memory opta por `infer=true` em fase posterior. ✅

---

## 14. Riscos e mitigações

| # | Risco | Mitigação |
|---|---|---|
| R1 | Vazamento entre projetos | lanes + `client_event_id` + testes de isolamento; nunca cross-session global |
| R2 | Sessões explodem | TTL/janitor para `sess:*`; consolidação para `proj:*` |
| R3 | Projeto errado por inferência | `confidence` + `needs_review`; nunca gravar baixa confiança como canônico |
| R4 | Duplicidade por retry de harness | idempotência por `client_event_id` |
| R5 | Relatório lento | materializar `prometheus_project_reports` via worker |
| R6 | Conflito de 2 agentes no mesmo estado | event sourcing + updated_at + origem; anexar, nunca sobrescrever |
| R7 | UI legada lê regex | nova aba usa `/api/pm/*`; manter `/api/projects` legado |
| R8 | `session_id` fixo do `web/memory.py` quebra | migração cuidadosa para lanes; testes multi-agente existentes continuam verdes |
| R9 | Custo LLM (extração/skills) | rate-limit por agent_id; fallback `infer=false`; métricas de fallback |
| R10 | Chave GitHub exposta (`Projeto.txt`) | rotacionar; usar `GITHUB_TOKEN`/`gh auth`; nunca commitar; `.gitignore` |
| R11 | index.html monolítico | extrair `static/projects.js` |
| R12 | Produção = `~/Projetos/web` (cópia) | sincronizar repo → produção após cada fase |

---

## 15. Fases de execução

### 🟢 Fase A0 — Identidade de contexto e sessões (pré-requisito)

- [ ] Tabelas sidecar (`prometheus_projects`, `_project_events`, `_project_tasks`, `_sessions`, `_events_ingest`, `_project_reports`)
- [ ] Envelope de contexto + Project Resolver v1
- [ ] `POST /api/pm/sessions/{start,heartbeat,close}`
- [ ] `POST /api/pm/events` (idempotente)
- [ ] Migração de `web/memory.py` para lanes (`sess:*`/`proj:*`)
- [ ] Worker de materialização de relatórios

**Critério de aceite A0:**
1. Duas sessões OpenCode em projetos diferentes não vazam memória.
2. Dois harnesses no mesmo projeto compartilham `proj:*`.
3. Retry do mesmo `client_event_id` não duplica.
4. Testes multi-agente atuais continuam passando.

### 🟢 Fase A — Aba Projetos (UI)

- [ ] Botão `🗂️ Projetos` + `#projects-view` + `resetViews()` + deep-link
- [ ] Sidebar de boards + header com progresso + KPIs
- [ ] Kanban read-only + timeline + drawer de detalhes
- [ ] Presença: polling `/api/pm/presence` + estados active/idle/stale/closed
- [ ] `web/static/projects.js` + chaves i18n

**Critério de aceite A:**
1. `http://localhost:8777/#projects` abre e alterna sem quebrar outras abas.
2. Cada projeto mostra progresso, timeline, sessões ativas e origem dos dados.
3. Dois agentes na mesma task → alerta de conflito.

### 🟡 Fase A2 — Conexões & Custos (painel do projeto)

- [ ] Tabela `prometheus_connections` + varredura read-only de `.env` (nomes + fingerprint, nunca valores)
- [ ] Endpoints `/api/pm/*/connections` + `/api/pm/connections/summary`
- [ ] Curadoria de billing (subscription/paygo/custo/expiração) na UI
- [ ] Alertas: "pago e sem uso" (>30d), "expirando" (<30d), chave compartilhada entre projetos
- [ ] Resumo financeiro global (custo/mês por projeto + total)

**Critério de aceite A2:**
1. Scan detecta as chaves do `.env` sem expor valores (só fingerprint mascarado).
2. UI nunca renderiza segredo; badge "compartilhada" aparece para a mesma chave em 2 projetos.
3. Assinatura sem uso há 30+ dias aparece no resumo global.

### 🟢 Fase A3 — Stack & Runtime (painel do projeto)

- [ ] Tabela `prometheus_tech_profile` + scanner de linguagens por bytes (estilo linguist, docs separados)
- [ ] Parsers de manifest (package.json/requirements.txt) + detecção de bancos (compose/DATABASE_URL)
- [ ] Snapshot de containers (docker ps por prefixo) + git (log/status/remote read-only)
- [ ] UI: barra de % linguagens, chips de frameworks/DB, blocos containers/git, badge "não versionado"

**Critério de aceite A3:**
1. Barra de linguagens condiz com a árvore real (docs separados do código).
2. DBs detectados do compose/DATABASE_URL aparecem como chips.
3. Projeto sem repo git mostra alerta "não versionado", sem erro.
4. Re-scan manual atualiza o cache; page load usa cache.

### 🟡 Fase B — Skills por projeto

- [ ] Migration da tabela `skills` (project_slug, scope, status, confidence, evidence_json)
- [ ] Skill Builder v1 com aprovação humana + pesquisa allowlist
- [ ] Aba Skills filtrando por projeto
- [ ] Promoção project → global

**Critério de aceite B:**
1. Skill gerada automaticamente aparece como `draft`.
2. Aprovação humana vira `active`.
3. Filtro por projeto funciona; skill reutilizada vira candidata global.

### 🟡 Fase C — Mem0 parity essencial

- [ ] M1 extração + dedup (SHA-256, scoped por channel, fallback `infer=false`)
- [ ] Prompt V3 real (grounding temporal, anti-eco, transições)
- [ ] Retrieval híbrido FTS5 + semântico + threshold
- [ ] Entity/linking v1
- [ ] Corrigir C4 (`call_llm`, backend deepseek explícito)

**Critério de aceite C:**
1. Gravar 2× a mesma decisão → segunda não duplica.
2. Recall misto supera só-vetorial.
3. "Ontem" vira data absoluta.
4. Entidades ligadas a memórias.

### 🟢 Fase D — Docs, i18n e release

- [ ] `README.md` EN canônico + `docs/lang/README.pt-BR.md` + `zh-CN.md` (espelho integral) + `es.md` (resumo)
- [ ] `docs/QUICKSTART.md` · `ARCHITECTURE.md` · `COMPARISON.md` · `CHANGELOG.md` · `docs/ROADMAP.md`
- [ ] `docs/DESIGN_PROJECTS.md` (tokens/design read) + `docs/SCREENSHOTS/projetos.png`
- [ ] GitHub: rotacionar chave → `gh auth` → tag `v0.2.0-projetos` → push (com aprovação explícita)

**Critério de aceite D:** docs nas 4 línguas citam a nova aba; README diagrama inclui `🗂️ Projetos`; release publicado com chave rotacionada e sem segredos no histórico.

---

## 16. Ordem de execução recomendada

```text
A0 (identidade/sessões)   ~4-6h   [sempre primeiro — sem isso, aba Projetos mistura contexto]
   ↓
A (aba Projetos UI)       ~6-8h   [valor visual + presença em tempo real]
   ↓
A2 (conexões & custos)    ~6-8h   [chaves/MCPs/assinaturas — economiza dinheiro]
   ↓
A3 (stack & runtime)      ~6-8h   [linguagens %, frameworks, DBs, containers, git]
   ↓
B (skills por projeto)    ~4-6h   [algoritmo + aprovação humana]
   ↓
(parar e medir ganhos)
   ↓
C (Mem0 parity)           ~8-12h  [extração/dedup/retrieval híbrido — reusa PLAN_MEM0_PATTERNS]
   ↓
D (docs/i18n/release)     ~3-4h   [com aprovação humana antes do push]
```

Total A0-D: ~34-48h (8-10 sessões Pedreiro + Inspetor nas fronteiras A0/A/A2/A3/C/D).

---

## 17. Critério global de aceite (v0.2-projetos)

1. Aba Projetos mostra relatório, kanban, timeline e progresso por projeto (A).
2. Presença em tempo real de agentes por projeto (A).
3. Multi-sessão do mesmo harness e multi-harness via MCP sem confusão de projeto (A0).
4. Conexões & Custos por projeto: chaves mascaradas, MCPs, assinaturas, alertas de uso/custo (A2).
5. Stack & Runtime por projeto: linguagens %, frameworks, DBs, containers e git (A3).
6. Skills por projeto com draft/aprovação/promoção (B).
7. Mem0 parity essencial: extração + dedup + retrieval híbrido + entities (C).
8. Backward compat: `/api/memory/*` e `/api/projects` legados seguem funcionando.
9. Testes em `tests/` passam (incluindo novos testes de isolamento multi-sessão).
10. Docs em EN/PT/ZH/ES atualizadas; changelog v0.2.0.
11. Release no GitHub com chave rotacionada e zero segredos.

---

## 18. Pós-implementação

- Atualizar `docs/ROADMAP.md` (marcar ✅), `ARCHITECTURE.md` (seção lanes + worker), `README.md`.
- Gravar no Mnemosyne: "Prometheus v0.2 — aba Projetos multi-sessão/multi-harness com lanes sess/proj/agent/team, presença em tempo real, skills por projeto e Mem0 parity essencial" (source `decisao`, importance 0.95, scope global).
- Tag git `v0.2.0-projetos` + release notes PT/EN.
- Sincronizar produção `~/Projetos/web/` + reiniciar `prometheus-web`.

---

## 19. Referências

- Mem0 V3: https://github.com/mem0ai/mem0 · `configs/prompts.py` · `docs/migration/oss-v2-to-v3.mdx`
- LongMemEval: https://github.com/mem0ai/longmemeval
- sqlite-vec: https://github.com/asg017/sqlite-vec
- Prometheus ROADMAP: `docs/ROADMAP.md` · MEM0 patterns: `docs/PLAN_MEM0_PATTERNS.md`
- Mnemosyne 3.12.2 (instalado): `mnemosyne/core/beam.py`, `mnemosyne/core/memory.py`, `mnemosyne/mcp_tools.py`
- State ecossistema: `~/Projetos/Bytex_AgentOS/STATE.md` (sessão 19)
