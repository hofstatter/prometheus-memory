# Motion — Regras de Animação

> Toda animação deve ter propósito, física e respeito ao usuário.
> Fonte: emilkowalski/skills + apple-design

---

## Curvas de Easing

```css
/* Ease-out forte — padrão para UI (substitui o ease-out do browser) */
--ease-out-strong: cubic-bezier(0.23, 1, 0.32, 1);

/* Ease-out sutil — para hover/color transitions */
--ease-out-subtle: cubic-bezier(0.4, 0, 0.2, 1);

/* iOS drawer — para modais e drawers */
--ease-ios: cubic-bezier(0.32, 0.72, 0, 1);

/* Spring sutil — para drag release (JS apenas) */
--spring-gentle: { type: "spring", stiffness: 200, damping: 25, mass: 0.5 };
```

## PROIBIDO

- `ease-in` — NUNCA use. Sempre ease-out.
- `ease-in-out` — muito simétrico, parece robótico.
- `linear` — só para loader indeterminado ou progress bar.
- Animar `width`, `height`, `padding`, `margin`, `top`, `left`.
- `transition: all` — sempre especificar propriedades exatas.

## PERMITIDO animar

- `transform` (translate, scale, rotate)
- `opacity`
- `background-color`, `border-color`, `color` (transições de estado)
- `filter` (blur, brightness)

---

## Tabela de Durações

| Elemento | Duração | Easing |
|---|---|---|
| Button press | 100-160ms | ease-out-strong |
| Toggle/Switch | 100-150ms | ease-out-strong |
| Tooltip (show/hide) | 125-200ms | ease-out-subtle |
| Dropdown (open/close) | 150-250ms | ease-out-strong |
| Toast (enter/exit) | 200-300ms | ease-out-strong |
| Modal (open/close) | 200-400ms | ease-ios |
| Page transition | 300-500ms | ease-out-strong |
| Stagger children | 30-80ms delay | ease-out-strong |

---

## Frequência de Animação

| Frequência | Exemplo | Animar? |
|---|---|---|
| >100x/dia | Teclas, scroll, hover em lista | ❌ NÃO |
| 10-100x/dia | Dropdown, tooltip, toggle | ✅ Padrão |
| <10x/dia | Modal, drawer, onboarding | ✅ Delight permitido |

---

## Gestos (Drag/Swipe)

```js
// Momentum threshold para dismiss (velocidade > 0.11)
if (velocity > 0.11) { dismiss(); }
else { snapBack(); }

// Rubber-banding no limite
const rubberBand = (delta, max) => max * (1 - 1 / (Math.abs(delta) / max + 1));
```

**Regras:**
- Pointer capture para drag (não mouse events)
- Multi-touch protection (ignorar toques adicionais)
- Velocity-based dismiss (não distance-based apenas)
- Damping no limite (rubber-banding, não hard stop)

---

## Acessibilidade

```css
@media (prefers-reduced-motion: reduce) {
  *, *::before, *::after {
    animation-duration: 0.01ms !important;
    transition-duration: 0.01ms !important;
  }
}
```

- Todo `@keyframes` e `transition` deve ser envolvido em `@media (prefers-reduced-motion: no-preference)`
- Alternativa: zerar durações no `reduce`
