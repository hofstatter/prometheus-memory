# PLAN — Identidade git canônica (3 camadas) + MCPs nos agentes + screenshots Opção B

- **Classificação:** SMALL · **Estado:** EXECUTADO sessão 44 (06/08/2026)
- **Motivo:** incidente PR #639 (commits com e-mail de conta alheia `herbert@...`). Herbert aprovou
  as 3 camadas de prevenção + verificação de uso correto dos MCPs pelos agentes + atualizar os 5
  screenshots desatualizados do repo.

---

## Fases

| # | Ação | Critério de aceite | Status |
|---|---|---|---|
| 0 | Backup + este PLAN | backup exit 0 | ⏳ |
| 1 | **Camada 2:** bloco identidade canônica + MCPs D6/D8 no `build.md` (Pedreiro) e `inspector.md` (checklist identidade) | grep "hofstatter@users.noreply.github.com" nos 2 arquivos | ⏳ |
| 2 | **GUARDRAILS regra 20 → v5.4:** bloco identidade canônica citado pela regra | grep no GUARDRAILS | ⏳ |
| 3 | **Camada 3 (trava mecânica):** `pre-push` hook com allowlist de e-mails (bloqueia push se `git log @{u}..HEAD --format=%ae` sair da lista) — prometheus-memory + script compartilhado `~/bin/git-hook-pre-push.sh` | push com e-mail errado → bloqueado; correto → passa (teste) | ⏳ |
| 4 | **Screenshots Opção B** (Playwright :8777): canvas.png, timeline.png, notes.png, rag.png, projetos.png → Visionário valida cada um (nota ≥7/10) | 5 screenshots novos + validação | ⏳ |
| 5 | Commit + push (screenshots + docs; GIT GATE: Inspetor ✅ + SIM Herbert) | push exit 0 | ⏳ |
| 6 | STATE.md + CONTEXT.md + Mnemosyne | seções atualizadas | ⏳ |

## Identidade canônica (a ser gravada nos 3 lugares)

> **Identidade Git ÚNICA do Herbert:** nome `Herbert Hofstatter` · username GitHub `hofstatter` ·
> e-mails permitidos: `hofstatter@users.noreply.github.com` (canônico CLI) e `herbertsuporte@gmail.com`
> (web UI). **PROIBIDO qualquer outro** — `herbert@users.noreply.github.com` é conta ALHEIA
> (incidente PR #639, 06/08).

## MCPs (a registrar no build.md)

- **Cascata D8:** Context7 (doc lib) → gh_grep (código) → Tavily (busca) → Firecrawl (scrape/crawl);
  nunca Tavily+Firecrawl na mesma query.
- **Screenshot D6:** localhost/privado → Playwright · URL pública → ScreenshotAPI (`enable_caching=true`).
- Inspector: verificar `%ae` de todos os commits na allowlist em toda revisão pré-push.

## Riscos

- Hook pre-push: manter compatível com o marcador `.git/PUSH_APPROVED` existente (checar AMBOS).
- Screenshots: abas com dados reais (timeline mostra memórias) — ok para repo público (já publicado antes).
- Não quebrar o fluxo GIT GATE: hook novo só adiciona a checagem de e-mail, não remove a de marcador.
