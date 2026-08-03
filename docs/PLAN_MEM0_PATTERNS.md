# PLAN — Padrões Mem0 V3 dentro do Prometheus Memory

> **Data:** 03/08/2026
> **Autor:** Arquiteto (Kimi K3)
> **Aprovado por:** Herbert (pendente execução)
> **Classificação:** MEDIUM (multi-arquivo, sem superfície sensível além de DB)
> **Status:** Plano aprovado — aguarda sessão Pedreiro dedicada (M0-M3)
> **Dependências:** Prometheus v0.1.0+ rodando · Mnemosyne v3.12+ · DeepSeek API key ativa
> **Backup pré-implementação:** `~/backups/prometheus-memory/pre-mem0-patterns/`

---

## 1. Contexto e motivação

O **Mem0** (github.com/mem0ai/mem0) é o sistema de memória reference para
agentes LLM em 2026. Em 02/08/2026, estudo comparativo identificou padrões
do Mem0 que faltam no Prometheus-Memory (registrados no `ROADMAP.md` v0.2/v0.3).

Este plano **não** propõe integrar o Mem0 MCP (seria redundante e conflitante
com Mnemosyne). Propõe **absorver os padrões arquiteturais** do Mem0 V3 dentro
do Prometheus, preservando os diferenciais existentes (pipeline L0→L3, RAG
multimodal, Canvas Mermaid, Persona tier, Skills auto-geradas).

### ⚠️ Correção importante vs ROADMAP atual

O `ROADMAP.md` linha 16 cita:
> "Dedup semântico estilo mem0 (ADD/UPDATE/DELETE/NOOP via LLM)"

Isso descreve o **algoritmo V2 do Mem0**. Em 2026 o Mem0 passou para **V3 —
ADD-only + hash-based dedup** (fonte: `mem0ai/mem0/configs/prompts.py`,
`docs/migration/oss-v2-to-v3.mdx`). Este plano reflete **V3**, não V2.

---

## 2. Estado atual do Prometheus (diagnóstico)

### ✅ O que JÁ tem (não mexer)

| Feature | Arquivo | Maturidade |
|---|---|---|
| Multi-agente (`agent_id` via `channel_id`) | `web/memory.py:16-25` | ✅ Produção |
| API REST `/api/memory` (remember/recall via HTTP) | `web/app.py:403-432` | ✅ Produção |
| Pipeline L0→L3 (session→facts→scenes→persona→skills) | `scripts/*.py` | ✅ Produção |
| RAG multimodal (PDF/DOCX/imagens, OCR, fastembed 384d) | `web/rag_engine.py` | ✅ Produção |
| Grafo G6 + Canvas Mermaid + Memory Browser | `web/templates/index.html` | ✅ Produção |
| Skills registry (CRUD + checksum + roles) | `web/skills_registry.py` | ✅ Produção |
| Offloading de outputs grandes (`ref_manager.py`) | `scripts/ref_manager.py` | ✅ Produção |
| SQLite + (sqlite-vec disponível mas usa cosine brute-force) | `web/storage.py` | ⚠️ Parcial |
| PostgresStore esboçado mas não usado no core | `web/storage.py:33-50` | ❌ Não usado |
| `extract_entities=True` no remember do Mnemosyne | (Mnemosyne nativo) | ⚠️ Não estruturado |

### ❌ O que FALTA (vai ser implementado por este plano)

| Gap | Impacto hoje |
|---|---|
| **G1** Sem extração de fatos via LLM (grava texto bruto) | Memórias verbosas, ruído semântico |
| **G2** Sem dedup (mesma decisão gravada 5×) | Banco cresce indefinidamente, recall poluído |
| **G3** Sem entity store estruturado | Entidades soltas, sem linking |
| **G4** Sem decay/eviction (só consolidation via cron) | Memórias velhas pesam igual às novas |
| **G5** sqlite-vec `vec0` KNN não usado | Busca O(N) em vez de O(log N) |
| **G6** Sem fila assíncrona de indexing | Upload bloqueia, LLM síncrono |
| **G7** Sem eval harness LongMemEval no CI | Regressões sem detecção |

---

## 3. O que é o Mem0 V3 (resumo técnico)

### Pipeline do `add()` em V3

```
Mensagens
   │
   ▼
1. EXTRAÇÃO (1 LLM call, prompt "ADDITIVE_EXTRACTION_PROMPT")
   ├── Lê "Recently Extracted Memories" (até 20, cache session)
   ├── Lê "Existing Memories" (top-10 por similaridade)
   └── Extrai fatos novos auto-contidos
   │
   ▼
2. DEDUPLICAÇÃO (hash MD5, batch)
   └── Remove duplicatas exatas (sem LLM aqui)
   │
   ▼
3. STORAGE (batch embed → vector store + entity extraction → entity store)
```

### Modos `infer=True` vs `infer=False`

- **`infer=True`** (default): extração LLM + dedup — para conversa natural
- **`infer=False`**: armazena raw, pula dedup — para bulk import / migração

### Princípios V3

1. **ADD-only** — nunca UPDATE/DELETE no prompt; dedup resolve duplicatas
2. **Single-pass extraction** — 1 LLM call por `add()` (não N calls por fato)
3. **Batch operations** — embed e insert em lote
4. **Dedup em 2 camadas** — prompt instruction + hash MD5 downstream
5. **"When in doubt, extract"** — leve redundância < memória perdida

---

## 4. Gap analysis Prometheus ↔ Mem0

| Padrão Mem0 V3 | Prometheus atual | Ação | Prioridade |
|---|---|---|---|
| Extração LLM de fatos (`infer=True`) | ❌ Grava texto bruto | Implementar em `web/memory.py` | 🔴 P0 |
| Single-pass prompt com "Recently Extracted" + "Existing Memories" | ❌ Não tem | Criar `web/extractor.py` | 🔴 P0 |
| Hash MD5 dedup | ❌ Não tem | Adicionar coluna `content_hash` | 🔴 P0 |
| `infer=False` (raw mode) | ✅ Hoje é sempre assim | Manter como modo explícito | 🟢 P2 |
| Entity extraction estruturada | ⚠️ Mnemosyne tem flag mas não usa | Implementar `entity_store` | 🟡 P1 |
| Batch embed + batch insert | ❌ Síncrono, 1-por-1 | Adicionar batch path | 🟡 P1 |
| sqlite-vec `vec0` KNN | ⚠️ Disponível mas brute-force | Migrar busca para `vec0` | 🟡 P1 |
| Decay/eviction (estilo Letta core/archival) | ❌ Só consolidation | Implementar `scripts/retention.py` (já existe esboço) | 🟡 P1 |
| Fila assíncrona (upload → 202, worker processa) | ❌ Síncrono | Adicionar `scripts/indexer_worker.py` + DB queue | 🟢 P2 |
| Postgres backend completo | ❌ Só esboço em `storage.py` | Migrar via `DATABASE_URL` | 🟢 P2 |
| LongMemEval no CI | ⚠️ `eval_pipeline.py` existe, não no CI | Integrar GitHub Actions | 🟢 P2 |

---

## 5. Ganhos esperados (métricas)

### Antes vs depois (estimativa, single-user 1k memórias)

| Métrica | Atual (v0.1) | Após P0+P1 | Após P2 (meta v0.3) |
|---|---|---|---|
| Tamanho médio memória | ~250 chars (texto bruto) | ~80 chars (fato extraído) | idem |
| Redundância (memórias duplicadas) | ~30-40% (estimado) | < 5% | < 2% |
| Latência recall @ top-5 | ~150ms (cosine brute-force) | ~150ms | **~20ms (vec0 HNSW)** |
| Latência recall @ top-5 (100k memórias) | ~15s (inviável) | ~12s | **~50ms** |
| Custo LLM por `add()` | $0 (sem extração) | ~$0.0005 (1 call DS-Flash) | idem |
| Throughput indexing | Síncrono, ~3/s | Síncrono, ~3/s | **Assíncrono, 50/s** |
| Precision@5 recall | ~70% (ruído de duplicatas) | ~88% (estimado) | **~92%** |
| LongMemEval Recall@5 | Não medido | Não medido | **> 90%** (meta Mem0-tier) |

### Ganhos qualitativos

- **Memórias automáticas melhores** — auto-memory skill hoje grava texto longo;
  com extração, grava fatos atômicos ("Decisão: troca Visionário GLM-4.6V →
  MiniMax M3 em 03/08/2026")
- **Banco compacto** — menos 30-50% em storage após dedup
- **Recall limpo** — sem 5 versões da mesma decisão aparecendo juntas
- **Multi-agente escala** — sem dedup, cada `agent_id` incha rápido

---

## 6. Diferencial competitivo (Prometheus vs Mem0)

O Mem0 é ótimo em extração/dedup mas **é só memória**. O Prometheus é mais amplo:

| Categoria | Mem0 V3 | Prometheus v0.1 + este plano |
|---|---|---|
| **Extração LLM** | ✅ Best-in-class | 🎯 P0 vai equiparar |
| **Dedup** | ✅ Hash + prompt | 🎯 P0 vai equiparar |
| **Entity linking** | ✅ Simples | 🎯 P1 vai equiparar |
| **Multi-agente (agent_id)** | ✅ | ✅ Já tem (`channel_id`) |
| **API REST** | ✅ Cloud + OSS | ✅ Já tem (`/api/memory`) |
| **Pipeline L0→L3** | ❌ Não tem | ✅ Diferencial (session→facts→scenes→persona) |
| **Persona tier** | ❌ Não tem | ✅ Diferencial (regras permanentes auto-injetadas) |
| **Grafo de triples temporal** | ❌ Não tem | ✅ Diferencial (válido de/até, supersede) |
| **RAG multimodal** | ❌ Não tem | ✅ Diferencial (PDF/DOCX/img OCR) |
| **Memory Browser web** | ⚠️ Cloud só | ✅ Diferencial (self-hosted :8777) |
| **Canvas Mermaid (compressão simbólica)** | ❌ Não tem | ✅ Único |
| **Skills auto-geradas** | ❌ Não tem | ✅ Único |
| **Offloading de outputs grandes** | ❌ Não tem | ✅ Único |
| **Self-hosted / local-first** | ⚠️ OSS mas empurra cloud | ✅ 100% local, zero dependência cloud |
| **Embeddings PT-BR nativos** | ⚠️ Inglês-centric | ✅ MiniLM-L12 multilíngue |

### Resumo do posicionamento

> **Mem0 = infraestrutura de memória** (camada 1).
> **Prometheus = sistema completo de memória + significado** (camadas 1-3 +
> RAG + Canvas + Persona + Skills).
>
> Este plano **copia a camada 1 do Mem0** (extração/dedup) para que o
> Prometheus alcance parity no básico, mantendo os diferenciais nas camadas
> superiores.

---

## 7. Roadmap em fases (M0 → M5)

### 🟢 M0 — Preparação (1h)

**Goal:** backups + branch + mensuração baseline.

- [ ] Backup completo: `~/backups/prometheus-memory/pre-mem0-patterns/$(date)/`
- [ ] Branch git: `git checkout -b feat/mem0-patterns`
- [ ] Medir baseline:
  - Tamanho banco: `du -h ~/.hermes/mnemosyne/data/mnemosyne.db`
  - Contagem duplicatas suspeitas: query SQL (hash manual de conteúdo)
  - Latência recall: script `evals/benchmark_recall.py` (criar)
- [ ] Documentar baseline em `docs/MEM0_BASELINE.md`

**Critério de aceite M0:** baseline documentado + branch criada + backup validado.

### 🔴 M1 — P0: Extração LLM + Dedup hash (4-6h)

**Goal:** memórias gravadas via `/api/memory` passam por extração e dedup.

#### Arquivos a criar

- `web/extractor.py` (novo) — extração LLM single-pass
- `web/dedup.py` (novo) — hash MD5 + dedup semântico opcional

#### Arquivos a alterar

- `web/memory.py` — adiciona parâmetro `infer: bool = True` em `remember()`
- `web/app.py:403-414` — passa `infer` do request body
- `web/storage.py` — adiciona migration com coluna `content_hash TEXT`
- `requirements.txt` — adicionar `tenacity` (retries LLM)

#### Interface do `web/extractor.py`

```python
# web/extractor.py (esboço)
from scripts.llm_backend import llm_complete  # já existe

RECENTLY_EXTRACTED_LIMIT = 20
EXISTING_MEMORIES_TOP_K = 10

EXTRACTION_PROMPT = """Você é um Extrator de Memórias. Sua única operação
é ADD: identifique toda informação memorável e produza afirmações factuais
auto-contidas, em português.

## Mensagens Novas
{new_messages}

## Memórias Recentes (não re-extrair)
{recently_extracted}

## Memórias Existentes (apenas para dedup/linking)
{existing_memories}

## Regras
1. Cada fato = 1 linha, auto-contido, sem "ele/ela/isso"
2. Não re-extrair info já presente acima
3. Em dúvida, extraia (dedup downstream resolve)
4. Formato: JSON array de strings

Output:"""


def extract_facts(
    new_messages: str,
    recently_extracted: list[str],
    existing_memories: list[str],
) -> list[str]:
    """Single LLM call → lista de fatos atômicos."""
    prompt = EXTRACTION_PROMPT.format(
        new_messages=new_messages,
        recently_extracted="\n".join(f"- {m}" for m in recently_extracted),
        existing_memories="\n".join(f"- {m}" for m in existing_memories),
    )
    raw = llm_complete(prompt, model="deepseek-v4-flash", max_tokens=1500)
    return _parse_json_array(raw)


def _parse_json_array(raw: str) -> list[str]:
    """Tolerante a markdown code fences e JSON malformado."""
    # ... implementação defensiva
```

#### Interface do `web/dedup.py`

```python
# web/dedup.py (esboço)
import hashlib


def content_hash(text: str) -> str:
    """Hash MD5 normalizado (lowercase + strip)."""
    norm = " ".join(text.lower().split())
    return hashlib.md5(norm.encode("utf-8")).hexdigest()


def is_duplicate(text: str, existing_hashes: set[str]) -> bool:
    return content_hash(text) in existing_hashes


def fetch_existing_hashes_for_agent(agent_id: str, db_path: str) -> set[str]:
    """SELECT content_hash FROM working_memory WHERE channel_id = ?"""
    # ... sqlite3 query
```

#### Fluxo novo do `remember()`

```python
# web/memory.py (alteração)
def remember(content: str, agent_id: str = "", source: str = "api",
             importance: float = 0.5, infer: bool = True) -> list[str]:
    """Lembre com extração opcional estilo Mem0 V3.

    Returns: lista de memory_ids criados (pode ser > 1 com infer=True).
    """
    if not infer:
        # raw mode (igual Mem0 infer=False)
        mid = _mem(agent_id).remember(content, source=source, importance=importance)
        return [mid]

    # Modo infer=True: extrai fatos
    from web.extractor import extract_facts
    from web.dedup import content_hash, fetch_existing_hashes_for_agent, is_duplicate

    recent = _fetch_recently_extracted(agent_id, limit=20)
    existing = _fetch_existing_memories(content, agent_id, top_k=10)
    facts = extract_facts(content, recent, existing)

    existing_hashes = fetch_existing_hashes_for_agent(agent_id, str(DB_PATH))
    mids = []
    for fact in facts:
        if is_duplicate(fact, existing_hashes):
            continue
        # marca o hash antes de inserir para race-condition dentro do batch
        existing_hashes.add(content_hash(fact))
        mid = _mem(agent_id).remember(fact, source=source, importance=importance)
        # armazena content_hash no metadata do Mnemosyne (ou coluna separada)
        _persist_hash(mid, content_hash(fact))
        mids.append(mid)
    return mids
```

#### Migration SQLite

```sql
-- migrations/001_add_content_hash.sql
ALTER TABLE working_memory ADD COLUMN content_hash TEXT;
CREATE INDEX idx_working_memory_hash ON working_memory(content_hash);
```

#### API change

```http
POST /api/memory
Content-Type: application/json

{
  "content": "Hoje decidimos trocar o Visionário de GLM-4.6V para MiniMax M3
  porque GLM não tem chave VLM. Custa $0.01 por análise.",
  "agent_id": "arquiteto",
  "source": "decisao",
  "importance": 0.8,
  "infer": true            ← novo (default true)
}
```

Resposta v0.1: `{id: "mem_xxx", stored: true}` (1 memória)
Resposta M1: `{ids: ["mem_a", "mem_b", "mem_c"], stored: 3, skipped_duplicates: 1}` (N memórias)

**Critérios de aceite M1:**

1. **Teste unitário:** `tests/test_extractor.py` — dado mensagem de entrada,
   extractor retorna lista de fatos (mock LLM)
2. **Teste dedup:** gravar 2× a mesma mensagem → 2ª retorna 0 stored
3. **Teste API:** POST `/api/memory` com `infer=true` retorna `ids.length > 0`
4. **Latência:** `infer=true` < 3s (1 LLM call DS-Flash)
5. **Backward compat:** `infer=false` ou ausente → comportamento idêntico a v0.1

**Riscos M1:**

| # | Risco | Mitigação |
|---|---|---|
| R1 | LLM devolve JSON inválido | Parser defensivo (regex fallback) + retry 2× com tenacity |
| R2 | LLM off-line degrada UX | Fallback `infer=False` automático + warning log |
| R3 | Hash collision (MD5) | Impossível prático (~10^-38); não mitigar |
| R4 | Custo LLM explode | Rate-limit por agent_id (100 adds/min) + cache de prompts |
| R5 | Race condition (2 adds simultâneos) | Hash check dentro de transação SQLite |
| R6 | Migração SQLite em banco grande | Rodar com banco quente OK (ALTER TABLE é atômico) |

### 🟡 M2 — P1: Entity Store + sqlite-vec `vec0` (3-5h)

**Goal:** entidades estruturadas + busca vetorial real (HNSW).

#### Arquivos a criar

- `web/entity_store.py` (novo) — CRUD de entidades + linking
- `migrations/002_create_entities.sql` — tabela `entities`, `memory_entities`

#### Arquivos a alterar

- `web/memory.py` — após extract_facts, chama `entity_store.extract_and_link(facts)`
- `web/app.py:418-426` (recall) — usa sqlite-vec em vez de cosine brute-force
- `web/storage.py` — adiciona `VectorStore` com `vec0` virtual table

#### Schema entities

```sql
-- migrations/002_create_entities.sql
CREATE TABLE IF NOT EXISTS entities (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    type TEXT,              -- person, project, tool, decision, ...
    first_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    mention_count INTEGER DEFAULT 1,
    UNIQUE(name, type)
);

CREATE TABLE IF NOT EXISTS memory_entities (
    memory_id TEXT NOT NULL REFERENCES working_memory(id) ON DELETE CASCADE,
    entity_id TEXT NOT NULL REFERENCES entities(id) ON DELETE CASCADE,
    PRIMARY KEY (memory_id, entity_id)
);

CREATE INDEX idx_entities_name ON entities(name);
CREATE INDEX idx_memory_entities_entity ON memory_entities(entity_id);
```

#### Migration vec0

```sql
-- migrations/003_create_vec0.sql
CREATE VIRTUAL TABLE IF NOT EXISTS memory_embeddings_vec0
USING vec0(
    embedding FLOAT[384],     -- fastembed MiniLM-L12 dimension
    memory_id TEXT PRIMARY KEY
);
```

#### Backfill embeddings existentes

Script `scripts/backfill_vec0.py` (único, idempotente):
```python
# Popula memory_embeddings_vec0 com vetores já calculados em working_memory
# (assumindo que Mnemosyne já armazena embeddings; senão, recalcula via fastembed)
```

**Critérios de aceite M2:**

1. Após M1, fatos são automaticamente parsed para entidades (Person: "Herbert", Project: "EVSCAR", Decision: "troca Visionário")
2. Query por entidade: `GET /api/entities/EVSCAR/memories` retorna todas as menções
3. Latência recall @ top-5 com 10k memórias: **< 50ms** (vs ~5s com cosine brute-force)
4. Backfill completo em < 10 min para 1k memórias existentes
5. Rollback: drop tabelas entities + vec0 volta ao estado anterior

**Riscos M2:**

| # | Risco | Mitigação |
|---|---|---|
| R1 | sqlite-vec não instalado | Setup.py já instala (`sqlite-vec>=0.1.6`); validar com `PRAGMA compile_options` |
| R2 | Embeddings do Mnemosyne em formato diferente | Inspecionar schema antes; converter se necessário |
| R3 | NER LLM (DeepSeek) impreciso em PT-BR | Validar com 50 amostras manuais; refinamento de prompt |
| R4 | Backfill de 1k+ memórias trava Web UI | Rodar em background thread com rate-limit |

### 🟡 M3 — P1: Decay/Eviction (2-3h)

**Goal:** memórias velhas perdem importância automaticamente.

#### Arquivos a alterar

- `scripts/retention.py` (já existe, esboço) — implementar políticas:
  - **T0 (tier 0):** working memory, > 30 dias sem recall → importance *= 0.8
  - **T1:** working memory, > 90 dias sem recall → move to episodic
  - **T2:** episodic, > 365 dias sem reinforcement → flag `archived`
  - **Persona tier:** NUNCA decay (regra do BEAM)

#### Política

```python
# scripts/retention.py (esboço)
DECAY_POLICY = {
    "working_30d_norecall": {"action": "decay", "factor": 0.8},
    "working_90d_norecall": {"action": "consolidate", "target": "episodic"},
    "episodic_365d_noreinforce": {"action": "archive"},
    "persona": {"action": "skip"},  # never decay
}

def run_retention_cycle():
    # 1. SELECT memórias working > 30d WHERE last_recall < now - 30d
    # 2. Aplicar política
    # 3. Log mudanças em retention_audit_log
```

#### Audit log

```sql
CREATE TABLE retention_audit_log (
    id INTEGER PRIMARY KEY,
    memory_id TEXT,
    action TEXT,             -- decay, consolidate, archive
    old_importance REAL,
    new_importance REAL,
    reason TEXT,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

**Critérios de aceite M3:**

1. Cron diário roda `retention.run_retention_cycle()`
2. Memória sem recall há 35 dias tem importance *= 0.8 (auditável)
3. Memória persona NUNCA é tocada (test explícito)
4. Toda ação vira log em `retention_audit_log`
5. UI mostra badge "arquivada" para memórias T2

### 🟢 M4 — P2: Async queue + Postgres backend (4-6h)

**Goal:** indexing não-bloqueante + opção Postgres para multi-tenant.

#### Fila assíncrona

- Novo `scripts/indexer_worker.py` — worker que consome `indexing_queue` table
- API `/api/rag/upload` retorna 202 imediatamente após ENQUEUE
- Worker processa em background (1 worker por processo, via systemd)

#### Postgres backend

- `web/storage.py:PostgresStore` já esboçado — completar
- Strategy: `DATABASE_URL` presente → PostgresStore, senão SQLiteStore
- Migration dual (SQLite → Postgres) via `scripts/migrate_to_postgres.py`
- Schema Postgres com `pgvector` (HNSW index) em vez de sqlite-vec

**Critérios de aceite M4:**

1. Upload de PDF 10MB responde em < 200ms (202 Accepted)
2. Worker processa em < 30s
3. Switch de SQLite → Postgres sem downtime (dual-write durante migração)
4. Performance recall em Postgres ≥ SQLite (mesma latência ou melhor)

### 🟢 M5 — P2: LongMemEval no CI (2h)

**Goal:** regressões de recall detectadas automaticamente.

- `evals/longmemeval_runner.py` (já existe esboço em `scripts/eval_pipeline.py`)
- GitHub Action roda a cada PR que mexe em `web/memory.py`, `web/extractor.py`, `web/dedup.py`
- Métrica: Recall@5 ≥ 90% (abaixo disso bloqueia merge)
- Dataset: subset PT-BR (traduzir 100 perguntas do LongMemEval original)

**Critério de aceite M5:**

1. PR que reduza Recall@5 abaixo de 90% é bloqueado
2. Relatório de eval publicado como comment no PR
3. Runtime total do eval < 5 min

---

## 8. Ordem de execução recomendada

```
M0 (baseline)         1h    [sempre]
   ↓
M1 (extração+dedup)   4-6h  [P0 — maior ROI, destrava qualidade]
   ↓
M2 (entity+vec0)      3-5h  [P1 — performance + significado]
   ↓
M3 (decay)            2-3h  [P1 — sustentabilidade a longo prazo]
   ↓
(parar e medir ganhos reais aqui)
   ↓
M4 (async+postgres)   4-6h  [P2 — só se single-user não bastar]
   ↓
M5 (eval CI)          2h    [P2 — quality gate para contribuições]
```

**Total M0-M3 (P0+P1):** ~10-15h de trabalho (3-4 sessões Pedreiro + 1 Inspetor)
**Total M0-M5 (com P2):** ~16-23h (5-6 sessões)

---

## 9. Riscos e armadilhas (cross-fase)

| # | Risco | Fase | Mitigação |
|---|---|---|---|
| R1 | **Custo LLM explode** se auto-memory chamar `remember()` muitas vezes | M1 | Rate-limit por sessão (50 adds/sessão) + batching |
| R2 | **Latência add()** sobe de ~50ms para ~2-3s (LLM call) | M1 | Aceitável para auto-memory; documentar trade-off |
| R3 | **Memórias Canônicas** (L3 persona) não devem passar por extração | M1 | Skip extraction se `source=canonical` |
| R4 | **Multi-agente**: hashes devem ser scoped por agent_id | M1 | `WHERE channel_id = ?` na query de hashes |
| R5 | **DeepSeek off-line** | M1-M5 | Fallback `infer=False` + warning |
| R6 | **Conflito com Mnemosyne upstream** (que pode mudar schema) | M2 | Manter extensions em tabelas próprias (`prometheus_*`) |
| R7 | **Eval LongMemEval** pode demorar mais que 5min em CI | M5 | Subset de 100 perguntas + cache de embeddings |
| R8 | **Migração SQLite → Postgres** pode perder dados | M4 | Backup completo + dry-run + checksum pós-migração |
| R9 | **Auto-memory skill** hoje grava texto bruto; mudar para infer=true silenciosamente pode quebrar expectativas | M1 | Skill update + comunicação no CHANGELOG |
| R10 | **Hash MD5** é cripto-fraco mas pra dedup basta; alguém pode perguntar | M1 | Documentar que não é propósito de segurança |

---

## 10. Critério global de aceite (M0-M3 = release v0.2)

Após M3, valida que Prometheus Memory v0.2:

1. ✅ `POST /api/memory` com `infer=true` extrai fatos + dedupa (M1)
2. ✅ Entidades estruturadas acessíveis via API (M2)
3. ✅ Recall top-5 latência < 50ms para 10k memórias (M2)
4. ✅ Decay policy roda automaticamente sem tocar persona tier (M3)
5. ✅ Backward compat: `infer=false` preserva comportamento v0.1
6. ✅ Todos os testes em `tests/` passam
7. ✅ Eval LongMemEval Recall@5 ≥ 85% (subset PT-BR)
8. ✅ Migrations SQLite aplicadas sem perda de dados
9. ✅ Documentação: ARCHITECTURE.md + ROADMAP.md + README.md atualizados
10. ✅ CHANGELOG entry: "v0.2.0 — Mem0 V3 patterns (extraction, dedup, entities, vec0, decay)"

---

## 11. Pós-implementação

### Atualizar docs

- `docs/ROADMAP.md`: marcar itens v0.2 como ✅; atualizar v0.3 com P2 (M4-M5)
- `ARCHITECTURE.md`: nova seção "Camada de Extração (Mem0-style)"
- `README.md`: mencionar "Mem0 V3 patterns implementados"
- `CHANGELOG.md`: entrada v0.2.0
- `COMPARISON.md`: atualizar tabela Prometheus vs Mem0

### Gravar no Mnemosyne

- Decisão canônica: "Prometheus Memory v0.2 implementa padrões Mem0 V3
  (extração + dedup hash + entities + vec0 + decay), preservando
  diferenciais L0→L3 + Canvas + Persona + Skills"
- Source: `decisao`, importance: 0.95, scope: global

### Release

- Tag git: `v0.2.0-mem0-patterns`
- GitHub release notes traduzidas PT-BR + EN

---

## 12. Referências

- Mem0 V3 source: https://github.com/mem0ai/mem0
- Mem0 V3 migration: https://github.com/mem0ai/mem0/blob/main/docs/migration/oss-v2-to-v3.mdx
- Mem0 prompts: https://github.com/mem0ai/mem0/blob/main/configs/prompts.py
- LongMemEval: https://github.com/mem0ai/longmemeval
- sqlite-vec: https://github.com/asg017/sqlite-vec
- Prometheus ROADMAP: `docs/ROADMAP.md`
- Prometheus ARCHITECTURE: `ARCHITECTURE.md`
- Estudo comparativo 02/08/2026: `STATE.md` sessão 16

---

## 13. Nota final

Este plano **não** torna o Prometheus "um clone do Mem0". Torna o Prometheus
**melhor que Mem0** para o caso de uso declarado (agentes locais com
significado hierárquico), absorvendo o que Mem0 faz melhor (extração +
dedup) e mantendo o que Mem0 não tem (L0→L3, Canvas, Persona, Skills,
RAG multimodal, 100% self-hosted).

O roadmap futuro (v0.4+) pode explorar:
- Memory consolidation via graph neural networks
- Cross-agent knowledge transfer (persona sharing)
- Active recall (agent pergunta pra memória em vez de só gravar)
- Streaming extraction (extração on-the-fly durante sessão, não só no add)
