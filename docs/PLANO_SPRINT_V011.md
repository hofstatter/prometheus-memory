# PLANO DETALHADO — Sprint v0.1.1 "Fechamento das Ressalvas"
### Prometheus Memory — resposta ao veredito externo (8/10 → 10/10)

**Status:** PLANEJADO — NÃO IMPLEMENTADO · **Criado:** 27/07/2026 · **Estimativa:** ~3h
**Base:** veredito externo do repo (5 ressalvas confirmadas como precisas)

## As 5 ressalvas e o plano de fechamento

| # | Ressalva | Fechamento | Esforço |
|---|---|---|---|
| 1 | Benchmarks herdados, não próprios | **Eval próprio do pipeline L2/L3** | ~1h |
| 2 | Cobertura fina (sem testes do pipeline) | **+8 testes do pipeline** | ~45min |
| 3 | L2/L3 exige DeepSeek (cloud) no coração local-first | **`LLM_BACKEND=ollama`** local | ~45min |
| 4 | Risco de nome (colide com Prometheus monitoring) | Nota SEO + PyPI nome único na v0.2 | 5min |
| 5 | Single-user sem isolamento por agente | **(opcional) multi-agent scoping antecipado** | ~1h |

---

## 1 — Eval próprio do pipeline L2/L3 (~1h) ⭐ prioridade

**Ressalva:** `COMPARISON.md` herda benchmarks do Mnemosyne, mas a qualidade da consolidação L1→L2 (cenas) e L2→L3 (persona, skills) — o **claim central do produto** — nunca foi medida formalmente.

### Implementação
- **`scripts/eval_pipeline.py`**:
  - **Suite de 20 cenários** (`evals/scenarios.json`): cada um com `facts: []` (fatos L1 simulados) + `expected_scene_topic` (tema esperado da cena consolidada)
  - Roda o `memory_aggregator` em modo eval (LLM ou degradado) → produz cena
  - **Judge LLM** (rubrica objetiva 0-100): relevância da cena aos fatos, fidelidade (não-alucinação: tudo na cena vem dos fatos?), completude (cobriu os pontos-chave?), formato
  - Também mede: persona coerente com cenas (L2→L3), skill generation só dispara com 3+ padrões (anti-falso-positivo)
  - **Score composto 0-100** + breakdown por critério
- **Badge no README**: `eval: 87/100` (gerado via CI ou manual, atualizado a cada release)
- **`evals/REPORT.md`**: relatório detalhado por cenário (o que passou/falhou e por quê)
- Modo `--degraded`: mede também o fallback sem LLM (prova que o pipeline funciona sem cloud)

### Verificação
`python3 scripts/eval_pipeline.py` → score impresso + `evals/REPORT.md` com 20 cenários avaliados + badge no README atualizado.

---

## 2 — +8 testes do pipeline (~45min)

**Ressalva:** os 10 testes atuais cobrem auth/segurança/i18n/savings — mas **zero testes do pipeline** (aggregator, persona_synthesizer, skill_generator, retention).

### Testes (`tests/test_pipeline.py`)
1. **Aggregator watermark**: state persiste IDs processados; segunda execução não reprocessa
2. **Cena degradada** (sem DEEPSEEK_KEY): fallback concatena fatos sem chamar LLM
3. **Persona não persiste erro**: LLM falha → persona.md NÃO é escrito (proteção L3)
4. **Skill dedup**: skill_generator não recria skill existente; só dispara com 3+ ocorrências do padrão
5. **Retention cleanup**: `retention.py` remove refs >90d e arquiva sessões >180d
6. **Briefing cap**: `/api/context/briefing` respeita max_chars (500 tokens)
7. **Storage WAL**: `storage.py` SQLiteStore abre com journal_mode=WAL + busy_timeout
8. **parse_mnemosyne_output edge cases**: output vazio, sem Score, IDs malformados

### Verificação
`pytest tests/ -q` → 18 passed (10 atuais + 8 novos), CI verde.

---

## 3 — `LLM_BACKEND=ollama` para síntese L2/L3 (~45min)

**Ressalva:** o pipeline local-first **exige DeepSeek (cloud)** para cenas/persona/skills — contradiz a tese de independência de cloud (e a máquina tem Ollama + Qwythos local de graça).

### Implementação
- **`scripts/llm_backend.py`** (compartilhado por aggregator, persona_synthesizer, skill_generator):
  ```python
  LLM_BACKEND = os.getenv("LLM_BACKEND", "ollama")  # ollama | deepseek | degraded
  # ollama → POST {OLLAMA_BASE_URL}/api/generate (default http://localhost:11434)
  # deepseek → POST api.deepseek.com/chat/completions (comportamento atual)
  # degraded → concatenação sem LLM (fallback atual)
  ```
- Refatorar `synthesize_scene_with_llm`, `synthesize_persona`, `generate_skills` para usar o backend unificado
- `.env.example`: `LLM_BACKEND=ollama` + `OLLAMA_MODEL=qwen2.5:0.5b` (ou Qwythos)
- Documentar no README: "100% local — zero cloud dependency" (com Ollama)

### Verificação
`LLM_BACKEND=ollama python3 scripts/memory_aggregator.py` → cena gerada via Ollama local (log mostra modelo local, sem chamar DeepSeek).

---

## 4 — Nota de nome / SEO (5min)

**Ressalva:** "prometheus memory" colide com Prometheus monitoring (prometheus.io) em buscas.

### Implementação
- README ganha linha de posicionamento SEO no topo: **"Prometheus Memory — the second brain for AI agents (not the monitoring tool)"** + tagline consistente "second brain for AI agents" em todos os idiomas
- Topics do GitHub já cobrem (`second-brain`, `agent-memory`, `llm-memory`) — reforçar `ai-agents-memory`
- **v0.2**: publicar pacote PyPI com nome único (`prometheus-agent-memory` ou `mnemosyne-fire`) — fica registrado no roadmap

### Verificação
README linha 3 tem a nota SEO.

---

## 5 — (OPCIONAL) Multi-agent scoping antecipado (~1h)

**Ressalva:** single-user sem isolamento por agente — times multi-agente (o bytex-agentos!) precisam de escopo.

### Implementação (se aprovado incluir)
- `agent_id` + `session_id` em remember/recall (Mnemosyne já suporta via `banks`)
- Bank por agente: `Mnemosyne(bank=f"agent-{id}")` → isolamento de memória por agente
- `GET /api/memory/recall?agent_id=X` filtra por bank
- **Se não incluir:** fica no ROADMAP v0.2 como já está (decisão do usuário)

---

## Entregáveis

| Item | Detalhe |
|---|---|
| `scripts/eval_pipeline.py` + `evals/scenarios.json` + `evals/REPORT.md` | eval próprio L2/L3 |
| Badge `eval: N/100` no README | claim medido |
| `tests/test_pipeline.py` (8 testes) | 18 passed na CI |
| `scripts/llm_backend.py` + refator dos 3 scripts | LLM_BACKEND configurável |
| `.env.example` com `LLM_BACKEND=ollama` | default local |
| Nota SEO no README (4 idiomas) | posicionamento de nome |
| `docs/reports/SPRINT_V011.md` | relatório com evidências |
| ROADMAP v0.2 atualizado (PyPI nome único) | — |

## Cronograma

| Etapa | Tempo |
|---|---|
| 1 Eval próprio | ~1h |
| 2 +8 testes pipeline | ~45min |
| 3 LLM_BACKEND=ollama | ~45min |
| 4 Nota SEO | 5min |
| 5 (opcional) multi-agent scoping | ~1h |
| Verificação + docs + push | ~20min |
| **Total (sem opcional)** | **~3h** |
| **Total (com opcional)** | **~4h** |

## Verificação final (definition of done)

- [ ] `scripts/eval_pipeline.py` → score 0-100 + `evals/REPORT.md` com 20 cenários
- [ ] Badge `eval: N/100` no README
- [ ] `pytest tests/ -q` → 18 passed
- [ ] `LLM_BACKEND=ollama` roda síntese sem chamar DeepSeek
- [ ] README com nota SEO "not the monitoring tool"
- [ ] CI verde + push GitHub + tag v0.1.1
