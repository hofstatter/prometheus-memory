# Report LongMemEval (subset EN oficial)

> ⚠️ **Artefato histórico (gerado ANTES do fix da régua — P4):** o cabeçalho dizia
> "LLM judge", mas com `LLM_BACKEND` default ollama (desligado) o run rodou o **proxy
> de overlap**. O baseline REAL com judge DeepSeek é **42.1%** (ver `p4-ruler-e-experimentos.md`).

- Data: 04/08/2026 · instâncias: 19 · mode: LLM judge (proxy de fato) · query_expansion: off
- **QA accuracy total: 36.8% (proxy)**

| Tipo | n | Accuracy |
|---|---|---|
| temporal-reasoning | 5 | 60.0% |
| knowledge-update | 3 | 66.7% |
| multi-session | 5 | 20.0% |
| single-session-user | 3 | 33.3% |
| single-session-preference | 1 | 0.0% |
| single-session-assistant | 2 | 0.0% |
