# PLAN_UPSTREAM_LEXICAL_GATE.md — Opção A: destravar o recall via upstream mnemosyne

- **Repo alvo:** `github.com/mnemosyne-oss/mnemosyne` (upstream, contribuição) · **Repo local:** prometheus-memory
- **Classificação:** MEDIUM (contribuição open source externa + possível upgrade de dependência — superfície sensível)
- **Data:** 05/08/2026 · **Status:** APROVADO por Herbert (05/08) — AGUARDANDO ordem de execução

---

## 1. Contexto e objetivo

O recall do Prometheus (e de todo usuário do mnemosyne) é limitado por um **gate lexical
hardcoded** em `mnemosyne/core/beam.py`: candidatos cuja pergunta **não compartilha tokens**
com a memória são descartados ANTES de o embedding vetorial decidir — mesmo que o significado
seja idêntico (sinonímia semântica). Sessão 39 provou: relaxando o gate, o e5-large ganha
+3.1pp no PT; com o gate ativo, qualquer troca de embedding é neutra.

Objetivo: **oferecer o knob `MNEMOSYNE_LEXICAL_GATE_MIN` ao upstream** para destravar o
recall para todos — contribuição com evidências medidas (régua PT + LongMemEval).

## 2. Investigação upstream (05/08 — fatos verificados)

| Fato | Detalhe |
|---|---|
| Repo upstream | `mnemosyne-oss/mnemosyne` (org — antes `AxDSan/mnemosyne`), 2096 ⭐, **MIT**, ativo (push 05/08) |
| Versão instalada local | `mnemosyne-memory 3.12.2` · **PyPI latest: 3.15.1** (3 minors atrás) |
| **Bug FK** (`memory_embeddings` → `memories`) | ✅ **JÁ CORRIGIDO upstream** — issue **#452** fechada, migração idempotente no init (CHANGELOG 3.13+) |
| **Gate lexical** (`_minimum_recall_relevance` / `_lexical_relevance`) | ❌ **AINDA HARDCODED no main** — função idêntica à nossa 3.12.2; **o knob não existe** |
| Issue relacionada | **#622 ABERTA** — "docs(configuration): document the lexical recall gate + measured recall-flag data" → pede exatamente documentar/compor o gate; ninguém implementou o knob |

**Conclusão:** o knob é o único item novo que temos a oferecer; a FK já está resolvida no
upstream (basta atualizarmos a dependência).

## 3. Decisões técnicas

| # | Decisão | Porquê |
|---|---|---|
| D1 | Contribuir o knob **ao upstream** (não manter monkeypatch local) | Monkeypatch só funciona no nosso harness; knob oficial destrava o recall para todos e reforça a reputação |
| D2 | **`MNEMOSYNE_LEXICAL_GATE_MIN`** (float 0.0–1.0; **default = comportamento atual**) | Padrão de nomenclatura `MNEMOSYNE_*`; default retrocompatível = risco zero para usuários existentes |
| D3 | **Comentar na issue #622 primeiro** com nossas evidências e oferecer o PR | Contribuidor externo: alinhar com o mantenedor evita retrabalho e mostra dados reais |
| D4 | **Upgrade 3.12.2 → 3.15.1 isolado** (venv de teste) com bateria completa | FK fix vem "de graça"; 3 minors podem quebrar integração nossa — testar antes de adotar |
| D5 | Evidências: `evals/reports/p5-e5-large.md` + `p5-multilingue-pt.md` | Contribuição com dados medidos é levada a sério; temos PT e EN |
| D6 | Plano B documentado: se upstream recusar/mudos, patch local documentado (monkeypatch em camada nossa) | Nunca editar site-packages; patch fica rastreável e substituível |

## 4. Passos e critérios de aceite executáveis

### Fase 0 — Preparação local (sem tocar upstream)
1. Venv de teste: `python3 -m venv /tmp/mnemosyne-upgrade && pip install mnemosyne-memory==3.15.1`.
2. Suíte completa do Prometheus contra 3.15.1 (`pytest` — 78 passed/1 skip esperados) + régua PT
   (`scripts/eval_pt_recall.py`) + LongMemEval subset-20 (judge real).
3. Confirmar FK fix: DB fresco → remember → **sem** `IntegrityError: FOREIGN KEY constraint failed`.
   - *Aceite:* suíte verde na 3.15.1 + FK fix confirmado em DB fresco.
   - *Se quebrar:* permanecer na 3.12.2 e knob vira patch local documentado (plano B).

### Fase 1 — Proposta ao upstream (requer SIM do Herbert)
4. Comentário na **issue #622** (inglês): caso real (recall PT/EN bloqueado pelo gate), dados
   medidos (PT hit@5 gate on/off; EN LongMemEval; e5-large neutro com gate, +3.1pp sem),
   proposta `MNEMOSYNE_LEXICAL_GATE_MIN` com default inalterado.
   - *Aceite:* resposta do mantenedor OU 7 dias sem resposta → seguir para Fase 2.

### Fase 2 — PR (só com sinal positivo ou timeout)
5. Fork + branch `feat/lexical-gate-knob`: `_minimum_recall_relevance` lê o env; atualizar
   `docs/api/configuration.mdx`; teste unitário (gate default = atual; env abaixa o gate).
6. Rodar testes do upstream; abrir PR.
   - *Aceite:* PR aberto no `mnemosyne-oss/mnemosyne` com CI verde.

## 5. Riscos e mitigações

1. **Upgrade 3.15.1 quebra integração** → testar em venv isolado (Fase 0); rollback `==3.12.2`.
2. **Mantenedor não responde** → 7 dias → PR direto; se rejeitado → patch local documentado (D6).
3. **Knob mal calibrado piora precisão** (mais ruído) → default = comportamento atual; medir
   com a régua PT antes/depois (hit@5 e falsos positivos).
4. **Contribuição pública expõe dados** → só métricas agregadas nos relatórios; nenhuma memória
   real vai para o PR/issue.

## 6. Fora de escopo (não fazer)

- NÃO editar site-packages do mnemosyne em produção.
- NÃO ativar API/OpenRouter de embeddings.
- NÃO trocar o embedding atual (bge-small mantido — decisão P5).
- NÃO migrar dados de memória nesta fase (não há troca de modelo).
