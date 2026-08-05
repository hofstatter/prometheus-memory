# F1 — Query-side Expansion: baseline vs on (subset-20, seed 42)

- Data: 04/08/2026 · 19 instâncias · judge DeepSeek temp 0 · mesma sessão (modelo/seed idênticos)
- **Total: off 36.8% → on 36.8% (Δ = 0.0pp, rótulos idênticos)**

| Tipo | n | off | on |
|---|---|---|---|
| temporal-reasoning | 5 | 60.0% | 60.0% |
| knowledge-update | 3 | 66.7% | 66.7% |
| multi-session | 5 | 20.0% | 20.0% |
| single-session-user | 3 | 33.3% | 33.3% |
| single-session-preference | 1 | 0.0% | 0.0% |
| single-session-assistant | 2 | 0.0% | 0.0% |

## Notas

1. **Mecanismo VALIDADO** (smoke test PT, DB temporário): off → `[]` (gate mata
   "formação"×"formou"); on → memória recuperada (score 0.462 via variante "formou").
   A expansão roda de verdade (após fix do env no runner).
2. **Benefício real**: morfologia PT ("formação"→"formou") — positivo para produção
   (ecossistema PT), confirmado por T4 + smoke test.
3. **Sem efeito no subset EN**: o mapa determinístico (12 sinônimos + sufixos) é
   pequeno demais para o vocabulário parafraseado das 500 questões EN. O gap real é
   **sinonímia semântica** (pergunta e evidência sem tokens compartilhados) — o que
   o mini-mapa não cobre (paper resolve com key expansion no índice = F2, ou
   expansão de query por LLM).
4. **Critério de aceite da F1 NÃO atingido** no benchmark (esperado: total > 47.4% /
   multi-session > 20%). Decisão registrada em DECISIONS.md — ver opções A/B/C.
