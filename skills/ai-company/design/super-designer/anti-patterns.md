# Anti-Patterns — 46 Padrões Proibidos

> Se qualquer um destes aparecer no output, corrija IMEDIATAMENTE.
> Fonte: impeccable.style + tasteskill.dev + ui-ux-pro-max-skill

---

## Visual (7)

| # | Padrão | Detecção |
|---|---|---|
| 1 | Rounded card + thick border clash | `border-radius > 8px` E `border-width > 2px` |
| 2 | Glassmorphism como decoração | `backdrop-filter: blur()` sem propósito funcional |
| 3 | Side-tab accent border | Borda colorida só no lado esquerdo de card |
| 4 | Ghost cards | `border: 1px solid` + `box-shadow` com blur > 10px |
| 5 | Extreme border-radius | `border-radius > 24px` em cards de conteúdo |
| 6 | Hand-drawn SVG illustrations | SVG decorativo inline não-icônico |
| 7 | Custom mouse cursors | `cursor: url(...)` |

## Tipografia (10)

| # | Padrão | Detecção |
|---|---|---|
| 8 | Flat hierarchy | Diferença < 1.25 entre steps de tipo |
| 9 | Icon tile stacked above heading | Ícone solitário centralizado acima de h2 |
| 10 | Italic serif hero | Hero com fonte serif itálica |
| 11 | Hero eyebrow/pill chip | Badge/chip antes do headline principal |
| 12 | Repeated section kicker labels | Mesmo texto de eyebrow em múltiplas seções |
| 13 | Oversized hero headline | `font-size > 72px` em mobile |
| 14 | Crushed letter-spacing | `letter-spacing < -0.05em` em body |
| 15 | Inter como default | `font-family: 'Inter'` sem pairing |
| 16 | Single font for everything | Apenas 1 font-family na página inteira |
| 17 | All-caps body text | `text-transform: uppercase` em parágrafos |

## Cor & Contraste (5)

| # | Padrão | Detecção |
|---|---|---|
| 18 | AI color palette | Gradiente purple→violet, cyan glow em dark |
| 19 | Gradient text | `background-clip: text` com gradiente |
| 20 | Gray text on colored bg | Texto #888+ em background não-branco |
| 21 | Cream/beige default | `#f5f1ea`, `#f7f5f1`, `#fbf8f1` como bg principal |
| 22 | Dark mode glowing accents | `box-shadow: 0 0 20px` em cor neon |

## Layout & Espaço (8)

| # | Padrão | Detecção |
|---|---|---|
| 23 | Hero metric layout | 3-4 números grandes lado a lado no hero |
| 24 | Identical card grids | 3+ cards com mesmo tamanho/layout em grid |
| 25 | Monotonous spacing | Mesmo gap entre TODAS as seções |
| 26 | Nested cards | Card dentro de card |
| 27 | Numbered section markers | "01 / 02 / 03" como labels de seção |
| 28 | Line length too long | `max-width > 75ch` em body text |
| 29 | Content overflowing | Qualquer elemento com scroll horizontal |
| 30 | Positioned child clipped | Elemento com `position: absolute` cortado pelo pai |

## Movimento (3)

| # | Padrão | Detecção |
|---|---|---|
| 31 | Bounce/elastic easing on UI | `cubic-bezier` com overshoot em UI |
| 32 | Animating layout properties | `transition: width/height/padding/margin` |
| 33 | Image hover transform | `transform: scale(1.05)` em hover de imagem |

## Copy (4)

| # | Padrão | Detecção |
|---|---|---|
| 34 | Em-dash overuse | `—` (em-dash) em qualquer lugar |
| 35 | Marketing buzzwords | "streamline", "empower", "supercharge", "world-class" |
| 36 | Aphoristic cadence | Frases curtas com ponto final em sequência |
| 37 | "Theater" framing | "Where X meets Y", "A new era of Z" |

## Qualidade Geral (8)

| # | Padrão | Detecção |
|---|---|---|
| 38 | Cramped padding | `padding < 12px` em cards/containers |
| 39 | Body touching viewport edge | Sem padding horizontal no body |
| 40 | Justified text | `text-align: justify` |
| 41 | Low contrast | Ratio < 4.5:1 em body text |
| 42 | Skipped heading | h1 → h3 (sem h2 entre eles) |
| 43 | Tight line height | `line-height < 1.4` em body |
| 44 | Tiny body text | `font-size < 14px` em parágrafos |
| 45 | Wide letter-spacing on body | `letter-spacing > 0.05em` em body |
| 46 | Div-fake screenshots | Div estilizado simulando screenshot de produto |

---

## Exceções

Nenhuma. Estes 46 padrões são **proibidos em todos os contextos**.
Se você acha que precisa de uma exceção, está errado.
