# PLAN — Commit público F1/F1.1 (grafo real) + docs 4 idiomas + screenshot

- **Classificação:** MEDIUM · **Estado:** EXECUTADO sessão 44 (06/08/2026)
- **Repo alvo:** `github.com/hofstatter/prometheus-memory` (main=46eb261, pré-commit)
- **Gate:** Inspetor APROVADO → commit local → push somente com OK verbal do Herbert (repo público)

---

## Escopo do commit

**Incluir:**
- `web/graph_service.py` (novo) — PageRank + degree em Python puro (F1)
- `web/app.py` — endpoint `/api/graph` real + recall `graph_degree` (F1)
- `web/templates/index.html` — UI G6 (legenda, badge, modo denso/circular) (F1+F1.1)
- `scripts/backfill_graph_edges.py` (novo) — 769 edges reais (F1.1, já revisado)
- `docs/PLAN_SEMANTICA_GRAFO_F1.md`, `docs/PLAN_SEMANTICA_GRAFO_F1_1.md`,
  `docs/PLAN_QUALIDADE_RECALL_P3.md`, `docs/PLAN_UPSTREAM_LEXICAL_GATE.md` (novos)
- `docs/DECISIONS.md` (modificado — inclui D6/D7/D8)
- `docs/SCREENSHOTS/graph.png` (screenshot novo da aba Grafo, substitui o de 25/07)
- `README.md` (EN) + `docs/lang/README.pt-BR.md`, `README.es.md`, `README.zh-CN.md` (seção Knowledge Graph)
- `.gitignore` (+ `web/mnemosyne-doctor.*`)

**Excluir:** `web/mnemosyne-doctor.{json,md}` (artefatos gerados — D7)

## Fases

| Fase | Ação | Critério de aceite | Status |
|---|---|---|---|
| 0 | PLAN + DECISIONS (D6/D7/D8) + backup | backup exit 0, DECISIONS com D6–D8 | ✅ |
| 1 | Inspetor revisa diff (read-only) | veredito APROVADO | ⏳ |
| 2 | Roteamento visual + cascata D8 nos docs de config (visionario.md, GUARDRAILS, FLUXO_BIMODELO, NB02) + teste real ScreenshotAPI | grep "url pública" em visionario+GUARDRAILS; chamada real retorna imagem | ⏳ |
| 3 | Screenshot aba Grafo (Playwright, :8777) → `docs/SCREENSHOTS/graph.png` + Visionário valida | nota ≥7/10 APROVADO | ⏳ |
| 4 | Seção Knowledge Graph nos 4 READMEs + .gitignore | imagem renderiza nos 4 (caminho relativo) | ⏳ |
| 5 | Commit local (estilo repo) → **parar no push (gate humano)** | `git log --oneline -1` local | ⏳ |
| 6 | STATE.md + CONTEXT.md + Mnemosyne | seções atualizadas + memória gravada | ⏳ |

## Risco / armadilhas

- Repo **público**: push exige OK verbal explícito do Herbert (nunca push silencioso).
- Não commitar `mnemosyne-doctor.*` por acidente (D7, `.gitignore`).
- Screenshot novo deve bater com o que o README descreve (aba Grafo, visão densa, badge).
- `git add` seletivo por arquivo, nunca `git add .` (evita doctor.* e .playwright-mcp/).
