# emil-design-eng — Apêndice de Referência (Design Engineering)

> Fonte: emilkowalski/skills (github.com/emilkowalski/skills, 22k★)
> **APÊNDICE DE REFERÊNCIA.** A autoridade de design é `design/super-designer/` (que já deriva desta fonte).
> **Em caso de divergência, super-designer vence.**
> Use este apêndice para profundidade em: animação, gestos, clip-path, toasts (Sonner), performance e acessibilidade.

## Animation Decision Framework

Pergunte antes de animar:
1. **Frequência?** >100x/dia (teclas, scroll, hover em lista) → NÃO anime
2. **Disparada por teclado?** → ZERO animação
3. **Resposta do sistema?** → instantânea (≤200ms)
4. **Ação deliberada?** (hold-to-delete, confirmação) → pode ser lenta (até 2s) — timing assimétrico é intencional

## Regras de Motion (detalhe)

- **Easing:** sempre ease-out forte `cubic-bezier(0.23, 1, 0.32, 1)`. `ease-in` proibido. `ease-in-out` robótico. `linear` só para loader indeterminado
- **Propriedades animáveis:** `transform`, `opacity`, cores de estado, `filter` (blur, brightness). NUNCA width/height/padding/margin/top/left
- **Origem de entrada:** `scale(0.95)` + `opacity: 0` — nunca `scale(0)` (nada no mundo real surge do nada)
- **Popovers/menus:** `transform-origin` no elemento trigger, não no centro
- **Blur como máscara:** 2px de blur resolve crossfade imperfeito entre estados
- **Stagger:** 30-80ms de delay entre filhos, sempre ease-out

## Componentes (detalhe)

### Buttons
- `:active` → `scale(0.97)`, 100-160ms
- Estados obrigatórios: hover, active, focus-visible, disabled, loading (mesmo tamanho)

### Tooltips
- Primeiro hover: delay 500ms
- Hovers subsequentes adjacentes: instantâneo (<100ms) — skip delay
- Máximo 1 linha

### Toasts (princípios Sonner)
- Entram com `scale(0.95)` + `translateY(8px)` + fade, 200-300ms
- Empilham com escala/offset decrescente, não com layout shift
- Pausam o auto-dismiss no hover
- Swipe-to-dismiss com physics (velocity > 0.11 = dismiss, senão snap back)

### Gestos (drag/swipe)
```js
if (velocity > 0.11) { dismiss(); } else { snapBack(); }
const rubberBand = (delta, max) => max * (1 - 1 / (Math.abs(delta) / max + 1));
```
- Pointer capture (não mouse events)
- Multi-touch protection (ignorar toques adicionais)
- Dismiss por velocidade, não só por distância
- Rubber-banding no limite, nunca hard stop

## Clip-path

- Use `clip-path: inset()` para reveals sem animar width/height (GPU-friendly)
- Transições de clip-path são animáveis entre formas compatíveis

## Performance

- Anime só propriedades compostas (transform/opacity/filter)
- `will-change` só durante a animação — remova depois (custa memória)
- Prefira transformações CSS a JS springs quando a física não é percebida
- Nada de animação em elementos dentro de listas longas com scroll

## Acessibilidade

```css
@media (prefers-reduced-motion: reduce) {
  *, *::before, *::after {
    animation-duration: 0.01ms !important;
    transition-duration: 0.01ms !important;
  }
}
```
- Todo motion envolvido em `@media (prefers-reduced-motion: no-preference)` ou zerado no `reduce`
- Focus visível sempre (2px outline + 2px offset)

## Debugging de animação

- Animação "travando"? Verifique se está animando propriedade de layout (width/height/margin)
- Elemento "pulando" no final? `transform-origin` errado ou `will-change` persistente
- Crossfade imperfeito? Adicione 2px blur na transição
- Jank em lista? Animação em item de lista durante scroll — remova

## Review Checklist (antes de entregar motion)

- [ ] Nenhum `ease-in` / `ease-in-out` / `transition: all`
- [ ] Só transform/opacity/filter animados
- [ ] Entradas de `scale(0.95)`, nunca `scale(0)`
- [ ] Popovers com origin no trigger
- [ ] Ações de teclado sem animação
- [ ] `prefers-reduced-motion` respeitado
- [ ] Durações UI ≤ 300ms (deliberadas podem ser mais)

---

*Em divergência com qualquer regra de `design/super-designer/`, a super-designer vence. Crédito: emilkowalski.*
