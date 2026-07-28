# Component Specifications

> Especificações completas de componentes. Aplique em todo projeto Flask/Jinja2 + Tailwind + Alpine.js.

---

## Buttons

```css
.btn-primary {
  background: var(--accent);
  color: #fff;
  padding: 8px 20px;
  border-radius: var(--radius-md);
  font-size: 14px;
  font-weight: 500;
  border: none;
  cursor: pointer;
  transition: transform 120ms cubic-bezier(0.23, 1, 0.32, 1);
}
.btn-primary:hover { filter: brightness(1.1); }
.btn-primary:active { transform: scale(0.97); }
.btn-primary:focus-visible { outline: 2px solid var(--accent); outline-offset: 2px; }
.btn-primary:disabled { opacity: 0.5; cursor: not-allowed; }
```

**Regras:**
- Texto em 1 linha no desktop (3 palavras máx)
- `scale(0.97)` no `:active`, 100-160ms
- `ease-out` forte, NUNCA `ease-in`
- WCAG AA: 4.5:1 contrast contra background
- Focus ring visível (2px outline + 2px offset)
- Loading state: mesmo tamanho, texto "..." ou spinner inline

---

## Cards

```css
.card {
  background: var(--surface-1);
  border: 1px solid var(--hairline);
  border-radius: var(--radius-lg);
  padding: var(--space-md);
}
.card-elevated {
  background: var(--surface-2);
  border: 1px solid var(--hairline-strong);
}
```

**Regras:**
- Um nível de superfície acima do canvas
- Hairline border OU soft shadow — NUNCA ambos
- Padding interno consistente (16-24px)
- Corner-radius do sistema da página
- NUNCA side-tab accent border (borda colorida só em um lado)
- NUNCA card dentro de card
- Empty state: ilustração centralizada + CTA único

---

## Forms / Inputs

```html
<div class="form-group">
  <label class="form-label">Email</label>
  <input type="email" class="form-input" placeholder="seu@email.com">
  <span class="form-error">Email inválido</span>
</div>
```

```css
.form-label { display: block; font-size: 13px; font-weight: 500; margin-bottom: 4px; color: var(--ink); }
.form-input {
  width: 100%; padding: 8px 12px;
  background: var(--canvas); border: 1px solid var(--hairline);
  border-radius: var(--radius-md); font-size: 14px; color: var(--ink);
  transition: border-color 150ms ease-out;
}
.form-input:focus { border-color: var(--accent); outline: none; }
.form-input.error { border-color: #ef4444; }
.form-error { display: none; font-size: 12px; color: #ef4444; margin-top: 4px; }
.form-input.error + .form-error { display: block; }
```

**Regras:**
- Label ACIMA do input
- Placeholder como exemplo, não como label
- Focus ring via border-color (não outline)
- Error state: borda vermelha + mensagem inline ABAIXO
- Min 44px tap target no mobile

---

## Navigation

```html
<nav class="nav">
  <span class="nav-brand">🧠 App Name</span>
  <div class="nav-links">...</div>
</nav>
```

```css
.nav {
  display: flex; align-items: center; gap: 24px;
  padding: 0 24px; height: 56px;
  background: var(--surface-1); border-bottom: 1px solid var(--hairline);
  position: sticky; top: 0; z-index: 50;
}
```

**Regras:**
- Altura ≤ 64px no desktop
- Sticky com `backdrop-filter: blur(8px)` se transparente
- Colapsa para hamburger abaixo de 768px
- Brand à esquerda, ações à direita
- Estados ativos com indicador sutil (underline ou bg shift)

---

## Modals / Drawers

```html
<div x-show="open" x-transition.opacity.duration.200ms class="modal-overlay" @click="open=false">
  <div x-show="open" x-transition.scale.95.opacity.duration.200ms class="modal-box" @click.stop>
    ...
  </div>
</div>
```

**Regras:**
- Overlay: `background: rgba(0,0,0,0.6)`, fade in 200ms
- Modal: `scale(0.95)` → `scale(1)`, 200-500ms ease-out
- `transform-origin: center` (não ancorado)
- Escape key fecha
- Click fora fecha
- Focus trap dentro do modal
- NUNCA `scale(0)` como origem

---

## Data Displays (Tabelas, Métricas)

```css
.metric-value { font-family: var(--font-mono); font-variant-numeric: tabular-nums; }
.table-row { border-bottom: 1px solid var(--hairline); }
.table-row:hover { background: var(--surface-2); }
```

**Regras:**
- Números em mono com `tabular-nums`
- Alinhamento direito para valores numéricos
- Cabeçalho sticky para tabelas longas
- Skeleton loader com mesmo layout do conteúdo final
- Empty state com entry point para popular

---

## Toasts / Notifications

```html
<div x-show="show" x-transition:enter="transition ease-out duration-300"
     x-transition:enter-start="translate-y-2 opacity-0 scale-95"
     x-transition:enter-end="translate-y-0 opacity-100 scale-100"
     class="toast">...</div>
```

**Regras:**
- Canto inferior direito (ou superior direito)
- `scale(0.95)` + `translateY(8px)` + `opacity: 0` → final
- 300ms ease-out
- Auto-dismiss após 5s (com pausa no hover)
- Máximo 3 toasts simultâneos
- Cor de fundo baseada no tipo (success=green, error=red, info=accent)

---

## Tooltips

**Regras:**
- Aparece com 500ms delay no primeiro hover
- Instantâneo (<100ms) em hovers subsequentes adjacentes
- 125-200ms duração
- `transform-origin` no elemento trigger
- NUNCA `scale(0)`
- Máximo 1 linha de texto
