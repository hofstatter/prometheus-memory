# Design Tokens — Paletas, Tipografia & Espaçamento

> Sistema de tokens portátil. Todo projeto gera seu DESIGN.md a partir destas regras.

---

## Paletas — Dark Product Lane (Dashboards, Admin, Tools)

### Linear-Inspired (recomendado para Memory Browser, Loop Dashboard)

| Token | Cor | Uso |
|---|---|---|
| `--canvas` | `#010102` | Fundo da página |
| `--surface-1` | `#0f1011` | Cards |
| `--surface-2` | `#141516` | Cards elevados, modais |
| `--surface-3` | `#18191a` | Hover states |
| `--accent` | `#5e6ad2` | CTA, focus, links, brand |
| `--ink` | `#f7f8f8` | Texto primário |
| `--ink-muted` | `#8a8f98` | Texto secundário |
| `--ink-subtle` | `#62666d` | Texto terciário |
| `--hairline` | `#23252a` | Borda 1px |
| `--hairline-strong` | `#34343a` | Borda ativa |

### Stripe-Inspired

| Token | Cor | Uso |
|---|---|---|
| `--canvas` | `#0a0f1a` | Fundo |
| `--surface-1` | `#111827` | Cards |
| `--surface-2` | `#1a2236` | Elevado |
| `--accent` | `#635bff` | CTA, focus |
| `--ink` | `#f0f2f5` | Texto |
| `--ink-muted` | `#8896a7` | Secundário |
| `--hairline` | `#1e293b` | Borda |

---

## Paletas — Light Product Lane

### Notion-Inspired

| Token | Cor | Uso |
|---|---|---|
| `--canvas` | `#ffffff` | Fundo |
| `--surface-1` | `#f7f6f3` | Sidebar, cards |
| `--surface-2` | `#efeee9` | Hover |
| `--accent` | `#2383e2` | CTA, links |
| `--ink` | `#37352f` | Texto |
| `--ink-muted` | `#9b9a97` | Secundário |
| `--hairline` | `#e9e9e7` | Borda |

---

## Tipografia

### Product Lane (Dashboards, Admin)

| Nível | Fonte | Size | Weight | Line | Tracking |
|---|---|---|---|---|---|
| Display | System | 32px | 600 | 1.2 | -0.02em |
| h1 | System | 24px | 600 | 1.3 | -0.01em |
| h2 | System | 18px | 600 | 1.4 | 0 |
| h3 | System | 15px | 600 | 1.4 | 0 |
| Body | System | 14px | 400 | 1.5 | 0 |
| Caption | System | 12px | 400 | 1.5 | 0 |
| Mono | JetBrains Mono | 13px | 400 | 1.5 | 0 |

### Brand Lane (Landing Pages)

| Nível | Exemplos de Fontes |
|---|---|
| Display | Cabinet Grotesk, Satoshi, Switzer, Geist |
| Headline | Display font (bold weight) ou serif (editorial) |
| Body | System stack (`-apple-system, sans-serif`) |

---

## Espaçamento (4px base)

| Token | Valor | Uso |
|---|---|---|
| `--space-xs` | 4px | Gap ícone-texto |
| `--space-sm` | 8px | Gap interno pequeno |
| `--space-md` | 16px | Padding padrão de card |
| `--space-lg` | 24px | Gap entre seções |
| `--space-xl` | 32px | Padding de página |
| `--space-section` | 64px | Gap entre seções grandes |

---

## Border Radius

| Token | Valor | Uso |
|---|---|---|
| `--radius-sm` | 4px | Chips, badges |
| `--radius-md` | 8px | Botões, inputs |
| `--radius-lg` | 12px | Cards |
| `--radius-xl` | 16px | Modais |
| `--radius-pill` | 9999px | Toggles |

---

## Regra de Ouro

**Antes de qualquer projeto, gere um DESIGN.md com estes tokens aplicados ao contexto específico.**
Não use os valores acima cegamente — adapte ao tipo de página, audiência e vibe.
Mas NUNCA use as paletas proibidas (AI purple, bege+creme, cyan neon).
