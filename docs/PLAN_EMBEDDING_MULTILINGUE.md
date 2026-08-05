# PLAN_EMBEDDING_MULTILINGUE.md — P5: Embedding multilíngue e5-large (troca do bge-small-en)

- **Repo:** prometheus-memory · **Classificação:** MEDIUM (migração de dados vetoriais — superfície sensível)
- **Data:** 04/08/2026 · **Status:** FECHADO — e5-large rejeitado no spike (ver DECISIONS.md 04/08 P5) · **Aprovado por:** Herbert (candidato escolhido: e5-large)

---

## 1. Contexto e objetivo

O Prometheus Memory usa `BAAI/bge-small-en-v1.5` (384d, **somente inglês**) como embedding
default do mnemosyne. O uso real do ecossistema é **português**, e o projeto é público no
GitHub (usuários internacionais = 100+ idiomas). Objetivo: trocar para um modelo **multilíngue
local** (fastembed/ONNX, sem API, sem engine nova, dados 100% na máquina).

### Verificação real no ambiente (04/08)

- fastembed **0.8.0**, 30 modelos no catálogo. **bge-m3 NÃO está** no catálogo (apesar de
  constar no mapa de dimensões do upstream). **Stella 1.5B não está** (análise da sessão 38).
- Candidatos multilíngues reais: `paraphrase-multilingual-mpnet-base-v2` (768d, ~278M),
  `intfloat/multilingual-e5-large` (1024d, ~560M), `jinaai/jina-embeddings-v3` (1024d, ~570M).
- **Decisão do Herbert: `intfloat/multilingual-e5-large`** (~560M) — qualidade MTEB + o
  upstream mnemosyne já tem compatibilidade (supressão de warning p/ e5 em `core/embeddings.py`).
- mpnet-base e jina-v3 ficam como **reserva documentada** — só entram se o e5-large falhar.

## 2. Decisões técnicas

| # | Decisão | Porquê |
|---|---|---|
| D1 | Não trocar engine; usar fastembed local com `MNEMOSYNE_EMBEDDING_MODEL=intfloat/multilingual-e5-large` | Zero edit em site-packages (decisão 04/08); embeddings continuam locais |
| D2 | Spike ANTES de migrar (Fase B), gate humano na Fase C | Histórico: bge-large "parecia melhor" e era -15.8pp; só migra com prova + SIM |
| D3 | Régua PT nova (`scripts/eval_pt_recall.py`) — não existe hoje | Sem régua PT não há como medir o benefício real (produção é PT) |
| D4 | Critério de corte duplo: PT hit@5 **≥ +10pp** E EN **não regride > 2pp** E latência ≤ ~2s/busca no i7 | PT é o uso real; GitHub público é EN; latência inaceitável desqualifica |
| D5 | Medir baseline e candidato **na mesma sessão** | Lição P4: drift de judge 47.4%→42.1% entre sessões invalida comparação |
| D6 | Migração só após vitória + SIM explícito | Trocar modelo sem re-embed = recall lixo; guarda dim do mnemosyne bloqueia, mas ordem importa |

## 3. Arquitetura-alvo (após migração)

```
env: MNEMOSYNE_EMBEDDING_MODEL=intfloat/multilingual-e5-large
     MNEMOSYNE_EMBEDDING_DIM=1024   (mapa upstream já conhece; override por segurança)
Embeddings: fastembed local (ONNX, CPU) — nenhuma chamada de rede
DB: memory_embeddings re-embeddado, coluna `model` registra intfloat/multilingual-e5-large
vec0 tables: recriadas com dim 1024 (guard beam.py:766-777 respeitada)
```

## 4. Passos e critérios de aceite executáveis

### Fase A — ✅ PUBLICADA (04/08): régua honesta P4 (commit `ca9713c`)
Aceite: `main=origin/main=ca9713c`, 78 passed/1 skip registrados.

### Fase B — Spike (em execução nesta sessão)

- **B1** `scripts/eval_pt_recall.py` (novo) — 20-30 pares pergunta→memória reais do
  ecossistema (FASHN/EVSCAR/Visionário/STATE.md etc.); mede **hit@5** com baseline e e5-large,
  mesma sessão; gera `evals/reports/p5-multilingue-pt.md`.
  - *Aceite:* script roda end-to-end e produz a tabela comparativa.
- **B2** Regressão EN: `evals/longmemeval_runner.py --subset 20` com e5-large, judge real
  (env pinado como no CI). Comparar com baseline real 42.1% (mesma sessão se possível).
  - *Aceite:* relatório com `mode: llm` e accuracy EN.
- **B3** Latência: cronometrar embed + recall no i7-13700H com e5-large (warm model).
  - *Aceite:* registro de ms/busca; corte automático se > ~2s.

### Fase C — Decisão (gate humano — NÃO migra sem SIM do Herbert)

- Se PT ≥ +10pp E EN ≥ -2pp E latência OK → apresentar números → aguardar **SIM**.
- Se não → registrar em `docs/DECISIONS.md` + `evals/reports/`, arquivar, fim (zero mudança em prod).
- **RESULTADO (04/08): NÃO atingiu** — PT +3.1pp (isolado), EN **-10.6pp**, latência 5x.
  e5-large rejeitado; bge-small mantido; sem migração. Detalhes: `evals/reports/p5-e5-large.md`.

### Fase D — Migração (só com SIM)

- **D1** `scripts/reembed_all.py` (novo): backup DB → re-embed de todas as memórias →
  atualiza `memory_embeddings.model` → drop/recreate `vec0` na nova dim → valida counts.
  - *Aceite:* `count(*)` idêntico antes/depois; `mnemosyne_diagnose` sem lacunas; recall PT real OK.
- **D2** Produção (`~/Projetos/web`): serviço parado → re-embed → flip env → restart → health 200.
- **D3** Docs: CHANGELOG + DECISIONS.md + nota multilíngue no README (4 idiomas) → GIT GATE.

## 5. Riscos e mitigações

1. **Latência CPU** — e5-large ~10x o bge-small. Medir no spike (B3); corte se inviável no dia a dia.
2. **Ordem da migração** — serviço parado → re-embed → flip env → start. Inverter = recall quebrado.
3. **Download HF ~2.2GB** (1ª execução; fica em cache fastembed).
4. **Drift de judge** — baseline e candidato na MESMA sessão (D5).
5. **Testes** — suíte (78 passed/1 skip) deve permanecer verde (a maioria usa `MNEMOSYNE_NO_EMBEDDINGS`).

## 6. Follow-up upstream (não bloqueia)

- Propor ao mnemosyne: knob `MNEMOSYNE_LEXICAL_GATE_MIN` + fix FK `memory_embeddings` (já registrado).
- Documentar no README do projeto: suporte multilíngue (100+ idiomas) para usuários internacionais.

## 7. Fora de escopo (não fazer)

- Stella 1.5B (não está no fastembed; exigiria engine nova — decidido não fazer).
- bge-m3 (não está no catálogo).
- Ativar OpenRouter/API de embeddings (dados sairiam da máquina; decidido não fazer).
- Qualquer edit em site-packages do mnemosyne.
