# PLAN DE EXECUÇÃO — Fase A0: Identidade de Contexto e Sessões

> **Documento:** `docs/PLAN_FASE_A0_EXECUCAO.md`
> **Origem:** `docs/PLAN_PROJETOS_MULTI_SESSAO.md` (§5-§9, §15-A0)
> **Executor:** Pedreiro (DeepSeek V4 Flash) — sessão dedicada
> **Revisor:** Inspetor (DeepSeek V4 Pro) — fronteira da fase
> **Data:** 03/08/2026
> **Branch:** `feat/pm-projetos-a0`
> **Backup:** `~/backups/prometheus-memory/fase-a0-execucao/20260803-164328/` + rodar backup pré-edição por arquivo
> **Classificação:** MEDIUM (DB sidecar + API nova — sem superfície sensível além de escrita em DB próprio)

---

## 1. Objetivo

Criar a espinha dorsal de **identidade de contexto** do Prometheus: lanes de memória (`sess:*`, `proj:*`, `agent:*`), registro de sessões ativas, ingestão idempotente de eventos de projeto e Project Resolver v1 — tudo via tabelas sidecar `prometheus_*` (SEM ALTER em tabelas do Mnemosyne upstream).

Ao final, duas sessões do mesmo harness em projetos diferentes **não vazam memória** e dois harnesses no mesmo projeto **compartilham** a lane canônica `proj:<slug>`.

## 2. Escopo

**Faz:** tabelas sidecar, lanes, `/api/pm/sessions/*`, `/api/pm/events`, `/api/pm/projects*`, `/api/pm/presence`, Project Resolver v1, relatório v1 materializado, testes de isolamento.

**NÃO faz (fases seguintes):** UI da aba Projetos (A), conexões & custos (A2), stack & runtime (A3), skills (B), Mem0 parity (C), docs 4 idiomas/release (D).

## 3. Ordem de execução (sequencial)

```text
0. backup + branch
1. web/prometheus_db.py          (conexão + schema sidecar)
2. web/projects_registry.py      (resolver + eventos + relatório v1)
3. web/session_registry.py       (sessões + lanes)
4. web/memory.py                 (alterar: lanes, manter backward compat)
5. web/pm_routes.py              (blueprint /api/pm) + registrar em web/app.py
6. tests/test_session_lanes.py   (novos testes)
7. pytest + smoke curl
8. sincronizar produção ~/Projetos/web + reiniciar prometheus-web
9. atualizar docs (ROADMAP/CHANGELOG) + Mnemosyne decisão
```

---

## 4. Arquivo 1 — `web/prometheus_db.py` (novo)

Padrão `skills_registry._db()` / `storage.SQLiteStore` (WAL + busy_timeout + synchronous=NORMAL). Caminho do DB: `PROMETHEUS_DB` (default `~/.hermes/mnemosyne/data/mnemosyne.db`).

```python
"""Conexão + schema das tabelas sidecar prometheus_* (não toca upstream)."""
import os, sqlite3
from pathlib import Path

MNEMOSYNE_HOME = Path(os.environ.get("MNEMOSYNE_HOME", Path.home() / ".hermes" / "mnemosyne"))
DB_PATH = Path(os.environ.get("PROMETHEUS_DB", MNEMOSYNE_HOME / "data" / "mnemosyne.db"))

SCHEMA = """..."""  # ver SQL na §5

def get_conn() -> sqlite3.Connection:
    con = sqlite3.connect(str(DB_PATH), timeout=10)
    con.execute("PRAGMA journal_mode=WAL")
    con.execute("PRAGMA busy_timeout=5000")
    con.execute("PRAGMA synchronous=NORMAL")
    con.row_factory = sqlite3.Row
    return con

def init_schema() -> None:
    con = get_conn()
    con.executescript(SCHEMA)
    con.commit(); con.close()
```

`init_schema()` é idempotente (`CREATE TABLE IF NOT EXISTS`) e roda na importação do blueprint (lazy, como `skills_registry`).

## 5. SQL — tabelas sidecar (em `prometheus_db.SCHEMA`)

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
  harness TEXT,
  agent_id TEXT,
  event_type TEXT,        -- plan | decision | implementation | issue | research | skill | note
  title TEXT,
  summary TEXT,
  memory_id TEXT,
  status_hint TEXT,       -- todo | doing | done | blocked
  progress_delta REAL DEFAULT 0,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_pme_pslug_ts ON prometheus_project_events(project_slug, created_at);

CREATE TABLE IF NOT EXISTS prometheus_project_tasks (
  id TEXT PRIMARY KEY,
  project_slug TEXT NOT NULL,
  title TEXT NOT NULL,
  status TEXT DEFAULT 'todo',   -- todo | doing | done | blocked
  source_event_id TEXT,
  confidence REAL DEFAULT 0.5,
  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_pmt_pslug_status ON prometheus_project_tasks(project_slug, status);

CREATE TABLE IF NOT EXISTS prometheus_sessions (
  session_key TEXT PRIMARY KEY,   -- <harness>:<harness_session_id>
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
  status TEXT DEFAULT 'active'    -- active | idle | stale | closed
);
CREATE INDEX IF NOT EXISTS idx_pms_pslug_seen ON prometheus_sessions(project_slug, last_seen_at);

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
```

## 6. Arquivo 2 — `web/projects_registry.py` (novo)

### 6.1 `resolve_project(*, project_slug=None, cwd=None, git_remote=None, agent_id=None, text="") -> dict`

Sinais em ordem de força (retorna `{slug, confidence, source}`):

| # | Sinal | Slug | Confidence |
|---|---|---|---|
| 1 | `project_slug` explícito | o próprio | 1.0 |
| 2 | `cwd` basename casa com `prometheus_projects` ou `PROMETHEUS_PROJECTS` env | slug | 0.95 |
| 3 | `git_remote` normalizado (org/repo) casa com repo_path/git_remote | slug | 0.9 |
| 4 | sessão recente do mesmo `agent_id` (última `prometheus_sessions.project_slug` não-closed) | slug | 0.75 |
| 5 | regex `\[(\w[\w-]*)\]` no texto (com exclusão de unknown/unk) | slug | 0.6 |
| 6 | fallback | `geral` | 0.4 |

- `confidence < 0.6` → marca `needs_review: true` (evento NÃO vira canônico; fica só na ingest).
- Slug normalizado: lowercase, `[^a-z0-9-]` → `-`, trim `-`.

### 6.2 `ingest_event(envelope: dict, *, client_event_id: str) -> dict`

Transação curta:

1. `resolve_project(...)` a partir do envelope.
2. **Idempotência:** `SELECT 1 FROM prometheus_events_ingest WHERE client_event_id=?` → se existe, retorna `{"duplicate": true, ...}` sem escrever nada.
3. Insere `prometheus_project_events` (id uuid4 curto) + `prometheus_project_events_ingest` na MESMA transação.
4. Se `confidence >= 0.6` e envelope tiver conteúdo → grava memória canônica na lane `proj:<slug>` (via `session_registry.remember_project`, §7.2) e guarda `memory_id`.
5. `UPDATE prometheus_projects SET last_event_at = now WHERE slug=?` (+ INSERT OR IGNORE se projeto novo).
6. `refresh_report(slug)` (síncrono no A0; worker assíncrono vem no M4).

Retorna `{id, project_slug, confidence, needs_review, memory_id, duplicate}`.

### 6.3 `refresh_report(slug: str) -> dict`

Progresso heurístico (explicável — tooltip na UI vem na Fase A):

```python
WEIGHTS = {"plan": 1, "decision": 2, "implementation": 4,
           "issue_resolved": 3, "skill_created": 2, "research": 1}
OPEN_PENALTY = {"issue_open": -2}

# done = Σ peso(event_type) onde status_hint IN ('done','resolved')
# total = Σ peso(event_type) de todos os eventos com status_hint != 'blocked' (mín 1)
# progress = clamp(done / total, 0, 1)
```

Preenche `prometheus_project_reports`: `summary` (1 linha: N eventos, X abertos), `progress`, `open_issues`, `last_decision`, `last_implementation` (últimos por tipo), `active_sessions` (contagem `prometheus_sessions` active/idle).

### 6.4 `list_projects() -> list[dict]`

JOIN `prometheus_projects` + contagem de sessões ativas + `prometheus_project_reports` (fallback: eventos).

## 7. Arquivo 3 — `web/session_registry.py` (novo)

### 7.1 `session_key(harness, harness_session_id) -> str` → `f"{harness}:{harness_session_id}"`

### 7.2 Lanes (usa `web/memory.py` internamente)

| Lane | session_id Mnemosyne | channel_id |
|---|---|---|
| sessão | `prom-sess-<hash8(session_key)>` | `sess:<harness>:<session_id>` |
| projeto | `prom-proj-<slug>` | `proj:<slug>` |
| agente | `prom-agent-<agent_id>` | `agent:<agent_id>` |

- `remember_session(harness, session_id, content, source, importance)` → lane `sess:*`, `scope="session"`.
- `remember_project(slug, content, source, importance, *, agent_id="")` → lane `proj:*`, `scope="global"`.
- `recall_lane(channel: str, query, top_k, *, agent_id="")` → `Mnemosyne.recall(..., channel_id=channel)` (filtro por canal já verificado no BEAM).
- `close_lane(key)` → fechar sessão + opcional consolidação `sess:*` → `proj:*` (v1: não consolida automaticamente; evento canônico já foi escrito).

### 7.3 `start_session(envelope) -> dict`

- `INSERT OR IGNORE INTO prometheus_sessions(session_key, harness, harness_session_id, project_slug, agent_id, author_id, cwd, git_remote, current_action, status)`.
- Se `project_slug` ausente → `resolve_project(cwd=..., git_remote=...)` e atualiza a linha.
- Retorna `{session_key, project_slug, confidence, context: <últimas 3 decisões do proj, via recall_lane>}`.

### 7.4 `heartbeat(session_key, *, current_action=None, status=None)`

- `UPDATE prometheus_sessions SET last_seen_at=now, current_action=COALESCE(?,current_action), status=COALESCE(?,status) WHERE session_key=?`.
- Se `status == "idle"` → marcador idle. Thresholds de presença: `active` < 30s, `idle` 30s–5min, `stale` > 5min (definidos como constantes, usados por `presence()`).

### 7.5 `presence(project_slug=None) -> list[dict]`

- Sessões com `status != 'closed'`, calculando `active/idle/stale` pela diferença `now - last_seen_at`.
- Filtro por `project_slug` se passado.
- Retorna só metadado operacional: `{session_key, harness, agent_id, project_slug, current_action, status, last_seen_at}` (sem conteúdo/secrets).

## 8. Arquivo 4 — `web/memory.py` (alterar)

**Regra de ouro: manter backward compat.** A assinatura pública atual `remember(content, agent_id="", source="api", importance=0.5) -> str` e `recall(query, agent_id="", top_k=5) -> list` NÃO pode quebrar (usada por `/api/memory/*` e testes existentes).

Alterações:

1. `_mem(agent_id="")` → session_id passa de `"prometheus"` para `f"prom-agent-{agent_id or 'default'}"`, mantendo `channel_id=f"agent-{agent_id}"` (corrige colisão de dedup exato entre agentes — achado da análise).
2. Novos helpers:
   - `_lane(channel: str, session: str) -> Mnemosyne` (instância cacheada por canal).
   - `remember_lane(channel, session, content, source, importance, scope) -> str`.
   - `recall_lane(channel, query, top_k) -> list`.
3. `remember()`/`recall()` existentes delegam para `_lane(f"agent-{agent_id}", ...)` — comportamento idêntico ao anterior (channel agent-<id>).

⚠️ `list_agents()` (SQL `channel_id LIKE 'agent-%'`) continua válido.

## 9. Arquivo 5 — `web/pm_routes.py` (novo) + registro

```python
pm_bp = Blueprint("pm", __name__, url_prefix="/api/pm")
```

| Método/rota | Corpo/query | Resposta |
|---|---|---|
| POST `/api/pm/sessions/start` | envelope `{harness, harness_session_id, project_slug?, agent_id, author_id?, cwd?, git_remote?, current_action?}` | `{session_key, project_slug, confidence, context}` 201 |
| POST `/api/pm/sessions/heartbeat` | `{session_key, current_action?, status?}` | `{session_key, last_seen_at}` 200 |
| POST `/api/pm/sessions/close` | `{session_key}` | `{session_key, status: "closed"}` 200 |
| POST `/api/pm/events` | envelope + `{client_event_id, event_type, title, summary, status_hint?, progress_delta?}` | `{id, project_slug, confidence, needs_review, memory_id, duplicate}` 201/200(dup) |
| GET `/api/pm/projects` | — | `[{slug, name, last_event_at, active_sessions, progress}]` |
| GET `/api/pm/projects/<slug>/report` | — | report materializado (ou 404) |
| GET `/api/pm/presence?project=<slug>` | query opcional | `[{session_key, harness, agent_id, status, last_seen_at, current_action}]` |

Registro em `web/app.py` (bloco try/except dos blueprints, padrão atual): `from pm_routes import pm_bp; app.register_blueprint(pm_bp)`. O gate de auth (`require_token_if_exposed`) cobre automaticamente.

**Não** mover/renomear `GET /api/projects` legado (fase D resolve).

## 10. Arquivo 6 — `tests/test_session_lanes.py` (novo)

Setup como `test_multiagent.py`: `os.environ["PROMETHEUS_DB"]="/tmp/test-lanes.db"`, remove DB, reload módulos.

| # | Teste | Assert |
|---|---|---|
| T1 | Duas sessões OpenCode, projetos diferentes | evento de `evscar` não aparece no recall de `provador` e vice-versa |
| T2 | Mesmo projeto, harnesses diferentes (opencode + codex) | memória da lane `proj:evscar` visível nas duas sessões |
| T3 | Idempotência | mesmo `client_event_id` 2× → 1 evento + 1 ingest (duplicate=true na 2ª) |
| T4 | Presence | heartbeat atualiza `last_seen_at`; sessão sem heartbeat > threshold vira `stale` |
| T5 | Resolver | `cwd="/home/herbert/Projetos/evscar"` → slug `evscar` conf 0.95; explícito vence; sem sinais → `geral` conf 0.4 + needs_review |
| T6 | Backward compat | `memory.remember("x", agent_id="atlas")` e `memory.recall("x", agent_id="atlas")` funcionam como antes |
| T7 | Report | 3 eventos `implementation done` + 1 `issue blocked` → progress > 0 e open_issues >= 1 |

## 11. Smoke test (após pytest)

```bash
# 1. duas sessões em projetos diferentes
curl -s -X POST localhost:8777/api/pm/sessions/start -H 'Content-Type: application/json' \
  -d '{"harness":"opencode","harness_session_id":"a1","project_slug":"evscar","agent_id":"pedreiro","cwd":"/home/herbert/Projetos/evscar"}'
curl -s -X POST localhost:8777/api/pm/sessions/start -H 'Content-Type: application/json' \
  -d '{"harness":"opencode","harness_session_id":"b2","project_slug":"provador-digital","agent_id":"pedreiro","cwd":"/home/herbert/Projetos/provador-digital"}'

# 2. evento idempotente
curl -s -X POST localhost:8777/api/pm/events -H 'Content-Type: application/json' \
  -d '{"harness":"opencode","harness_session_id":"a1","project_slug":"evscar","agent_id":"pedreiro","client_event_id":"a1:1","event_type":"implementation","title":"fix frontend","status_hint":"done"}'
# repetir → duplicate:true

# 3. relatório + presença
curl -s localhost:8777/api/pm/projects/evscar/report
curl -s "localhost:8777/api/pm/presence?project=evscar"
```

Esperado: `report.progress > 0`, `presence` lista a sessão `opencode:a1` como active.

## 12. Rollback

- Tudo é sidecar: drop de `prometheus_*` restaura o estado anterior sem tocar Mnemosyne.
- Backup por arquivo via `~/bin/backup-before-edit.sh` (exit 0 obrigatório antes de cada edição).
- Git: branch `feat/pm-projetos-a0`; revert por commit se necessário.

## 13. Riscos e mitigações

| # | Risco | Mitigação |
|---|---|---|
| R1 | Quebrar `web/memory.py` existente (API `/api/memory/*`) | backward compat preservada (T6) + rodar `tests/` completos |
| R2 | SQLite lock com UI/Mnemosyne abertos | WAL + busy_timeout (padrão) + transações curtas |
| R3 | Envelope malformado (harness vazio) | validação 400 com mensagem clara |
| R4 | Resolver com `cwd` de fora de `~/Projetos` | fallback por regex/texto; `needs_review` quando conf < 0.6 |
| R5 | `PROMETHEUS_DB` diferente em produção (`~/Projetos/web/.env`) | usar a mesma env var; sincronizar produção no fim |
| R6 | Presença com relógio/harness travado | threshold staleness + `status=closed` explícito |

## 14. Critérios de aceite (definição de done da Fase A0)

1. ✅ Duas sessões do mesmo harness em projetos diferentes não vazam memória (T1).
2. ✅ Dois harnesses no mesmo projeto compartilham a lane `proj:<slug>` (T2).
3. ✅ Retry do mesmo `client_event_id` não duplica (T3).
4. ✅ Sessão sem heartbeat fica `stale` e sai do "agora" (T4).
5. ✅ Resolver com confidence + needs_review (T5).
6. ✅ Backward compat: `/api/memory/*` e testes multi-agente existentes seguem verdes (T6).
7. ✅ `pytest tests/` 100% verde (novos + existentes).
8. ✅ Smoke curl responde 200/201 e report/progress consistentes.
9. ✅ ROADMAP/CHANGELOG atualizados; decisão gravada no Mnemosyne.
10. ✅ Produção `~/Projetos/web/` sincronizada + `prometheus-web` reiniciado (smoke em :8777).

## 15. Estimativa

~4-6h Pedreiro + 1 revisão Inspetor (fronteira: memory.py + ingest/transação).

## 16. Referências

- `docs/PLAN_PROJETOS_MULTI_SESSAO.md` §5 (envelope), §6 (schema), §7 (API), §9 (presença), §15-A0
- Mnemosyne 3.12.2: `mnemosyne/core/beam.py` (recall com `channel_id`, `_find_duplicate` por session_id), `mnemosyne/core/memory.py` (remember/recall)
- Padrão de DB local: `web/skills_registry.py`, `web/storage.py`
