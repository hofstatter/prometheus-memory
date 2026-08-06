# DECISIONS — Prometheus Memory

Registro de decisões arquiteturais e resultados de medição que alteram o curso do
plano. Seção nova no topo. Cada entrada: contexto, decisão, evidência, status.

---

## 06/08/2026 — Sessão 44: D6 roteamento visual · D7 doctor.* fora do repo · D8 cascata de consulta externa

**Contexto (sessão 44, pré-commit público F1/F1.1):** Herbert aprovou (1) commit do F1/F1.1 no
`prometheus-memory` + docs em 4 idiomas + screenshot de amostra, (2) regra explícita de roteamento
de captura de tela, (3) política de uso para os MCPs pagos/limitados (Tavily free 1K req/mês;
Firecrawl free 1.278 créditos restantes, renova 1.000 em 22/08/2026).

- **D6 — Roteamento de captura (visual):** `localhost/privado → Playwright` (roda no Chromium local,
  autentica e interage); `URL pública → ScreenshotAPI` ($9/mês, render externo não enxerga localhost;
  sempre `enable_caching=true`). Registrado em `visionario.md` + GUARDRAILS + FLUXO_BIMODELO.
- **D7 — Artefatos gerados fora do repo:** `web/mnemosyne-doctor.{json,md}` são saída de diagnóstico,
  não fonte → `.gitignore`, nunca versionar.
- **D8 — Cascata de consulta externa (anti-custo):** 1) doc de lib → Context7 (grátis) ·
  2) código real → gh_grep (grátis) · 3) pesquisa web/factual → Tavily (default, 1K req/mês) ·
  4) ler URL específica → Firecrawl scrape · 5) mapear/crawlear site → Firecrawl map/crawl ·
  6) screenshot localhost → Playwright · 7) screenshot público → ScreenshotAPI. **Regras duras:**
  nunca Tavily+Firecrawl na mesma query (fallback, nunca paralelo); nunca buscar pago se
  Context7/gh_grep resolvem; `firecrawl_search` só como fallback ou com `scrape_results=true`.

**Status:** fechadas — aplicadas na sessão 44 (docs de config do ecossistema + este repo).

---

## 06/08/2026 — F1.1: Visionário = glm-4.5v (não existe "glm-4.7v"); backfill 769 edges; visual colapsa p/ hubs

**Contexto:** aprovado (1) glm-4.5v como Visionário, (2) melhorias visuais F1.1 e (3) enriquecer/migrar
dados existentes para o grafo real. Achados de medição mudaram o curso:

- **"GLM-4.7V" NÃO existe no Z.AI Coding Plan.** Testes diretos na API (`api.z.ai/api/coding/paas/v4`):
  `glm-4.7` aceita só `text` (rejeita `image_url`, HTTP 400); `glm-4.7v` → `Unknown Model`;
  **`glm-4.5v` → aceita imagem** (validado 3×). `glm-4.6v` timeout (inconclusivo). O registry do
  opencode não lista 4.5v → **declarado no `opencode.jsonc`** (`provider.zai-coding-plan.models.glm-4.5v`
  com `attachment: true` — schema confirma o shape). `visionario.md` → `model: zai-coding-plan/glm-4.5v`.
- **Backfill (migração) escreve em `graph_edges`:** script `scripts/backfill_graph_edges.py` —
  M1 gists→`ctx` (339) · M2 mentions compartilhadas (conf≥0.8, grupos ≥2) → `references` (417) ·
  M3 `prometheus_memory_entities` → `mentions` (13). Total **769 edges** (de 10). Idempotente,
  endpoints validados, backup do DB pré-apply, `mnemosyne doctor` critical=0/error=0.
- **Visual:** ≤40 nós → `circular` (G6) com labels; **>40 nós → colapsa para o subgrafo de
  hubs+entidades** (fitView comprimia 232 nós para zoom ~0.03 = ilegível; zoom fixo 0.65-0.75).
  Nota do glm-4.5v: 2/10 (hairball, sem labels) → **7/10 APROVADO** após o colapso.

**Decisões:** D1 glm-4.5v (validado) · D2 switch de layout por tamanho com colapso p/ hubs ·
D3 backfill idempotente com dedup pré-existente + intra-batch + reverso (fix Inspetor) ·
D4 mentions com conf≥0.8 + normalização anti-ruído · D5 entidades por nome (casa com triples).

**Evidência (06/08):** prod live `/api/graph?limit=500` → **232 nós / 501 arestas** (23ms) ·
`graph_edges` pós-apply 769 (0 duplicatas, 0 self-loops) · doctor 0 erros · Inspetor APROVOU a
migração (1 fix LOW aplicado: dedup reverso undirected) · Playwright v7 + glm-4.5v 7/10.
**Backups:** `semantica-graph-f1_1/20260806-035946/` (config+index.html+docs) ·
`f1_1-graphservice-memoria/20260806-040209/` · `semantica-graph-f1_1/20260806-040245/mnemosyne-pre-backfill.db`.

**Status:** fechada — F1.1 aceite CA1–CA9 verde; detalhe em `docs/PLAN_SEMANTICA_GRAFO_F1_1.md`.



## 06/08/2026 — F1 Grafo real: adotar analytics puros do semantica; SEM boost extra no recall

**Contexto:** varredura `semantica-agi/semantica` (MIT, "Palantir open-source") a pedido
do Herbert para melhorar o Grafo :8777. Core do pacote inviável como dependência
(pyproject puxa torch/spacy/faiss/opencv/librosa/umap → 3-5GB); módulos-alvo de grafo
(centrality, community, link_pred, conflicts, decisions, temporal) são quase pure-Python.
Gap no nosso lado: `/api/graph` era O(n²) fake (recall CLI + hub-spoke memória↔projeto,
cap 100) e a UI G6 só orbitava projetos — ignorava `graph_edges`/`triples` reais.

**Decisões (D1–D5, detalhe em `docs/PLAN_SEMANTICA_GRAFO_F1.md`):**
- **D1 — SEM boost extra no recall:** o `graph_bonus` por grau **já roda upstream**
  (mnemosyne beam.py:6250-6261, `min(edge_count*0.02, 0.08)`, knob `MNEMOSYNE_GRAPH_BONUS`).
  F1 **expõe** `graph_degree` no payload do `/api/memory/recall` (visibilidade) sem alterar
  scoring — evita dupla contagem.
- **D2 — Grafo computado por request:** dados reais pequenos hoje (10 edges/347 gists);
  PageRank+degree em Python puro é sub-ms. Cap `?limit=500`.
- **D3 — Dois alvos:** repo canônico `~/Projetos/prometheus-memory/web/` + **cópia viva
  `~/Projetos/web/`** (WorkingDirectory do systemd user `prometheus-web.service` — achado
  crítico da sessão). Implementa no repo → sync por arquivo → restart; **.env nunca tocado**.
- **D4 — Nada em site-packages/mnemosyne** (padrão PLAN_QUALIDADE_RECALL_P3).
- **D5 — Analytics em Python puro:** `pagerank()` ~30 linhas adaptado de
  `semantica/kg/centrality_calculator.py` (MIT, NOTICE no docstring). Zero deps novas.

**Evidência (06/08):** `/api/graph` 3ms (repo/test client) e 10ms (prod :8777 com token),
20 nós + **11 arestas reais** (10 `ctx` + 1 `executou`), degree+pagerank por nó, recall 200
com `graph_degree`, UI com legenda de edge types + badge de contagens (Playwright snapshot
na instância de teste 127.0.0.1:18777). Backups: `~/backups/herbert/semantica-graph-f1/20260806-031327/`.

**Status:** fechada — F1 aceite CA1-CA8 verde (ver PLAN_SEMANTICA_GRAFO_F1.md §4).



## 04/08/2026 — P5 (embedding multilíngue): e5-large REJEITADO — gate lexical upstream domina; regressão EN -10.6pp

**Contexto:** Herbert escolheu `intfloat/multilingual-e5-large` (~560M, 1024d, 100+ idiomas)
para substituir o `bge-small-en-v1.5` (só EN) e dar suporte multilíngue real ao projeto
público. Spikes medidos com régua PT nova (`scripts/eval_pt_recall.py`, 22-32 pares reais
do ecossistema) + regressão EN (LongMemEval subset-20, judge real, MESMA sessão).

**Evidência (mesma sessão, DB de eval isolado):**

| Métrica | bge-small | e5-large | Δ |
|---|---|---|---|
| PT hit@5 (gate lexical real) | 54.5% | 54.5% | 0.0pp |
| PT hit@5 (gate relaxado — isola embedding) | 43.8% | 46.9% | +3.1pp |
| EN LongMemEval QA (judge real) | 47.4% | 36.8% | **-10.6pp** ❌ |
| Latência PT (p50, i7) | 8ms | 42ms | ~5x |

**Descoberta central:** o **gate lexical upstream** (`beam.py _lexical_relevance`,
hardcoded, sem knob env) zera candidatos sem overlap de tokens ANTES de o vetor
decidir — o recall atual é dominado por FTS5 lexical + gate, não pelo embedding.
Mesmo relaxando o gate em runtime (monkeypatch no harness, sem tocar site-packages),
o ganho PT do e5-large é só +3.1pp, e o EN regride -10.6pp.

**Decisão:** **e5-large REJEITADO para migração.** Manter `bge-small-en-v1.5`. Nenhuma
mudança em produção. mpnet-base e jina-v3 nem foram testados (o melhor da família já
reprovou o critério). Stella/bge-m3 continuam fora do fastembed (verificado).

**Lições:** (a) melhorar recall exige atacar o gate lexical upstream (knob
`MNEMOSYNE_LEXICAL_GATE_MIN`) e/ou reranker/granularidade de ingest — não a troca de
embedding; (b) drift de judge persistente (47.4%→42.1%→47.4% no mesmo subset) reforça a
regra de comparar só na mesma sessão; (c) a régua PT nova fica no repo como asset
contínuo.

**Status:** fechada — candidato rejeitado; plano P5 arquivado com reservas documentadas.

---


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
