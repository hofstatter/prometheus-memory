# PLAN_SEMANTICA_GRAFO_F1_1 — Visionário glm-4.5v + Visual F1.1 + Backfill de arestas reais

> Estado: **EM EXECUÇÃO** (06/08/2026, sessão 43) · Dono: Pedreiro (build) · Inspetor: revisão na Fase 2 (migração = escrita no DB)
> Base: PLAN_SEMANTICA_GRAFO_F1.md (F1 entregue, CA1–CA8 verde, Inspetor APROVOU).
> Gatilho: Herbert aprovou glm-4.5v como Visionário + melhorias visuais (F1.1) + enriquecer/migrar dados existentes para o grafo real.

---

## 1. Contexto

### 1.1 Achado crítico (F1)
O "GLM-4.7V" **não existe** no Z.AI Coding Plan. Testes diretos na API (credencial `zai-coding-plan`):
- `glm-4.7` → existe, mas **rejeita `image_url`** (text-only no endpoint `/api/coding/paas/v4/chat/completions`)
- `glm-4.7v` → HTTP 400 `Unknown Model`
- **`glm-4.5v` → FUNCIONA com visão** (analisou os 2 screenshots do grafo, validado ao vivo)
- `glm-4.6v` → timeout (inconclusivo; pode existir)

→ **Visionário = `zai-coding-plan/glm-4.5v`.** Se o opencode não resolver o ID (não está em `opencode models`), declarar modelo custom no `opencode.jsonc` (provider `zai-coding-plan`, openai-compatible, base já configurada).

### 1.2 Estado real do grafo (medido)
- `graph_edges`: 10 (todas `ctx`, gist→fact, 17/07–03/08) · `triples`: 1 · `gists`: 354 (todas com `memory_id`) · `facts`: 10
- `annotations`: **1.446** (`mentions` 784 em **106 memórias** · `has_source` 331 · `occurred_on` 331)
- `prometheus_memory_entities`: **13** links memória↔entidade (EVSCAR 4, FASHN 4, Prometheus Memory 4, Visionario 1)
- `memories`: 329 · Visual novo do grafo: 20 nós / 11 arestas — **legítimo mas esparso** (modelo de visão: legibilidade 3/10, "parece erro de render, não escassez de dados")

### 1.3 Diagnóstico visual (glm-4.5v, 06/08)
- Antigo: estrela hub-and-spoke artificial (7/10 legibilidade, "enganosa")
- Novo: esparso real, nós pequenos, dispersão excessiva, arestas quase invisíveis (3/10)
- Sugestões: layout circular + nós 2-3x maiores + labels permanentes + arestas grossas (3-4px) + nós isolados semi-transparentes

## 2. Decisões

- **D1:** `glm-4.5v` é o modelo de visão (validado na API). `glm-4.7`/`glm-4.7v` descartados (text-only/inexistente).
- **D2:** F1.1 visual por **switch de layout por tamanho**: ≤40 nós → `circular`; >40 → `d3-force` (atual).
- **D3:** Backfill **escreve em `graph_edges`** (tabela upstream, endpoints freeform) — dedup idempotente, endpoints validados, dry-run obrigatório, backup do DB antes do apply.
- **D4:** M2 (mentions) usa **confidence ≥ 0.8** + normalização anti-ruído (lowercase, ≥4 chars, sem puro dígito, stopwords) — precisão > volume.
- **D5:** Entidades viram nós pelo **nome** (casa com subjects das `triples`: "Prometheus Memory"); se o `doctor` upstream reclamar de dangling, prefixar `entity:`.

## 3. Escopo

### Fase 0 — Visionário glm-4.5v (MICRO)
- `~/.config/opencode/agent/visionario.md`: `model: zai-coding-plan/glm-4.5v`
- `opencode.jsonc`: declarar modelo custom `glm-4.5v` no provider `zai-coding-plan` (se necessário — validar antes)
- Cascata: AGENTS.md, GUARDRAILS (v5.3), FLUXO_BIMODELO (v6.3), CONTEXT.md, STATE.md (corrigir `glm-4.7` → `glm-4.5v`)
- **Aceite:** após restart, subagent `visionario` analisa imagem real (teste com `/home/herbert/graph-f1-real.png`)

### Fase 1 — F1.1 Visual (SMALL, só `templates/index.html`)
1. **Switch de layout:** `nodes.length <= 40` → G6 `circular` (ordering `degree`, radius `min(cw,ch)/2 - 60`); senão `d3-force` atual
2. **Nós:** conectados 24-30px (memória) / 32px (entidade), escalado por degree; **isolados 12px + fillOpacity 0.4**
3. **Labels permanentes** (truncadas ~16 chars) no modo circular
4. **Arestas:** lineWidth 2.5–4.5 (por peso), opacity 0.85, cores por tipo, setas; halo só em nós conectados
5. Badge/legenda/controles/Atualizar mantidos
- **Aceite:** Playwright snapshot sem erros JS · glm-4.5v nota ≥ 6/10 · sync prod + restart + live 200

### Fase 2 — Backfill de arestas reais (MEDIUM — escrita no DB)
Novo `scripts/backfill_graph_edges.py` (camada Prometheus; `--dry-run` default, `--apply` escreve; idempotente):

| Migração | Fonte | Edge | Vol. estimado |
|---|---|---|---|
| M1 | `gists.memory_id` (354) | `(memory_id, gist_id, 'ctx', 1.0)` | ~354 |
| M2 | `annotations` `mentions` (conf≥0.8, normalizadas) | pares de memórias que compartilham mention → `references` (w=0.6+0.1×grupo, cap 1.0; completo ≤8, senão estrela) | centenas |
| M3 | `prometheus_memory_entities` (13) | `(memory_id, entity_name, 'mentions', 0.9)` | 13 |

**Segurança:** backup `mnemosyne.db` pré-apply · dry-run com relatório antes · endpoints validados · `mnemosyne doctor` pós-apply · dedup idempotente.
- **Aceite:** dry-run mostra contagens ≥ 1 por tipo · apply insere sem duplicar · `/api/graph` live com nós+arestas maiores · doctor sem falhas novas · Inspetor APROVA

## 4. Critérios de aceite consolidados

| # | Critério | Verificação |
|---|---|---|
| CA1 | visionario.md = `zai-coding-plan/glm-4.5v` + cascata consistente | grep |
| CA2 | UI modo circular ≤40 nós: labels permanentes + nós maiores + isolados 0.4 | Playwright snapshot + glm-4.5v ≥ 6/10 |
| CA3 | Backfill dry-run reporta M1/M2/M3 | execução |
| CA4 | Apply idempotente (2ª execução insere 0) | execução |
| CA5 | `/api/graph` live: nós e arestas reais > antes (≥ 11) | curl + payload |
| CA6 | `mnemosyne doctor` sem novas falhas | comando |
| CA7 | Sem regressão: rotas `/`, `/api/timeline`, `/api/stats` 200 | test client |
| CA8 | Inspetor APROVOU Fase 2 (migração) | task inspector |
| CA9 | Docs: PLAN + STATE + CONTEXT + Mnemosyne atualizados | — |

## 5. Riscos

- **R1:** opencode não resolve `glm-4.5v` → declarar no `opencode.jsonc` (provider models) — validado antes do restart
- **R2:** mentions ruidosas → filtros + conf≥0.8 (D4)
- **R3:** doctor upstream flagga entidades (nome≠id) → prefixo `entity:` (D5)
- **R4:** grafo denso demais → cap `?limit=500` + F1.1 melhora legibilidade
- **R5:** consolidação upstream duplica → dedup idempotente também pós-consolidação

## 6. Fora do escopo
F2 (decision/causal chains), F3 (conflicts temporal + bi-temporal), F4 (communities/link-pred + unificação entidades) — roadmap semantica.

## 7. Entregáveis
- [ ] PLAN_SEMANTICA_GRAFO_F1_1.md (este)
- [ ] visionario.md + opencode.jsonc + cascata → glm-4.5v
- [ ] index.html F1.1 (circular + nós + labels + arestas)
- [ ] scripts/backfill_graph_edges.py + dry-run + backup DB + apply + doctor
- [ ] Sync prod + restart + validação visual (Playwright + glm-4.5v)
- [ ] Inspetor APROVADO
- [ ] STATE.md + CONTEXT.md + Mnemosyne + workflow/recovery
