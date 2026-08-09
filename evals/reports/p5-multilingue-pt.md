# P5 — Régua PT: recall hit@5 (mesma sessão, retrieval puro)


- 2026-08-04 21:05 — - model: `BAAI/bge-small-en-v1.5 (default)` · **hit@22 = 12/22 (54.5%)** · latência p50 15ms · máx 17ms
  - acertos: 12/22

- 2026-08-04 21:10 — - model: `BAAI/bge-small-en-v1.5 (default)` · **hit@22 = 12/22 (54.5%)** · latência p50 7ms · máx 8ms
  - acertos: 12/22

- 2026-08-04 21:10 — - model: `intfloat/multilingual-e5-large` · **hit@22 = 12/22 (54.5%)** · latência p50 42ms · máx 48ms
  - acertos: 12/22

- 2026-08-04 21:10 — - model: `BAAI/bge-small-en-v1.5 (default)` · **hit@32 = 14/32 (43.8%)** · latência p50 7ms · máx 9ms
  - acertos: 14/32

- 2026-08-04 21:11 — - model: `intfloat/multilingual-e5-large` · **hit@32 = 14/32 (43.8%)** · latência p50 44ms · máx 49ms
  - acertos: 14/32

- 2026-08-04 21:12 — - model: `BAAI/bge-small-en-v1.5 (default)` · **hit@32 = 14/32 (43.8%)** · latência p50 8ms · máx 13ms
  - acertos: 14/32

- 2026-08-04 21:12 — - model: `intfloat/multilingual-e5-large` · **hit@32 = 15/32 (46.9%)** · latência p50 42ms · máx 47ms
  - acertos: 15/32

- 2026-08-05 04:40 — - model: `BAAI/bge-small-en-v1.5 (default)` · **hit@32 = 14/32 (43.8%)** · latência p50 8ms · máx 20ms
  - acertos: 14/32

- 2026-08-05 15:15 — - model: `BAAI/bge-small-en-v1.5 (default)` · **hit@32 = 14/32 (43.8%)** · latência p50 14ms · máx 29ms
  - acertos: 14/32

- 2026-08-08 21:16 — - model: `BAAI/bge-small-en-v1.5 (default)` · **hit@32 = 14/32 (43.8%)** · latência p50 14ms · máx 26ms
  - acertos: 14/32

- 2026-08-08 21:16 — - model: `BAAI/bge-small-en-v1.5 (default)` · **hit@32 = 14/32 (43.8%)** · latência p50 15ms · máx 36ms
  - acertos: 14/32

- 2026-08-08 21:17 — - model: `BAAI/bge-small-en-v1.5 (default)` · **hit@32 = 14/32 (43.8%)** · latência p50 0ms · máx 1ms
  - acertos: 14/32

- 2026-08-08 21:17 — - model: `BAAI/bge-small-en-v1.5 (default)` · **hit@32 = 23/32 (71.9%)** · latência p50 0ms · máx 2ms
  - acertos: 23/32

- 2026-08-08 21:17 — - model: `BAAI/bge-small-en-v1.5 (default)` · **hit@32 = 21/32 (65.6%)** · latência p50 0ms · máx 1ms
  - acertos: 21/32

---

## 📊 COMPARAÇÃO — knob MNEMOSYNE_LEXICAL_GATE_MIN (08/08/2026, mnemosyne 3.16.0 @ c4344f2d, venv)

| Modo | hit@32 | Δ vs default |
|---|---|---|
| default (histórico 0.3/0.5/0.15) | 14/32 (43.8%) | — |
| `MNEMOSYNE_LEXICAL_GATE_MIN=0.15` | 21/32 (65.6%) | +21.9pp |
| `MNEMOSYNE_LEXICAL_GATE_MIN=0.0` (recall-first) | **23/32 (71.9%)** | **+28.1pp** |

**Conclusão (D11):** valor **0.0** escolhido — melhor acurácia, sem queda perceptível de precisão nos 32 casos.
