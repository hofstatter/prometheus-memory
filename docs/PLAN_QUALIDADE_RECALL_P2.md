# PLAN — Qualidade do Recall, Parte 2: NER v1.2 (Aliases) + M5 (LongMemEval no CI)

> **Data:** 04/08/2026
> **Autor:** Arquiteto (sessão 37) — aprovado por Herbert em diálogo
> **Classificação:** 2× SMALL, execução sequencial (P1 → P2, cada uma com ciclo Pedreiro→Inspetor→push próprio)
> **Status:** Plano aprovado — execução na sessão 37 (Pedreiro)
> **Dependências:** v1.1 publicado (`d59a316`) · DeepSeek key ativa · ⚠️ GH Secret `DEEPSEEK_API_KEY` (ação do Herbert em Settings → Secrets, necessária antes do gate no CI)
> **Backup pré-implementação:** `~/backups/prometheus-memory/qualidade-recall-p2/` (obrigatório: `web/prometheus_db.py`, `web/entity_store.py`, `tests/test_mem0_patterns.py`)

---

## PARTE 1 — NER v1.2: Aliases/Canonização (executar primeiro)

### Contexto

Produção hoje: 7 entidades, 11 links. **4 são lixo legado do regex v1** (`Mini`, `Model`,
`Vision Language`, `Visionario` sem acento). O v1.1 só cura no próximo mention — nunca
remove. Fragmentos futuros ("MiniMax M3" vs "MiniMax") continuariam criando entidades
irmãs, fragmentando `memories_for(name)`.

### Decisões

| # | Decisão | Porquê |
|---|---|---|
| D1 | `canonical_id TEXT` na própria `prometheus_entities` (ALTER ADD COLUMN com guard `PRAGMA table_info` — padrão `_fts_ready` da Fase 3) | 1 coluna resolve; alias = linha apontando pro canônico |
| D2 | Resolução **determinística** em `resolve_canonical(con, name, type_)`: normalize (lowercase + NFKD strip acentos + colapsa pontuação) → match exato → containment (prefixo/sufixo) **dentro do mesmo type** | Barato, testável, zero custo LLM; anti over-merge por type |
| D3 | Resolução no write (`extract_and_link`) antes do lookup | Impede fragmentação nova na fonte |
| D4 | Merge: canônico = maior `mention_count` (empate → nome mais longo); soma counts; re-link `INSERT OR IGNORE`; alias marcado (não deletado — rastreável) | Histórico preservado e reversível |
| D5 | Migração one-shot `scripts/merge_entities.py --dry-run/--apply` + `--prune` para genéricos sem canônico | Dry-run obrigatório; Herbert aprova diff antes do apply; backup DB antes |
| D6 | Produção: sync + restart + backup do DB + dry-run exibido + apply só com OK | Superfície de dados — mesmo cuidado de migração |

### Arquivos

| Arquivo | Ação |
|---|---|
| `web/prometheus_db.py` | `init_schema()` + guard de migração `canonical_id` (PRAGMA → ALTER TABLE ADD COLUMN) |
| `web/entity_store.py` | `normalize_name()`, `resolve_canonical()`, integração no `extract_and_link`, `merge_into()` |
| `scripts/merge_entities.py` | **novo** — dry-run/apply/prune |
| `tests/test_mem0_patterns.py` | +4 testes (C16 containment resolve · C17 acentos · C18 types separados não fundem · C19 merge soma count + re-link sem dup) |
| `CHANGELOG.md` | entrada v1.2 |

### Aceite Parte 1

```bash
pytest tests/  # 74 passed (70 + C16-C19), 0 regressão
python3 scripts/merge_entities.py --dry-run   # relatório exibido a Herbert
# produção (após OK): backup DB → apply → restart → /api/pm/entities
# esperado: ~4 canônicas (FASHN, EVSCAR, Prometheus Memory, Visionário);
#   Mini/Model/Vision Language fundidas ou pruned; menções somadas; links íntegros
```

---

## PARTE 2 — M5: LongMemEval no CI (executar depois)

### Contexto

LongMemEval (ICLR 2025, `xiaowu0162/LongMemEval`, dataset `longmemeval-cleaned` na
HuggingFace): 500 perguntas, 5 habilidades (extração, multi-sessão, atualização de
conhecimento, raciocínio temporal, abstenção). O judge oficial usa GPT-4o — aqui o judge
é **DeepSeek** via `scripts/llm_backend.call_llm` (restrição: sem modelos ocidentais).
Protege o recall híbrido recém-entregue (v1.1): qualquer mudança que piore o recall vira
detectável no CI.

### Decisões

| # | Decisão | Porquê |
|---|---|---|
| D7 | **Dataset: subset EN original** (estrato por tipo, seed 42) — ⚠️ **mudança pós-aprovação**: o plano dizia PT-BR 100, mas as sessões do dataset oficial são **EN**; perguntas PT contra memórias EN não recall (FTS/gate lexical por idioma). PT-BR exige traduzir ~50k turnos de sessões (fora do v1; script de tradução fica como ferramenta futura) | Mede o recall real; o objetivo (proteger o recall) independe do idioma |
| D8 | Ingest com **`infer=False`** (raw, sem LLM) + prefixo de data da sessão | Testa a camada que M5 protege (recall híbrido + dedup + threshold); sem 4000+ chamadas LLM; temporal-reasoning precisa das datas |
| D9 | Runner mede **QA accuracy** (recall top-5 → DeepSeek responde → DeepSeek judge, rubrica estrita, temperature 0) por tipo + total. QA com **prompt extrativo** (não abstenção-first — DeepSeek abstém demais com "never invent") + **`_render_content`** decodificando "[Fact metric] snake_case" do suplemento MEMORIA | Métrica padrão; descobertas de execução: modelo abstém com framing conservador; memórias estruturadas precisam de normalização (como os "reading methods" do oficial) |
| D10 | **Report-only primeiro**: baseline medido **47.4%** (19 instâncias: temporal 80%, knowledge-update 67%, multi-session 20%) → gate depois com threshold real (mudança 1-linha) | Benchmark é duro; gate cego geraria falso alarme |
| D11 | Trigger CI: push filtrado por path (`web/memory.py`, `entity_store.py`, `dedup.py`, `extractor.py`, `evals/**`) + `workflow_dispatch` + cron semanal | R7: eval lento/custoso não roda em todo push |
| D12 | Runner com lane isolada `eval:lme-<question_id>` + `SEMANTIC_DEDUP=off` + DB temporário; **`_prepare_eval_db`** contorna bug upstream (memória_embeddings com FK→memories epísodicas quebra o insert de embedding de working em DB fresco — rebuild sem FK) | Isolamento total; dedup não interfere; DB fresco utilizável |

### Descobertas de execução (registradas p/ upstream)

1. **Bug Mnemosyne (upstream)**: `mnemosyne/core/memory.py` cria `memory_embeddings` com `FOREIGN KEY (memory_id) REFERENCES memories(id)` (episódica), mas o BEAM grava embeddings de **working_memory** na mesma tabela → em DB fresco o insert falha (`FOREIGN KEY constraint failed`) e o recall vetorial morre silenciosamente. Produção sobrevive por ter sido criada antes da FK. Workaround no runner; **fix upstream deve ser proposto**.
2. **Gate lexical do recall**: resultados só-vetoriais (sem overlap de tokens com a query) são descartados pelo gate de relevância lexical → morfologia PT ("formação" vs "formou") e queries parafraseadas não recall. O baseline 47.4% reflete isso (multi-session 20%). Candidato a melhoria futura (stemmer PT no FTS5 ou relaxar o gate).
3. **Suplemento MEMORIA**: o recall injeta resultados sintéticos "[Fact metric] key: value" (regex). O QA (DeepSeek) abstém frente a chaves snake_case — o harness normaliza (`_render_content`) e usa prompt extrativo.

### Arquivos

| Arquivo | Ação |
|---|---|
| `evals/longmemeval_runner.py` | **novo** — ingest/recall/QA/judge/relatório (`--subset N`, `--local-only`) |
| `evals/longmemeval_ptbr.json` | **adiado** — ferramenta futura (corpus de sessões PT-BR pendente; D7) |
| `scripts/translate_longmemeval_subset.py` | **novo** — one-shot de tradução via DeepSeek (não entra no CI) |
| `.github/workflows/eval.yml` | **novo** — path-filter + dispatch + cron semanal; artifact com `evals/REPORT_LONGMEMEVAL.md` |
| `evals/REPORT_LONGMEMEVAL.md` | gerado (baseline) |
| `CHANGELOG.md` | entrada M5 |

### Fluxo do runner

```
para cada instância (lane eval:lme-<qid>, DB temporário):
  1. INGEST: sessões do haystack → remember_lane raw com prefixo [data] (infer=False, SEMANTIC_DEDUP=off)
  2. RECALL: recall_lane(lane, question, top_k=5)  # embeddings locais, grátis
  3. QA: call_llm responde com memórias recuperadas (temperature 0)
  4. JUDGE: call_llm rubrica binária gold vs hipótese (temperature 0)
  agrega por question_type → QA accuracy total + por tipo → REPORT
```

### Aceite Parte 2

```bash
python3 evals/longmemeval_runner.py --subset 20   # baseline local <10min, QA accuracy + relatório
# CI: push em web/memory.py dispara eval.yml → artifact com REPORT (não quebra build ainda)
# gate: após baseline (3 rodadas), threshold real → workflow vira gate (PR separado)
```

---

## Riscos

| Risco | Mitigação |
|---|---|
| Over-merge destrutivo em produção (P1) | Dry-run + aprovação Herbert + backup DB antes do apply |
| Judge DeepSeek instável (P2) | Rubrica binária oficial + temperature 0 + report-only primeiro |
| Temporal-reasoning sem datas (P2) | Prefixo de data no ingest (padrão das adaptações) |
| Secret no GH Actions (P2) | Herbert adiciona manualmente; nunca commitamos keys |
| Dedup semântico interferir no ingest (P2) | Lane isolada por questão + `SEMANTIC_DEDUP=off` |

## Fora do escopo

- NER: aliases via LLM (regras determinísticas bastam; LLM = v1.3)
- M5: dataset EN, LongMemEval-M (500 sessões), gate ativo no CI (vem depois do baseline)
- Orquestrador Conversacional (adiado por Herbert)

---

## Arquivos afetados (resumo)

| Arquivo | Ação | Backup |
|---|---|---|
| `web/prometheus_db.py` | Alterar (migração canonical_id) | Obrigatório |
| `web/entity_store.py` | Alterar (resolve_canonical + merge) | Obrigatório |
| `web/memory.py` | Inalterado em P1 | — |
| `scripts/merge_entities.py` | **Criar** | — |
| `tests/test_mem0_patterns.py` | Alterar (C16-C19) | Obrigatório |
| `evals/longmemeval_runner.py` | **Criar** | — |
| `evals/longmemeval_ptbr.json` | **adiado** — ferramenta futura (corpus de sessões PT-BR pendente; D7) |
| `scripts/translate_longmemeval_subset.py` | **Criar** | — |
| `.github/workflows/eval.yml` | **Criar** | — |
| `CHANGELOG.md` | Alterar (2 entradas) | — |
