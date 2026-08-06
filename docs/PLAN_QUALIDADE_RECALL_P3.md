# PLAN — Qualidade do Recall, Parte 3: Gate Lexical + Key Expansion + Chain-of-Note

> **Data:** 04/08/2026
> **Autor:** Arquiteto (sessão 38) — aprovado por Herbert em diálogo
> **Classificação:** MEDIUM (multi-arquivo, toca superfície sensível do recall — Inspetor rigoroso por fase, GIT GATE por fase)
> **Status:** Plano aprovado — execução: F1 inicia APÓS o CI #30935254078 confirmar o baseline (47.4%)
> **Dependências:** baseline publicado (`04d88a9`) · CI `eval.yml` como régua · `mnemosyne-memory 3.12.2` (upstream PyPI — NÃO editamos site-packages)
> **Backup pré-implementação (F1):** obrigatório `web/memory.py`, `evals/longmemeval_runner.py`, `tests/test_mem0_patterns.py`

---

## Contexto

O baseline **QA accuracy 47.4%** (19 instâncias, subset EN oficial) está publicado e o CI roda
report-only. Este plano ataca os três gargalos mapeados, em fases autocontidas e medíveis:

| Gap | Causa | Local | Fase |
|---|---|---|---|
| Multi-session 20% (pior tipo) | gate lexical: `relevance >= row_min_relevance` (0.3 p/ queries ≥4 tokens); `_lexical_relevance` = 0 sem overlap de tokens → **candidatos só-vetoriais (paráfrase) morrem** | `mnemosyne/core/beam.py:5584-5612` (**upstream**) | **F1** |
| Morfologia PT ("formação"≠"formou") | mesmo gate; `_RECALL_SYNONYMS` é EN-curado | upstream | **F1** |
| Retrieval fraco | paper §5.3: key expansion +user facts = **+9.4% recall@k, +5.4% QA** | ingest (nossa camada) | **F2** |
| Leitura (98.9% R@5 → 47.4% QA) | QA prompt extrativo simples; paper §5.5: Chain-of-Note = **+10pp** | `evals/longmemeval_runner.py` (nosso) | **F3** |

### Descoberta arquitetural (sessão 38) — FUNDAMENTAL

`mnemosyne-memory` v3.12.2 é pacote **PyPI externo** (`github.com/AxDSan/mnemosyne`). O gate
lexical vive em `beam.py` (8737 linhas), **fora do nosso repo**. Regra dura deste plano:

> **NENHUM edit em site-packages.** Tudo é feito na nossa camada (`web/`, `evals/`). O pacote
> é re-instalável (perde-se qualquer patch local).

Gate em detalhe (lido em `beam.py`):
- `_minimum_recall_relevance(query_tokens)`: ≥4 tokens → 0.3 · 3 tokens → 0.5 · senão 0.15
- `_lexical_relevance(query_tokens, content)`: tokens exatos + sinônimos (`_RECALL_SYNONYMS`,
  EN) + parcial (substring ≥4 chars) + split de snake_case. **0.0 sem overlap real.**
- Drop: `if relevance >= row_min_relevance` (beam.py:5612, working; ~6055/6177, episodic).
- Já existe relaxamento p/ `broad_multi_hit_query` (≥2 tokens distintos match no candidato set)
  e `MNEMOSYNE_LENIENT_FACT_MATCH` (fact matcher). **Não existe knob para o min_relevance.**
- `enhanced_recall` (intent + synonym + cache + Weibull) existe, mas é método separado —
  nossa camada chama `.recall()`; não é o caminho.

---

## FASE 1 — Query-side Expansion (executar primeiro)

### Decisões

| # | Decisão | Porquê |
|---|---|---|
| F1-D1 | **Query-side expansion na nossa camada**: para cada recall, gerar **≤3 variantes lexicais** (stem simples EN/PT + sinônimos + split de termos); chamar `recall_lane` por variante; **merge por id com max(score)**. Env `PROM_QUERY_EXPANSION=on\|off` (default **off** até medir) | Não toca upstream; o gate fica **intacto** (variantes geram candidatos FTS E passam no gate legitimamente); resolve EN (paráfrase) E PT (morfologia); beneficia produção |
| F1-D2 | **NÃO usar monkey-patch** de `_minimum_recall_relevance` | Frágil em upgrade do pacote; F1-D1 é determinístico e medível. Patch descartado (registrar no CHANGELOG como experimento avaliado) |
| F1-D3 | Variantes: (a) stem por regra simples (sufixos EN `ing/ed/ion/s`, PT `ar/ou/ou-forma/ção/ções`), (b) sinônimos de um mini-mapa, (c) query original sempre inclusa | Cap 3 evita explodir chamadas; regras determinísticas (zero LLM) |
| F1-D4 | Merge: dedup por `id`, conserva **max(score)**, ordena desc, corta em `top_k` | Não infla resultado; ordem estável |

### Implementação (contratos)

**`web/memory.py`** — novo:
```python
def expand_query_variants(query: str, max_variants: int = 3) -> list[str]:
    """Variantes lexicais determinísticas (stem EN/PT + sinônimos + original)."""
    # original SEMPRE primeiro; cap = 3; dedup; ordem estável

def recall_lane_expanded(channel: str, query: str, top_k: int = 5) -> list:
    """recall_lane por variante → merge por id com max(score) → top_k.
    Ativo quando PROM_QUERY_EXPANSION=on; senão delega a recall_lane()."""
```
Env: `PROM_QUERY_EXPANSION` (default off). Stem por regra — sem lib externa.

**`evals/longmemeval_runner.py`** — flag `--query-expansion on|off` (default off): `_recall`
usa `recall_lane_expanded` quando on. Report ganha coluna `query_expansion` no cabeçalho.

**`tests/test_query_expansion.py`** — novo:
- T1: variantes contêm original + stem + sinônimo; ≤3; sem duplicatas
- T2: merge max-score preserva top_k e não duplica ids
- T3: gate intacto — query nonsense ("purple bicycle quantum oatmeal") ainda retorna vazio
- T4: morfologia PT — recall com "formação" encontra memória "formou" (quando on)

### Aceite Fase 1

```bash
pytest tests/                                    # 78 + T1-T4, 0 regressão
python3 evals/longmemeval_runner.py --subset 20 --query-expansion on
# esperado: total > 47.4% e multi-session > 20% (delta real medido)
python3 evals/longmemeval_runner.py --subset 20                     # baseline igual ao antigo (off)
# CI: push web/memory.py + runner dispara eval.yml → artifact ≈ local
# relatório: evals/reports/baseline-vs-f1.md (comparativo)
```

---

## FASE 2 — Key Expansion (depois do F1 mergeado)

### Decisões

| # | Decisão | Porquê |
|---|---|---|
| F2-D1 | `KEY_EXPANSION=llm\|off` (default off). No ingest: **1 chamada LLM em lote por sessão** extrai keyphrases/facts → prefixo `Facts: k1; k2 | <conteúdo>` no conteúdo armazenado | Paper: +9.4% R@k, +5.4% QA. Prefixo alimenta FTS + embeddings + gate. Batch = ~50 calls/instância (centavos) |
| F2-D2 | Aplicar **somente a memórias novas** (sem backfill em produção) | Migração de dados fora de escopo; env-gated; formato documentado |
| F2-D3 | Fallback: LLM indisponível → grava raw (degraded, igual padrão existente) | Nunca quebra o write (mesma filosofia do `remember_inferred`) |

### Implementação (contratos)

**`web/extractor.py`** — novo:
```python
def extract_keyphrases_batch(texts: list[str]) -> list[str]:
    """1 call_llm por sessão (temperature 0, timeout 45) → keyphrases curtas.
    Fallback: LLM indisponível → retorna lista vazia (caller grava raw)."""
```

**`web/memory.py`** — `remember_lane(..., key_expansion: bool = None)`:
quando `KEY_EXPANSION=llm` e `key_expansion=True`, prefixa `Facts: … | ` no content
antes de `Mnemosyne.remember`. Sem mudança de assinatura pública obrigatória.

**`evals/longmemeval_runner.py`** — flag `--key-expansion` aplicada no `_ingest`.

**`tests/test_key_expansion.py`** — novo:
- T5: prefixo correto quando on; content original preservado após o prefixo
- T6: fallback LLM off → grava raw (sem prefixo, degraded)
- T7: idempotência — dupla chamada não duplica prefixo

### Aceite Fase 2

```bash
pytest tests/                                    # 78 + F1 + T5-T7, 0 regressão
python3 evals/longmemeval_runner.py --subset 20 --query-expansion on --key-expansion llm
# esperado: delta positivo adicional vs F1 (paper sugere +5.4% QA)
# relatório: evals/reports/f1-vs-f2.md
```

---

## FASE 3 — Chain-of-Note no Leitor (depois do F2 mergeado)

### Decisões

| # | Decisão | Porquê |
|---|---|---|
| F3-D1 | `QA_PROMPT_CON` (leitor): instrui o modelo a **anotar fatos relevantes por memória → depois responder**. Flag `--con` no runner | Paper §5.5: +10pp. Mede o **teto** do sistema com reader otimizado |
| F3-D2 | Produção: vira **template documentado** para agentes (docs/) — leitura é agent-side; não muda recall de produção | Isola o ganho de retrieval (F1/F2) do ganho de leitura (F3) |
| F3-D3 | Judge inalterado (rubrica binária, temperature 0) | Não confundir o leitor com o avaliador |

### Implementação (contratos)

**`evals/longmemeval_runner.py`** — `QA_PROMPT_CON` (passo 1: anote o fato-chave de cada
memória relevante; passo 2: responda com base nas anotações) + flag `--con`.

**`tests/test_longmemeval.py`** — +T8: `QA_PROMPT_CON` contém as duas etapas; formatação válida.

**`docs/`** — novo `docs/AGENT_READING_TEMPLATE.md` (prompt CoN reutilizável por agentes
que consomem o recall do Prometheus).

### Aceite Fase 3

```bash
pytest tests/                                    # 78 + F1 + F2 + T8, 0 regressão
python3 evals/longmemeval_runner.py --subset 20 --query-expansion on --key-expansion llm --con
# esperado: delta positivo adicional (paper sugere até +10pp)
# relatório: evals/reports/f2-vs-f3.md
```

---

## Gate do CI (fase final, PR separado — NÃO agora)

Após 3 rodadas de baseline estável com F1+F2+F3: se total ≥ **55%**, transformar o
`eval.yml` em gate (remover `continue-on-error` + threshold real). Requer aprovação
explícita de Herbert (mudança 1-linha + remoção do report-only).

---

## Riscos e armadilhas

| Risco | Mitigação |
|---|---|
| Query expansion traz ruído (variantes erradas inflam top_k) | Cap ≤3; merge max-score; T3 garante nonsense-query vazia |
| F2 custo/latência no CI (~5k chamadas DeepSeek em 100 instâncias) | Batch 1/sessão; medir subset-20 primeiro; cron semanal tolera; `continue-on-error` |
| Efeitos das fases se confundirem | Matriz de flags + relatório comparativo por fase; 1 PR por fase |
| Gate existe para bloquear nonsense — não queremos enfraquecê-lo | F1 preserva o gate; variantes passam nele legitimamente |
| F2 altera conteúdo armazenado (prefixo visível) | Env-gated; só memórias novas; formato documentado |
| F3 não refletir produção (leitura agent-side) | Documentado: F3 mede o teto; produção ganha via template |
| Upgrade do pacote mnemosyne pode mudar o gate | Pin `mnemosyne-memory==3.12.2` no requirements; testes T1-T4 protegem a camada |

## Follow-up upstream (NÃO bloqueia este plano)

1. **Env knob `MNEMOSYNE_LEXICAL_GATE_MIN`** no `AxDSan/mnemosyne` (beam.py:5584) — proposta
   de PR: default preserva o comportamento atual; knob permite relaxar sem patch.
2. **Fix da FK `memory_embeddings`** (bug da sessão 37: FK→memories episódica quebra insert
   de working em DB fresco) — PR upstream + remove `_prepare_eval_db` workaround.

## Fora do escopo

- Time-aware query expansion (temporal já 80% — prioridade menor) · stemmer PT no FTS5 upstream
- LongMemEval-M (500 sessões) · tradução PT-BR do dataset (D7 da Parte 2 — ferramenta futura)
- Threshold/gate ativo no CI (vem na fase final, ≥55% + aprovação)

---

## Arquivos afetados (resumo)

| Arquivo | Fase | Ação | Backup |
|---|---|---|---|
| `web/memory.py` | F1+F2 | `expand_query_variants` + `recall_lane_expanded` + prefixo F2 | Obrigatório (F1) |
| `web/extractor.py` | F2 | `extract_keyphrases_batch` | Obrigatório |
| `evals/longmemeval_runner.py` | F1+F2+F3 | flags `--query-expansion/--key-expansion/--con` + `QA_PROMPT_CON` | Obrigatório |
| `tests/test_query_expansion.py` | F1 | **novo** | — |
| `tests/test_key_expansion.py` | F2 | **novo** | — |
| `tests/test_longmemeval.py` | F3 | +T8 | Obrigatório |
| `evals/reports/` | todas | relatórios comparativos | — |
| `docs/AGENT_READING_TEMPLATE.md` | F3 | **novo** (template CoN p/ agentes) | — |
| `CHANGELOG.md` | todas | 1 entrada por fase | Obrigatório |
