# DESIGN — Aba Projetos (Prometheus Memory v0.2)

> Fonte: `super-designer` (skill) — true portátil de design da aba Projetos.
> Data: 03/08/2026 · Lane: **product** · Status: aplicado nas fases A/A2/A3/B

## Design Read

```text
Page: Dashboard de projetos / kanban operacional
Audience: dev operando múltiplos projetos simultâneos
Lane: product
VARIANCE: 4 | MOTION: 3 | DENSITY: 8
Palette: herdar tokens atuais (Linear dark) — NENHUMA cor de destaque nova
Display: system-ui | Body: system-ui
```

## Tokens (herdados de `:root` do index.html)

| Token | Valor | Uso |
|---|---|---|
| `--canvas` / `--surface-1/2/3` | escada de superfícies | elevação por superfície, não sombra |
| `--hairline` / `--hairline-strong` | 1px | bordas de separação |
| `--accent` | #5e6ad2 | barra de progresso + foco (máx. 4 usos) |
| `--ink` / `--ink-muted` | texto | hierarquia por weight+size+leading |
| `--radius-md/lg` · `--ease-out` | 8/12px · cubic-bezier | cantos + motion |

## Cores semânticas (estados, não decoração)

| Estado | Cor |
|---|---|
| presence active / skill active / git clean | `#22c55e` |
| presence idle / draft / dirty | `#eab308` |
| stale / archived / sem uso | `#6b7280` |
| blocked / "pago e sem uso" / não versionado | `#ef4444` |
| MCP/db/entity chips | `#0ea5e9` (com alpha 1a/40) |

## Regras aplicadas

1. **Zero animação em ações frequentes** — polling de presença e troca de board não animam; só a barra de progresso (0.4s `--ease-out`) e o drawer (0.25s).
2. **Feedback de clique** — cards com `transform: scale(1)` + `:active scale(0.97)` implícito via cursor; sem micro-animações decorativas.
3. **3 cards iguais?** — o kanban usa 3 colunas iguais por necessidade de padrão mental (Backlog/Em andamento/Concluído) — exceção consciente documentada; o resto da página usa grid assimétrico (KPIs flex, stack 2 colunas, blocos empilhados).
4. **Segredos** — fingerprint mascarado (`442cbf••••`); **nunca** valor de chave na UI.
5. **Densidade 8** — tabela de conexões e chips compactos; cabe "passar o olho" em <5s (objetivo declarado por Herbert).
6. **XSS** — todo dado dinâmico passa por `esc()`; eventos/cliques via `data-*` + delegação (sem interpolação em `onclick`).

## Anti-padrões evitados

- ❌ Paleta AI (roxo neon/bege) — herdada a atual; sem cores novas
- ❌ Sombra como elevação — só surface + hairline
- ❌ `scale(0)` em entradas — drawer usa `width 0→320px` + `--ease-out`
- ❌ Emoji como dado — ícones são labels de aba, dados são texto sanitizado

## Checklist pré-entrega (resumo)

- [x] Contraste texto/fundo OK nos tokens atuais
- [x] Foco visível (accent) em controles
- [x] i18n EN/PT/ES/ZH nas labels novas
- [x] Zero segredo renderizado (testes C1-C5 + revisão Inspetor)
- [x] Drawer fecha (✕) e não vaza para outras abas

*Screenshot pendente:* `docs/SCREENSHOTS/projetos.png` — captura local (browser tool) no próximo passe.
