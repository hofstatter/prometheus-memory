# PLAN — Fix de autoria dos commits da PR #639 (upstream mnemosyne)

- **Classificação:** SMALL · **Estado:** EXECUTADO sessão 44 (06/08/2026)
- **Motivo:** commits `e97a122`/`1cc4aa0`/`df7e49b` da PR #639 (mnemosyne-oss/mnemosyne) foram
  commitados com e-mail `herbert@users.noreply.github.com` — noreply de uma conta GitHub **alheia**
  (username "herbert"), não a do Herbert (username real: `hofstatter`). CLAassistant exige que todos
  os autores assinem o CLA → impossível pois "herbert" não é conta do Herbert.
- **Objetivo:** reescrever autor/committer para `Herbert Hofstatter <hofstatter@users.noreply.github.com>`
  e force-push na branch da PR. Conteúdo dos commits: **zero alteração**.

---

## Fases

| Fase | Ação | Critério de aceite | Status |
|---|---|---|---|
| 0 | Backup (STATE/CONTEXT/GUARDRAILS) + este PLAN | backup exit 0 | ✅ |
| 1 | Clonar fork `hofstatter/mnemosyne` (em /tmp) + checkout `feat/lexical-gate-knob` | branch checkout | ⏳ |
| 2 | `git filter-branch --env-filter` → reescreve autor/committer dos 3 commits para hofstatter@ | `git log` mostra só hofstatter@ | ⏳ |
| 3 | Validar: `git log --format` = 4 commits, 3 com hofstatter@ + 1 web (herbertsuporte@gmail.com) intacto; conteúdo idêntico (tree hash) | tree hashes iguais | ⏳ |
| 4 | Force-push `--force-with-lease` com GH_PAT (credential helper inline, aspas duplas) | push exit 0; GitHub mostra commits com hofstatter | ⏳ |
| 5 | `git config --global user.name/email` = Herbert Hofstatter / hofstatter@users.noreply.github.com | `git config --global user.email` retorna hofstatter@ | ⏳ |
| 6 | GUARDRAILS regra 20 (GIT GATE): Inspetor verifica autor dos commits == hofstatter@ em toda revisão pré-push | grep no GUARDRAILS | ⏳ |
| 7 | STATE/CONTEXT/Mnemosyne: incidente + lição | seções atualizadas + memórias | ⏳ |

## Riscos / armadilhas

- Force-push em branch de PR aberta: seguro se ninguém deu checkout (mantenedores não revisaram —
  janela ideal). `--force-with-lease` protege contra overwrite de push alheio.
- `filter-branch` é deprecated mas funciona; usar `--env-filter` só trocando e-mail, nunca conteúdo.
- NÃO tocar no 4º commit `0a05989` (web, já atribuído a hofstatter via herbertsuporte@gmail.com).
- Não rebasear sobre main atual (scope creep) — a PR está "out-of-date" mas mergeável; mantenedor decide.
- GH_PAT: usar aspas DUPLAS no credential helper inline (aspas simples não expandem a variável —
  erro da sessão 44 no push do prometheus-memory).
- Depois do force-push: CI re-roda (~5min) + CodeRabbit re-revisa — inofensivo; CLA rechecka automático.
