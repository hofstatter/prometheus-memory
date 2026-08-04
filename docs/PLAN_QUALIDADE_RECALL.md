# PLAN — Qualidade do Recall: NER LLM Entities v1.1 + Dedup Semântico + Fix FTS5 Notas

> **Data:** 04/08/2026
> **Autor:** Arquiteto (sessão 37) — aprovado por Herbert em diálogo
> **Classificação:** SMALL (6 arquivos, sem superfície sensível além de DB local)
> **Status:** Plano aprovado — aguarda execução do Pedreiro
> **Dependências:** Prometheus v0.2.0-projetos rodando · DeepSeek API key ativa (já em uso pelo `extractor.py`) · Mnemosyne com FTS5 ativo (já em produção)
> **Backup pré-implementação:** `~/backups/prometheus-memory/pre-qualidade-recall/` (obrigatório antes de editar `web/entity_store.py`, `web/memory.py`, `web/notes_routes.py`)

---

## 1. Contexto e motivação

A sessão 36 entregou os **padrões Mem0 V3** (extração LLM de fatos, dedup SHA-256 exato,
threshold no recall, entities v1 heurística, grounding temporal) — validado em produção
com `LLM_BACKEND=deepseek`. Este plano fecha os **3 gaps de qualidade do recall** que
sobraram, verificados com dados reais na sessão 37:

### G1 — Entity store v1 é lixo (heurística)

Diagnóstico real da produção (`prometheus_entities`, 4 linhas):

```
2x  auto    Mini            ← "MiniMax M3" quebrado pelo regex (2 tokens máx)
1x  auto    Visionario
1x  auto    Model           ← palavra genérica
1x  auto    Vision Language ← fragmento de frase
```

Problemas da heurística atual (`web/entity_store.py:17-25`):

1. **Acrônimos escapam** — o regex `[A-ZÀ-Ý][a-zà-ÿ0-9.-]{2,}` exige minúsculas após a
   1ª letra; `FASHN`, `EVSCAR`, `API`, `MCP` **nunca** são capturados.
2. **Falsos positivos** — início de frase capitalizado vira entidade ("Decisão", "Trocar").
3. **Sem tipo** — tudo entra como `type='auto'`; impossível filtrar pessoa/org/projeto/tech.
4. **Sem canônicos** — "MiniMax" vs "MiniMax M3" viram entidades distintas (aliases ficam
   para v1.2).

**Por que importa:** entidades são o índice de "quem/o quê" das memórias. Com elas boas,
"mostre tudo que você sabe sobre FASHN" responde via `memories_for()` sem depender de busca
semântica. Hoje isso **não funciona**.

### G2 — Dedup é só hash exato

O dedup atual (`web/dedup.py`) compara SHA-256 do texto normalizado. Quase-duplicatas
semânticas passam:

- "Decisão: trocar Visionário GLM por MiniMax M3 em 2026-08-03"
- "Visionário foi substituído pelo MiniMax M3 no dia 03/08"

→ as duas são gravadas, o recall volta poluído (o problema exato que o Mem0 V3 resolve
com `existing_memories` no prompt — mas que escapa quando o LLM reformula).

### G3 — FTS5 de notas rebuilda por request

`web/notes_routes.py:298-325` cria o FTS5 e **re-insere TODAS as notas a cada chamada**
de `/notes/fts`. A tabela `notes_fts` acumula duplicatas (6 linhas na produção) e a busca
degrada com o volume. O recall de memórias já é híbrido (Mnemosyne nativo: 50% vetor +
30% FTS5 + 20% importância, `fts_working` com 176 linhas em produção) — **não precisa de
FTS5 novo no sidecar**. Só as notas têm o defeito.

---

## 2. Decisões técnicas (aprovadas por Herbert em 04/08)

| # | Decisão | Porquê |
|---|---|---|
| D1 | **Extração de entidades em lote** — 1 chamada LLM por `remember_inferred` com todos os fatos; linking por substring | Custo: ~1 request por gravação, não 1 por fato |
| D2 | **Taxonomia fixa:** `person \| org \| project \| tech \| other` | Filtrável e consistente; tipos livres geram ruído ("empresa" vs "org") |
| D3 | Reusar `scripts/llm_backend.call_llm` | Mesma infra do `extractor.py` (DeepSeek em prod, degrada para vazio) — zero dependência nova |
| D4 | **Fallback em cascata:** LLM indisponível/vazio/JSON inválido → heurística regex atual | Write nunca quebra; coerente com o padrão `degraded` do extractor |
| D5 | Flag `ENTITY_LLM=on\|off` (default on) | Kill switch sem deploy se custo/latência incomodar |
| D6 | Lookup de entidade por `name` (sem filtro de type); upgrade `type='auto'` → tipo real no mention | Dados v1 existentes se curam organicamente; sem migração destrutiva |
| D7 | **Dedup semântico reusa o recall já existente** — zero chamadas LLM extras | `remember_inferred` já faz `recall_lane(chan, content, top_k=10)` (memory.py:98); só falta usar o `score` |
| D8 | Score do recall é 0..1 (capado em `min(score*k, 1.0)` no beam) → threshold default `SEMANTIC_DEDUP_THRESHOLD=0.90`, **calibrar antes de fixar** | Escala confirmada no código do Mnemosyne |
| D9 | `notes_fts` passa a sincronizar **incrementalmente** no create/update/delete da nota | Fim do rebuild O(n) por request e das duplicatas |
| D10 | Sem backfill em massa de entidades; sem aliases/canonização | Escopo contido; v1.2 fica para depois |

---

## 3. Fases de implementação

### 🔴 Fase 1 — NER LLM entities v1.1 (`web/entity_store.py`)

**Arquivo:** `web/entity_store.py` (alterar)

#### 1.1 Novo prompt e extração LLM

```python
ENTITY_PROMPT = """Extraia entidades nomeadas presentes NOS FATOS abaixo.
Use APENAS os tipos: person, org, project, tech, other.
INCLUA acrônimos (ex: FASHN, EVSCAR, MCP, API).
EXCLUA termos genéricos (ex: modelo, projeto, decisão, sistema).
Uma entidade por objeto. Se não houver nenhuma, retorne [].

Formato: JSON array, um objeto por entidade:
[{{"fact": <índice do fato>, "name": "<nome>", "type": "<tipo>"}}]

Fatos:
{numbered_facts}

Output:"""

def extract_entities_llm(text: str, max_tokens: int = 300) -> list[dict]:
    """Extrai entidades via LLM. Falha/vazio → [] (caller decide fallback)."""
    # Mesmo padrão de import do extractor.py:22 (loop de sys.path candidates
    # porque na produção o backend vive em web/scripts; no repo em scripts/).
    from llm_backend import call_llm
    raw = call_llm(ENTITY_PROMPT.format(numbered_facts=text),
                   max_tokens=max_tokens, temperature=0, timeout=45)
    # parse tolerante: slice "[".."]" (mesmo padrão de extractor._parse)
    ...

def extract_entities_batch(facts: list[str]) -> dict[int, list[dict]]:
    """1 chamada LLM com fatos numerados → {índice_fato: [entidades]}.

    Garantia anti-alucinação: entidade só é aceita se
    name.lower() estiver contido no fato (substring) — índice do LLM é
    hint, não contrato.
    """
    ...
```

#### 1.2 `extract_and_link` adaptado (D6)

```python
def extract_and_link(memory_id: str, text: str, entities: list[dict] | None = None) -> int:
    """entities=None → ENTITY_LLM=on ? extract_entities_llm : heurística."""
    ...
    # Lookup: SELECT id, type FROM prometheus_entities WHERE name = ?  (sem filtro de type)
    # Se existe e type='auto' e LLM deu tipo real → UPDATE ... SET type=? junto
    #   com last_seen/mention_count
    # Se novo → INSERT com type do LLM (ou 'auto' no caminho heurístico)
    # Link → INSERT OR IGNORE INTO prometheus_memory_entities
```

**Critério de aceite Fase 1:**
- `ENTITY_LLM=off` → comportamento idêntico ao v1 (heurística) — teste c6 existente passa.
- `ENTITY_LLM=on` + mock do `call_llm` → `FASHN`/`EVSCAR` linkam com type `project`.
- Entidade `type='auto'` pré-existente recebe upgrade de tipo no mention seguinte.

### 🔴 Fase 2 — Dedup semântico (`web/memory.py`)

**Arquivo:** `web/memory.py` (alterar, função `remember_inferred`)

Integração no fluxo existente (memory.py:93-134):

```python
SEMANTIC_DEDUP = os.getenv("SEMANTIC_DEDUP", "on").lower() in ("1", "on", "true")
SEMANTIC_DEDUP_THRESHOLD = float(os.getenv("SEMANTIC_DEDUP_THRESHOLD", "0.90"))

# no lugar de: existing_texts = [... for x in recall_lane(chan, content, top_k=10)]
existing = recall_lane(chan, content, top_k=10)
existing_texts = [x.get("content", "")[:300] for x in existing]
existing_scores = [float(x.get("score") or 0.0) for x in existing]
max_existing = max(existing_scores) if existing_scores else 0.0

# no loop de fatos (antes de gravar):
if SEMANTIC_DEDUP and max_existing >= SEMANTIC_DEDUP_THRESHOLD:
    if _is_near_dup(fact, existing):      # guarda de contenção (ver abaixo)
        skipped.append(fact)              # vira skipped_duplicates
        continue
```

Guarda de contenção (evita over-dedup quando o conteúdo tem 2+ fatos e só 1 bate):

```python
def _is_near_dup(fact: str, existing: list[dict]) -> bool:
    f = fact.lower().strip()
    for row in existing:
        if float(row.get("score") or 0.0) < SEMANTIC_DEDUP_THRESHOLD:
            continue
        c = row.get("content", "").lower()
        if f in c or c in f:          # contenção textual + score alto
            return True
    return False
```

**⚠️ Passo obrigatório antes de fixar o threshold:** rodar um script de calibração que
imprime a distribuição de `score` do `recall_lane` contra memórias conhecidamente
duplicadas × distintas (ex: `scripts/calibrate_semantic_dedup.py`, 1x na vida, não sobe
pro fluxo). O default 0.90 é hipótese — o valor final fica documentado no CHANGELOG.

**Critério de aceite Fase 2:**
- Mock `call_llm` retornando fato A; 2ª gravação com fato quase-idêntico B (reformulado)
  → `skipped_duplicates >= 1`, `stored == 0`, **sem chamada LLM extra**.
- Fatos distintos no mesmo conteúdo → nenhum skip indevido (guarda de contenção).
- `SEMANTIC_DEDUP=off` → comportamento atual (só hash exato).

### 🟡 Fase 3 — Fix FTS5 de notas (`web/notes_routes.py`)

**Arquivo:** `web/notes_routes.py` (alterar)

- Extrair a sincronização do índice para `_sync_notes_fts()`: idempotente, cria a tabela
  `notes_fts` (já existe), e **apenas insere notas novas / atualiza notas mudadas**
  (comparar mtime ou checksum por nota).
- Chamar `_sync_notes_fts()` em `import_url()` (após criar), `update_note()`, `delete_note()`
  (com delete da linha no índice).
- `/notes/fts` passa a **só consultar** (MATCH + rank), sem re-inserir nada.
- Na implantação: **rebuild único** (`DELETE FROM notes_fts` + reindex) para limpar as
  duplicatas acumuladas (6 linhas atuais).

**Critério de aceite Fase 3:**
- 2 chamadas seguidas a `/notes/fts` → `notes_fts` **não cresce** (sem duplicatas novas).
- Criar nota → aparece no índice; editar → snippet reflete; deletar → some.
- Rebuild único documentado no CHANGELOG.

### 🟢 Fase 4 — Testes + docs

**Arquivos:** `tests/test_mem0_patterns.py` (alterar), `CHANGELOG.md` (alterar),
`docs/ROADMAP.md` (alterar — marcar itens)

Testes novos (mock de `call_llm`, nunca LLM real):

| Teste | O que cobre |
|---|---|
| `test_c8_entities_llm_acronyms` | `FASHN`/`EVSCAR` linkam com type `project`; `list_entities()` reflete |
| `test_c9_entities_type_upgrade` | insert manual `('X','auto')` → `extract_and_link` com tipo real → type atualizado |
| `test_c10_entities_fallback` | `call_llm → ""` → heurística ainda linka (c6 não pode quebrar) |
| `test_c11_batch_mapping` | 3 fatos, resposta LLM com índices → cada memory_id linka só suas entidades |
| `test_c12_semantic_dedup` | A vs B quase-idêntico → 2º é skipped; sem chamada LLM extra |
| `test_c13_semantic_guard` | conteúdo 2 fatos, só 1 bate → só o que bate é skip |
| `test_c14_notes_fts_idempotent` | 2 chamadas ao sync → sem duplicatas em `notes_fts` |

Docs:
- `CHANGELOG.md`: "🧠 Qualidade do Recall: NER LLM entities v1.1 (5 tipos fixos, lote,
  fallback heurístico, `ENTITY_LLM`) · dedup semântico (`SEMANTIC_DEDUP_THRESHOLD`) ·
  notes_fts incremental (rebuild único na implantação)".
- `docs/ROADMAP.md`: marcar `[x]` em "Dedup semântico + retrieval híbrido FTS5/BM25 +
  semântico + threshold (Mem0 parity — P0c, refinamento)" e "FTS5 para busca de notas"
  (nota: recall híbrido é nativo do Mnemosyne; FTS5 sidecar de notas foi consertado).

**Critério de aceite Fase 4:** `pytest tests/test_mem0_patterns.py` → 14 testes PASS
(7 existentes + 7 novos), 0 regressão.

---

## 4. Critério de aceite global (executável)

```bash
cd ~/Projetos/prometheus-memory

# 1. Testes
python -m pytest tests/test_mem0_patterns.py -v
# Esperado: 14 passed, 0 failed

# 2. Calibração do dedup semântico (uma vez)
python scripts/calibrate_semantic_dedup.py
# Esperado: relatório de distribuição de scores → threshold final no CHANGELOG

# 3. Ao vivo (produção, LLM real)
curl -X POST localhost:8777/api/remember_inferred \
  -H 'Content-Type: application/json' \
  -d '{"content":"FASHN e EVSCAR usam o Prometheus Memory"}' ...
# Esperado: degraded=false; FASHN/EVSCAR aparecem em /api/entities com type real

# 4. notas/fts idempotente
curl -X POST localhost:8777/api/notes/fts -d '{"query":"..."}' (2x)
# Esperado: SELECT COUNT(*) FROM notes_fts estável entre chamadas
```

## 5. Riscos e mitigação

| Risco | Mitigação |
|---|---|
| LLM retorna JSON malformado | Parser tolerante (slice `[`..`]`) → fallback heurística |
| LLM alucina entidade fora do fato | Substring match obrigatório (`name.lower() in fact.lower()`) |
| Índice errado no batch | Substring match resolve — índice é hint, não contrato |
| Threshold 0.90 fora da escala real | Calibração obrigatória (Fase 2) antes de fixar; flag env |
| Over-dedup em conteúdo multi-fato | Guarda de contenção `_is_near_dup` |
| Duplicatas acumuladas em `notes_fts` | Rebuild único na implantação (DELETE + reindex) |
| Custo LLM extra | Lote único por gravação + `ENTITY_LLM=off` (kill switch) |
| Deadlock SQLite (2ª escrita no loop) | `extract_and_link` mantém conexão própria (padrão atual) |
| Teste c6 existente quebrar (lookup sem filtro de type) | Lookup por name-only é **superset** do atual; c6 continua válido |
| Score híbrido não é cosseno puro | Fase 2 mede a escala real antes de confiar no valor |

## 6. Fora do escopo (v1.2+)

- Aliases/canonização de entidades ("MiniMax" ≡ "MiniMax M3")
- Desambiguação e grafo de relações entre entidades
- Backfill em massa de entidades existentes
- Dedup semântico via LLM (custo alto; guarda de contenção cobre o caso comum)

---

## 7. Arquivos afetados (resumo)

| Arquivo | Ação | Backup |
|---|---|---|
| `web/entity_store.py` | Alterar (NER LLM + lote + upgrade de type) | Obrigatório |
| `web/memory.py` | Alterar (dedup semântico) | Obrigatório |
| `web/notes_routes.py` | Alterar (sync incremental) | Obrigatório |
| `tests/test_mem0_patterns.py` | Alterar (7 testes novos) | — |
| `scripts/calibrate_semantic_dedup.py` | **Criar** (calibração 1x) | — |
| `CHANGELOG.md` / `docs/ROADMAP.md` | Alterar (docs) | — |
