# F0/F1 — Upgrade 3.15.1 validado + proposta do gate lexical no upstream

- Data: 05/08/2026 · Status: F0 VERDE + F1 POSTADO

## F0 — Upgrade mnemosyne-memory 3.12.2 → 3.15.1 (venv de teste isolado)

| Teste | 3.12.2 (atual) | 3.15.1 (venv) | Resultado |
|---|---|---|---|
| pytest (suíte completa) | 78 passed, 1 skip | **79 passed, 0 skip** | ✅ melhorou |
| Régua PT hit@5 (`eval_pt_recall.py`, 32 pares) | 14/32 (43.8%) | 14/32 (43.8%) | ✅ idêntico |
| LongMemEval EN subset-20 (judge real, mesma sessão) | 42.1% (referência tarde) | **42.1%** | ✅ sem drift |
| FK fix (DB fresco, remember sem hack de drop) | bug (IntegrityError) | **OK, 2/2 gravados + recall n=2** | ✅ corrigido upstream #452 |

→ **3.15.1 segura para adotar**: mesmo comportamento de recall + bug FK resolvido de graça.
  O hack `_prepare_db` (drop/recreate memory_embeddings) dos harnesses NÃO é mais necessário.

## F1 — Proposta no upstream (issue #622)

- Comentário postado: https://github.com/mnemosyne-oss/mnemosyne/pull/622#issuecomment-5189054413
  (usuário hofstatter, 05/08 07:46 UTC) — confirmação independente do root cause + dados medidos
  (PT hit@5, EN LongMemEval, gate on/off) + proposta do knob **`MNEMOSYNE_LEXICAL_GATE_MIN`**
  (float 0-1, default = comportamento atual, retrocompatível) + oferta de PR
  `feat/lexical-gate-knob`.
- Próximo: aguardar resposta do autor/mantenedor (7 dias) → sinal positivo ou timeout → PR (Fase 2).

## Nota

O run da 3.15.1 ficou registrado em `evals/reports/p5-multilingue-pt.md` (evidência contínua).
