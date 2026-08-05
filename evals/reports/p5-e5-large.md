# P5 — Spike e5-large (multilingual) vs baseline bge-small-en

- Data: 04/08/2026 · régua: PT hit@5 (`scripts/eval_pt_recall.py`) + regressão EN (LongMemEval subset-20, judge DeepSeek real, mesma sessão)
- Candidato: `intfloat/multilingual-e5-large` (1024d, ~560M) · Baseline: `BAAI/bge-small-en-v1.5` (384d)
- DB de eval isolado (PROMETHEUS_DB=tmp) — **produção NÃO foi tocada** no spike (o 1º run com bug de env foi revertido e limpo)

## Resultados

| Métrica | bge-small (baseline) | e5-large | Δ |
|---|---|---|---|
| **PT hit@5 — gate lexical real** | 54.5% (12/22) | 54.5% (12/22) | **0.0pp** |
| **PT hit@5 — gate relaxado (isola embedding)** | 43.8% (14/32) | 46.9% (15/32) | **+3.1pp** |
| **EN LongMemEval QA (judge real, mesma sessão)** | 47.4% (9/19) | 36.8% (7/19) | **-10.6pp** ❌ |
| Latência PT (p50, i7 CPU) | ~8ms | ~42ms | ~5x |

## Análise

1. **Gate lexical domina o recall atual**: com overlap de tokens (perguntas fáceis), o FTS5
   encontra sozinho — os dois modelos empatam. O gate upstream (`beam.py _lexical_relevance`,
   hardcoded, sem knob) **zera candidatos sem overlap de tokens** antes de o vetor decidir.
   É a mesma descoberta da DECISIONS.md (upstream, P3): o problema do recall é retrieval
   + gate, não o embedding em si.
2. **Isolando o embedding (gate relaxado)**: e5-large ganha +3.1pp no PT — benefício REAL
   mas modesto, e depende de um knob que o upstream não expõe.
3. **Regressão EN -10.6pp (mesma sessão, judge real)**: piora significativa no benchmark
   oficial. Custo de latência ~5x no CPU.
4. **Drift de judge confirmado de novo**: baseline EN mediu 47.4% agora vs 42.1% na tarde
   (mesmo subset, judge pinado) — comparações só valem na mesma sessão.

## Veredito (critério PLAN_EMBEDDING_MULTILINGUE D4)

Critério: PT ≥ +10pp E EN não regride > 2pp E latência aceitável.

- PT: **+3.1pp** (isolado) / 0.0pp (gate real) → **NÃO atende ≥ +10pp**
- EN: **-10.6pp** → **NÃO atende (regride > 2pp)**
- Latência: 42ms (aceitável tecnicamente, mas 5x pior)

→ **e5-large REJEITADO para migração.** Manter `bge-small-en-v1.5`. Nenhuma mudança em
produção. Decisão registrada em `docs/DECISIONS.md`.

## Próximos passos reais (para melhorar recall de verdade)

1. **Knob do gate lexical upstream** (`MNEMOSYNE_LEXICAL_GATE_MIN`) — o +3.1pp do e5-large
   e qualquer ganho de embedding ficam trancados atrás do gate. Proposta já registrada.
2. **Reranker** ou granularidade de ingest (turn-level) — ataca o retrieval, não o vetor.
3. **Alvo PT (produção)** com métricas PT contínuas (a régua PT nova já fica no repo).

## Reservas documentadas

- `paraphrase-multilingual-mpnet-base-v2` (~278M) e `jinaai/jina-embeddings-v3` (~570M):
  candidatos multilíngues do fastembed; não testados porque o critério já foi reprovado
  pelo melhor candidato da família (e5-large).
- Stella 1.5B e bge-m3: **fora do catálogo fastembed 0.8.0** (verificado) — exigiriam
  engine nova/API; decidido não fazer.
