# Preflight Checklist — 35 Verificações Obrigatórias

> Antes de considerar QUALQUER design como concluído, execute TODOS os checks.
> Se QUALQUER um falhar, corrija ANTES de entregar.

---

## Design Foundation (6)

- [ ] Design Read declarado (tipo + audiência + vibe + lane)
- [ ] 3 Dials definidos (VARIANCE, MOTION, DENSITY)
- [ ] DESIGN.md gerado para esta página
- [ ] Uma cor de destaque, máximo 4 usos (CTA, focus, links, brand)
- [ ] Um sistema de border-radius, aplicado consistentemente
- [ ] Um tema (light/dark/auto), sem flips no meio da página

## Tipografia (5)

- [ ] Hierarquia clara (≥1.25 ratio entre steps de tipo)
- [ ] Fontes pareadas (display + body, ou system stack + mono)
- [ ] Inter NÃO é default (se for, tem justificativa explícita)
- [ ] Sem all-caps body text
- [ ] Sem letter-spacing < -0.05em em body

## Cor & Contraste (4)

- [ ] Sem gradiente purple/violet, cyan neon, bege+creme
- [ ] Sem gradient text (`background-clip: text`)
- [ ] Todo texto passa WCAG AA (4.5:1 body, 3:1 large)
- [ ] Sem gray text (#888+) em background não-branco

## Layout (5)

- [ ] Hero cabe na viewport (máx 2 linhas headline, máx 20 palavras subtexto)
- [ ] Sem nested cards
- [ ] Sem grid de 3 cards idênticos
- [ ] Sem espaçamento monótono (tight groupings + generous separations)
- [ ] Máximo 1 eyebrow por 3 seções

## Navegação (2)

- [ ] Nav single-line no desktop, altura ≤ 80px
- [ ] Colapsa para hamburger abaixo de 768px

## Motion (4)

- [ ] Sem `ease-in` em lugar nenhum
- [ ] Sem animação em ações de teclado ou >100/dia
- [ ] Todas as durações de UI ≤ 300ms
- [ ] Apenas `transform` + `opacity` animados

## Componentes (4)

- [ ] Botões: `scale(0.97)` no `:active`, estados hover/active/focus/disabled/loading
- [ ] Botões: texto cabe em 1 linha no desktop
- [ ] Forms: label ACIMA do input, erro ABAIXO
- [ ] Cards: um nível de superfície, hairline OU shadow (nunca ambos)

## Estados (3)

- [ ] Empty state para todo componente interativo
- [ ] Loading skeleton para todo conteúdo assíncrono
- [ ] Error state com mensagem e ação de recuperação

## Copy (2)

- [ ] Zero em-dashes (—) no texto
- [ ] Zero buzzwords (streamline, empower, supercharge, world-class)

---

**Total: 35 checks. NENHUM pode falhar.**

Se todos passarem, o design está APTO para entrega.
