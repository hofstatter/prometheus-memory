# DECISIONS — Prometheus Memory

Registro de decisões arquiteturais e resultados de medição que alteram o curso do
plano. Seção nova no topo. Cada entrada: contexto, decisão, evidência, status.

---

## 04/08/2026 — P4 (melhorar recall EN): régua consertada; as 2 "melhorias" de retrieval REJEITADAS

**Contexto:** com a régua honesta (abaixo), medimos 2 melhorias candidatas no subset-20
com judge real DeepSeek (deepseek-chat, temp 0), mesma sessão.

**Evidência (mode=llm, mesma sessão):**

| Config | QA accuracy | Δ vs baseline |
|---|---|---|
| baseline (bge-small-en-v1.5) | **42.1%** | — |
| expansão da pergunta por IA (paráfrases) | 31.6% | **-10.5pp** ❌ |
| embedding BAAI/bge-large-en-v1.5 (dim 1024) | 26.3% | **-15.8pp** ❌ |

**Causas prováveis:** (1) paráfrases afastam a query do vocabulário da evidência EN
(as perguntas do LongMemEval já são otimamente formuladas; o merge por max-score traz
ruído); (2) modelos BGE exigem prefixo de instrução ("Represent this sentence for
searching relevant passages:") que o mnemosyne upstream não adiciona — bge-small é
tolerante, bge-large colapsa sem ele (26.3% era deterministicamente ruim, com e sem
MNEMOSYNE_EMBEDDING_DIM=1024).

**Decisão:** reverter ambas (código `web/memory.py` revertido; eval.yml sem o env de
embedding). **Fica o conserto da régua**: runner agora reporta o mode REAL
(llm vs local-only) + backend (antes dizia "LLM judge" mas rodava proxy de overlap
porque LLM_BACKEND default=ollama e o Ollama está desligado) e o CI fixa
`LLM_BACKEND=deepseek` + `DEEPSEEK_MODEL=deepseek-chat` + `--subset 30`.

**Lições:** (a) todo o P3 (F1/F2/F3) foi medido com proxy, não judge — o "36.8%" era
proxy; o baseline real com judge é 42.1% (e 47.4% na manhã — drift de modelo ainda
existe, mas a régua agora é honesta e pinada); (b) o benchmark EN não melhora com
truques baratos de wrapper — exige trabalho upstream (prefixo de instrução, reranker,
ou granularidade turn-level). **Recomendação:** alvo PT (produção real) ou aceitar o
EN como está.

**Status:** fechada — consertos reais mantidos; experimentos revertidos.

---

## 04/08/2026 — F2/F3 (PLAN P3): resultado NEUTRO no benchmark EN — capacidade mantida, sem "melhoria"

**Contexto:** F2 (key expansion no ingest, `KEY_EXPANSION=llm`, prefixo `Facts: … |`)
e F3 (Chain-of-Note no leitor, `--con`) implementadas conforme plano, testes verdes.

**Evidência (subset-20, seed 42, mesma sessão):** off 36.8% → F1 36.8% → F2 36.8% →
F3 36.8% → **local-only 36.8%** — rótulos byte-idênticos nos 5 runs. Diagnostic:
local-only == LLM-judge ⇒ o erro é do **retrieval** (vocabulário gold fora do top-5
em 63%), não da leitura/juiz. CoN não salva o que não foi recuperado; sinonímia EN
completa não é coberta por mini-mapa nem keyphrases de sessão. subset-100 inviável
(>40min local; CI cancelava nos 60min → `eval.yml` agora `--subset 30`).

**Decisão (Herbert autorizou F1+F2+F3):** as 3 fases ficam como **capabilities
env-gated** (off por default), 86 testes verdes, sem virarem "melhoria" (aceite não
atingido). Fix real: CI passa a rodar `--subset 30`.

**Próximo passo (recomendado):** decidir alvo EN vs PT (produção é PT — morfologia
PT da F1 provada); se EN: query expansion por LLM (opção B) e/ou melhor granularidade
de ingest; pinar modelo reader/judge p/ matar baseline móvel (47.4%→36.8% no mesmo
subset entre sessões).

**Status:** fechada — capabilities mantidas, sem push como melhoria.

---

## 04/08/2026 — F1 (PLAN P3): query-side expansion determinística → resultado NEGATIVO no benchmark EN

**Contexto:** F1 implementada conforme plano (variantes determinísticas: stem EN/PT +
mini-mapa de 12 sinônimos + original, ≤3, merge max-score, env `PROM_QUERY_EXPANSION`,
gate upstream intacto). Critério de aceite do plano: total > 47.4% e multi-session > 20%.

**Evidência (subset-20, seed 42, mesma sessão):** off 36.8% → on 36.8% — **Δ = 0.0pp,
19/19 rótulos idênticos** (`evals/reports/baseline-vs-f1.md`). O mecanismo é válido
(smoke test PT: "formação"→"formou" recupera; off retorna vazio) — mas o mini-mapa é
pequeno demais para a sinonímia semântica das 500 questões EN (pergunta × evidência
sem tokens compartilhados).

**Decisão pendente de Herbert (opções):**
- **A — Manter F1 como ganho de PT-morfologia:** aceita o benefício real de produção
  (ecossistema PT, provado) e registra "sem efeito medido no benchmark EN"; segue para F2.
- **B — Pivotar F1 para expansão por LLM:** `PROM_QUERY_EXPANSION=llm` — DeepSeek gera
  ≤2 paráfrases da query (1 call por recall, env-gated; ~1 call por instância no eval).
  Ataca diretamente a sinonímia semântica. Mudança de arquitetura → novo aceite + custo LLM.
- **C — F1 neutral e seguir para F2:** F2 (key expansion no índice, paper: +9.4% R@k,
  +5.4% QA) ataca o retrieval pelo lado do índice; F3 (Chain-of-Note) ataca a leitura.
  Combinadas podem atingir o target sem LLM por query.

**Status:** aberto — aguardando decisão (não houve improviso; o critério da F1 não foi
atingido e o plano não prevê este caso).

---

## 04/08/2026 — Upstream: `mnemosyne-memory` 3.12.2 é PyPI externo (não editamos site-packages)

**Contexto:** o gate lexical do recall vive em `mnemosyne/core/beam.py:5584-5612`
(`_minimum_recall_relevance` 0.3 p/ ≥4 tokens; `_lexical_relevance` = 0 sem overlap de
tokens → candidatos só-vetoriais morrem). Pacote instalado de `AxDSan/mnemosyne`.

**Decisão:** nenhum edit em site-packages; P3 opera 100% na nossa camada (`web/`,
`evals/`). Follow-up: propor upstream o knob `MNEMOSYNE_LEXICAL_GATE_MIN` + fix da FK
`memory_embeddings` (sessão 37).

**Status:** fechada — registrada em PLAN_QUALIDADE_RECALL_P3.md §Follow-up upstream.
