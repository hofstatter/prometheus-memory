# PLAN_SEMANTICA_GRAFO_F1 — Grafo real + analytics na UI :8777

> Estado: **EM EXECUÇÃO** (06/08/2026) · Dono: Pedreiro (build) · Inspetor: revisão na fronteira
> Origem: pedido Herbert — "varredura do semantica-agi/semantica e implementar parte no prometheus-memory para melhorar o Grafo (:8777)"

---

## 1. Contexto — varredura semantica-agi/semantica (concluída)

Repo analisado: `semantica-agi/semantica` (MIT, 176k linhas Python, v0.6.0, 2k★ — "open source Palantir para agentes"). Perfil: ingest → extract → KG → reasoning/provenance/decisions.

### 1.1 Adoção como dependência — **DESCARTADA**
Core deps de `pyproject.toml` puxam `torch`, `transformers`, `spacy`, `faiss-cpu`, `opencv`, `librosa`, `umap-learn`, `gensim`, `rdflib`… → ~3–5GB para usar 5% do pacote. Inválido para um serviço que roda em VPS/local leve.

### 1.2 Módulos alvo — **quase pure-Python** (vendoring/adaptação viável, MIT)

| Módulo semantica | Deps | Gap que fecha no prometheus-memory | Decisão |
|---|---|---|---|
| `kg/centrality_calculator.py` (degree/betweenness/PageRank :642) | stdlib+scipy | UI grafo sem sinal de importância | **F1: VENDOR (PageRank + degree em Python puro)** |
| `kg/community_detector.py` (Louvain/label-prop :664) | stdlib | Sem clusters | F4 (futuro) |
| `kg/link_predictor.py` (Adamic-Adar/Jaccard :336-390) | stdlib | Sem sugestão de arestas | F4 (futuro) |
| `context/decision_models.py` + `causal_analyzer.py` (chain/root-cause :378) | stdlib | `edge_type=caused` existe mas nada cria/reconstrói cadeias | F2 (futuro) |
| `conflicts/conflict_detector.py` (rule-based, temporal :818) | stdlib | Conflitos só via LLM noturno | F3 (futuro) |
| `kg/temporal_model.py` (BiTemporalFact, ~180 linhas) | stdlib | Só valid-time hoje | F3 (futuro) |
| `provenance/manager.py` + `storage.py` (SQLite PROV-O) | stdlib | Provenance parcial | SKIP majoritário (já temos `triples.source`) |
| `explorer/` (workbench FastAPI+React) | FastAPI | UI :8777 é hub-and-spoke fake | **F1: INSPIRAR features (não código)** |

### 1.3 Estado real do grafo no prometheus-memory (levantado 06/08)
- Banco único `~/.hermes/mnemosyne/data/mnemosyne.db` (SQLite). Tabelas reais:
  - `graph_edges(id, source, target, edge_type, weight, timestamp)` — **10 linhas** (gist→fact, tipo `ctx`)
  - `triples(subject, predicate, object, valid_from, valid_until, source, confidence)` — 1 linha
  - `gists(id, text, memory_id)` — 347 · `facts(fact_id, subject, predicate, object)` — 10
  - `canonical_facts` — 3 · `prometheus_entities` — 4
- `/api/graph` (web/app.py:146) **NÃO lê nada disso**: recall CLI "cena fato" (50 itens) + arestas O(n²) memória↔projeto, cap 100 — grafo falso.
- UI `renderGraph()` (index.html:934) desenha só hub-and-spoke; sem edge types, sem labels de aresta, sem entidades, sem analytics.
- **Descoberta:** upstream mnemosyne 3.15.1 **já aplica** `graph_bonus` no recall (beam.py:6250-6261, `min(edge_count*0.02, 0.08)`, knob `MNEMOSYNE_GRAPH_BONUS`). Ou seja, "alimentar o recall com grau" **já existe upstream** — F1 não deve somar boost extra (evitar dupla contagem).

## 2. Decisões de arquitetura (registradas em DECISIONS.md)

1. **D1 — Sem boost extra no recall:** o `graph_bonus` por grau já roda upstream. F1 *expõe* o grau no recall (`graph_degree` no payload) para dar visibilidade, sem alterar scoring.
2. **D2 — Grafo computado por request:** com dados reais pequenos (10 edges/347 gists hoje), PageRank+degree em Python puro é sub-ms. Sem cache complexo; cap `?limit=500`.
3. **D3 — Dois alvos:** repo canônico `~/Projetos/prometheus-memory/web/` + cópia viva `~/Projetos/web/` (WorkingDirectory do systemd user `prometheus-web.service`). Implementa no repo, **sync dos arquivos alterados** para prod, restart.
4. **D4 — Sem tocar no upstream** (`site-packages/mnemosyne`): todas as mudanças ficam na camada Prometheus (padrão já usado no PLAN_QUALIDADE_RECALL_P3).
5. **D5 — Python puro nos analytics** (sem numpy): `pagerank()` ~30 linhas, adaptado do semantica (MIT). Nada de dependência nova.

## 3. Escopo F1 (fatia vertical)

### F1a — `web/graph_service.py` (NOVO, ~150 linhas)
- `fetch_graph(limit=250, include_entities=True) -> dict` — lê SQLite read-only:
  - **nós:** endpoints de `graph_edges` (gist_*/fact_*) com label a partir de `gists.text`/`facts.object`; entidades de `prometheus_entities` quando endpoint de tripla; nós de tripla (subject/object) sem match.
  - **arestas:** linhas de `graph_edges` (edge_type real) + triplas (`predicate` → edge_type).
  - **analytics:** `degree_centrality()` (adjacência não-direcionada) + `pagerank()` (direcionado) por nó; meta com top pagerank, contagens, timestamp.
- `EDGE_TYPE_COLORS` — paleta por tipo (`ctx` ciano, `references` verde, `related_to` roxo, `caused` vermelho, `supersedes` âmbar, `syn` rosa, padrão cinza).
- `degree_by_memory()` — mapa `memory_id → grau` via `gists.memory_id` + parse do prefixo `fact_<memid>_<n>` (para o campo `graph_degree` no recall).
- Licença: adaptado de `semantica/kg/centrality_calculator.py` (MIT) — NOTICE no docstring.

### F1b — `web/app.py` (editar)
- `graph()` reescrito → delega a `graph_service.fetch_graph()`; param `?limit=`/`?entities=`.
- `/api/memory/recall` → enriquece resultados com `graph_degree` (mapa `degree_by_memory`, TTL curto, falha silenciosa).
- `_clean_text` move para graph_service (limpeza no conteúdo dos nós).

### F1c — `web/templates/index.html` (editar renderGraph)
- Busca `/api/graph` (fetch, cache em `graphCache`, botão Atualizar).
- Arestas reais: cor por tipo, `curveOffset`, `endArrow`, label do tipo no hover/ativo.
- Tamanho do nó ∝ degree/pagerank; detalhe mostra conteúdo + grau + pagerank + tipos de aresta + botão editar (memory_id).
- **Legenda** de edge types + badge de analytics (nº arestas/nós reais).
- Mantém: physics toggle, fitView, reheat 25s, deep-link `#graph`.

### F1d — Sync + deploy
- `rsync` dos arquivos alterados → `~/Projetos/web/` (NUNCA .env).
- `systemctl --user restart prometheus-web` → verificação real em :8777.

## 4. Critérios de aceite (todos verificáveis)

| # | Critério | Verificação |
|---|---|---|
| CA1 | `/api/graph` retorna arestas **reais** (`edge_type` de `graph_edges`/`triples` presentes) e **não** mais arestas O(n²) hub-spoke de memória↔projeto | Flask test client + contagem no payload |
| CA2 | Cada nó carrega `data.degree` e `data.pagerank`; `analytics` com top pagerank e contagens | payload |
| CA3 | Resposta `/api/graph` < 1s com dados reais | timing no test client |
| CA4 | UI renderiza arestas com cor/label por tipo + legenda (DOM G6) | Playwright snapshot de `localhost:8777/#graph` |
| CA5 | `/api/memory/recall` segue 200 com campo `graph_degree` quando há grau | test client |
| CA6 | `python3 -m py_compile` limpo nos arquivos alterados + app boots (test client `GET /api/graph` 200) | comando |
| CA7 | Sem regressão: `/api/timeline`, `/api/stats`, `/` 200 | test client |
| CA8 | Sync prod + restart: `:8777` responde e grafo real aparece | playwright + curl |

## 5. Riscos e mitigações

- **Risco:** `graph_edges` quase vazio hoje (10) → grafo parece pobre. **Mitigação:** incluir nós de `gists`/`facts`/triplas e entidades; o grafo real cresce com a consolidação noturna. Registrado como limitação honesta na UI (badge mostra contagens reais).
- **Risco:** sync prod divergir do repo (web/ não é git). **Mitigação:** sync por arquivo dif e conferência de sha256; .env nunca é tocado.
- **Risco:** PageRank em grafos grandes. **Mitigação:** cap 500 nós, iteração max 100, puro python; degrado para sub-50ms.

## 6. Fora do escopo (próximas fatias)

- **F2:** Decision/causal chains (`record_decision` MCP tool + `trace_decision_chain` + edges `caused/influenced` automáticas).
- **F3:** Conflict detection temporal rule-based (overlap de intervalos em `triples`) + `recorded_at` bi-temporal.
- **F4:** Community detection (Louvain) + link prediction na UI + unificação `prometheus_entities` ↔ subjects de `triples`.

## 7. Entregáveis da sessão

- [ ] PLAN (este arquivo) + DECISIONS.md atualizado
- [ ] `web/graph_service.py` criado
- [ ] `web/app.py` editado (graph real + graph_degree no recall)
- [ ] `web/templates/index.html` editado (grafo real G6)
- [ ] Backup pré-edição: `~/backups/herbert/semantica-graph-f1/20260806-031327/`
- [ ] Aceite CA1–CA8 verdes
- [ ] Sync prod + restart + screenshot Playwright
- [ ] STATE.md + CONTEXT.md + Mnemosyne
