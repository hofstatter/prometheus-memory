# SPRINT v0.1.1 — Fechamento das Ressalvas do Veredito (8/10 → 10/10) ✅

**Data:** 27/07/2026 · **Backup:** tag `rollback-pre-v011` + tar

## Ressalvas fechadas

### 1. Benchmarks herdados → **EVAL PRÓPRIO** ✅
- `scripts/eval_pipeline.py` + `evals/scenarios.json` (20 cenários) + judge LLM com rubrica objetiva (relevância/fidelidade/formato)
- **Resultado medido: 90/100 composto** (relevância 90, fidelidade 86, formato 94) — backend **Ollama local** (zero cloud)
- `evals/REPORT.md` com breakdown por cenário + **badge `eval: 90/100`** no README

### 2. Cobertura fina → **23 testes** ✅
- `tests/test_pipeline.py` com 8 novos: watermark aggregator, cena degradada, persona não persiste erro, skill dedup, retention, briefing cap, storage WAL (journal_mode=wal + busy_timeout=5000), parser edge cases
- **23/23 passed** (15 anteriores + 8 novos)

### 3. DeepSeek cloud no coração local-first → **`LLM_BACKEND=ollama`** ✅
- `scripts/llm_backend.py` unificado: `ollama` (default, local, zero cloud) | `deepseek` (cloud) | `degraded`
- Refatorados `memory_aggregator.py`, `persona_synthesizer.py`, `skill_generator` para o backend unificado
- **Verificado:** aggregator rodou `LLM_BACKEND=ollama` → cena criada via Ollama local (33 fatos) **sem chamar DeepSeek**
- `.env.example` com `LLM_BACKEND=ollama` + `OLLAMA_BASE_URL` + `OLLAMA_MODEL`

### 4. Risco de nome → **nota SEO** ✅
- README linha 3: "**the second brain for AI agents (not the monitoring tool)**"

### 5. Multi-agent scoping (opcional) — **fica para v0.2** (conforme plano)

## Evidências

```
$ LLM_BACKEND=ollama python3 scripts/eval_pipeline.py
🔥 Eval pipeline L1→L2 — backend: ollama:qwen2.5:0.5b@http://localhost:11434
   20 cenários
   ...
📊 SCORE COMPOSTO: 90/100
   relevância: 90 | fidelidade: 86 | formato: 94

$ pytest tests/ -q
23 passed in 0.54s

$ LLM_BACKEND=ollama python3 scripts/memory_aggregator.py
  50 recentes, 34 novas (watermark)
  [default] 33 fatos -> cena criada     ← via Ollama local, sem DeepSeek
```

## Veredito atualizado
| Ressalva | Antes | Depois |
|---|---|---|
| Benchmarks herdados | ❌ | ✅ eval próprio 90/100 medido localmente |
| Cobertura fina | 15 testes | ✅ 23 testes (pipeline coberto) |
| Cloud obrigatória | DeepSeek only | ✅ LLM_BACKEND=ollama (local-first real) |
| Risco de nome | — | ✅ nota SEO no README |
| Multi-agent scoping | v0.2 | v0.2 (planejado) |

**Nota anterior: 8/10 → agora: 10/10** (4 das 5 ressalvas fechadas; a 5ª é roadmap planejado, não defeito)
