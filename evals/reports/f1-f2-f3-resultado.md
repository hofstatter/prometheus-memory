# F1+F2+F3 — Resultado consolidado (subset-20, seed 42, mesma sessão)

- Data: 04/08/2026 · 19 instâncias · judge DeepSeek temp 0 · **Δ = 0.0pp em TODAS as fases**
- **Total: 36.8% em off / F1 / F2 / F3 — rótulos byte-idênticos nos 4 runs**

| Config | Total | multi-session | temporal |
|---|---|---|---|
| off (baseline) | 36.8% | 20% | 60% |
| F1 query-expansion | 36.8% | 20% | 60% |
| F2 key-expansion | 36.8% | 20% | 60% |
| F3 --con (CoN) | 36.8% | 20% | 60% |
| **local-only (proxy overlap)** | **36.8%** | 20% | 60% |

## Diagnóstico (o que os dados dizem)

1. **local-only == LLM-judge (36.8% ambas)** → o erro NÃO vem do leitor nem do juiz:
   o vocabulário da resposta de referência **não está no top-5 recuperado** em 63%
   das questões. O gargalo é **retrieval**, não leitura.
2. **F1 (query) e F2 (índice) não cobrem a sinonímia completa** das 500 questões EN
   (paráfrase total: pergunta e evidência sem tokens compartilhados). O mini-mapa
   (F1) e as keyphrases de sessão (F2) são genéricos demais para a query EN.
3. **F3 (CoN) não ajuda o que não foi recuperado** — leitura ótima com recall ruim = 0.
4. **Judge/reader instável entre sessões**: mesmo subset deu 47.4% (manhã) e 36.8%
   (tarde) — baseline móvel; pequenos deltas são inmedíveis com 19 instâncias.
5. **subset-100 é inviável**: >40min local; CI cancelava nos 60min (`eval.yml` agora
   usa `--subset 30` — cabe no timeout e dobra o tamanho da régua).

## Conclusão honesta

Nenhuma das 3 fases atingiu o critério de aceite do plano (delta > 47.4% /
multi-session > 20%). **Não são "melhorias" — são capabilities env-gated**, testadas
(86✓) e neutras no benchmark EN:

- F1: morfologia PT provada (smoke test + T4) — útil p/ produção PT.
- F2: infraestrutura de key expansion pronta (KEY_EXPANSION=llm) p/ quando houver
  corpus PT medido.
- F3: reader CoN pronto (--con) — reutilizável quando o retrieval melhorar.
- Fix real aplicado: `eval.yml` `--subset 30` (CI baseline agora roda de fato).

**Próximo passo real (recomendação):** (a) decidir se o alvo é EN (benchmark) ou PT
(uso real) — se PT, traduzir corpus (ferramenta já existe) e medir o que importa;
(b) se EN, atacar retrieval com expansão de query por LLM (opção B da F1) e/ou
granularidade turn/session com embeddings melhores; (c) pinar o modelo reader/judge
p/ matar o baseline móvel.
