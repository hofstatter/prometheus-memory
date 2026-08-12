/* Canvas v2 — chips de projeto, legenda, highlight de subgraph e cross-link p/ aba Projetos. */
(function(){
  'use strict';
  var S = { chips: [], selected: null, userChoice: false, origSet: false };

  function esc(s){
    if (typeof window.escapeHtml === 'function') return window.escapeHtml(s);
    return String(s == null ? '' : s).replace(/[&<>"']/g, function(c){
      return {'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c];
    });
  }

  function clusterLabel(g){
    var el = g.querySelector('.cluster-label');
    return el ? (el.textContent || '').trim() : (g.textContent || '').trim();
  }

  function setupCanvasExtras(){
    loadCanvasChips();
    var orig = window.handleCanvasClick;
    if (orig && !S.origSet){
      S.origSet = true;
      window.handleCanvasClick = function(e){
        orig(e);
        addCanvasCrossLink(e);
      };
    }
  }

  function loadCanvasChips(){
    var el = document.getElementById('canvas-chips');
    if (!el) return;
    fetch('/api/pm/projects').then(function(r){ return r.json(); }).then(function(data){
      S.chips = (data.projects || []).map(function(p){
        return { slug: p.slug, name: p.name || p.slug, progress: p.progress || 0 };
      });
      renderChips(el);
      // Default (1ª carga apenas): mostra só o projeto mais ativo — Opção A
      if (!S.userChoice && !S.selected){
        var last = (data.projects || []).slice()
          .filter(function(p){ return p.last_event_at; })
          .sort(function(a,b){ return String(b.last_event_at).localeCompare(String(a.last_event_at)); })[0];
        if (last && last.slug){
          S.selected = last.slug;
          renderChips(el);
          setTimeout(function(){ selectCanvasFilter(last.slug); }, 80);
        }
      }
    }).catch(function(){});
  }

  function renderChips(el){
    var all = '<button data-cslug="__all__" style="border:1px solid var(--hairline);background:var(--surface-2);border-radius:999px;padding:4px 10px;font-size:11px;cursor:pointer;color:var(--ink)">Todos</button>';
    var chips = S.chips.map(function(c){
      var sel = S.selected === c.slug
        ? 'border-color:var(--accent);color:var(--ink);font-weight:600'
        : 'border-color:var(--hairline);color:var(--ink-muted)';
      return '<button data-cslug="' + esc(c.slug) + '" style="border:1px solid;' + sel + ';background:var(--surface-2);border-radius:999px;padding:4px 10px;font-size:11px;cursor:pointer">' + esc(c.name) + ' · ' + Math.round(c.progress || 0) + '%</button>';
    }).join('');
    var legend = '<span style="font-size:10px;color:var(--ink-muted)">legenda: ' +
      '<span style="color:#22c55e">done</span> · <span style="color:#eab308">doing</span> · ' +
      '<span style="color:#ef4444">blocked</span> · <span style="color:#94a3b8">backlog</span>' +
      ' — clique no chip para destacar</span>';
    el.innerHTML = all + chips + legend;
    el.querySelectorAll('[data-cslug]').forEach(function(b){
      b.onclick = function(){ selectCanvasFilter(b.getAttribute('data-cslug')); };
    });
  }

  function labelMatches(label, name){
    if (!label || !name) return false;
    return label.indexOf(name) === 0 || name.indexOf(label) === 0;
  }

  function selectCanvasFilter(slug){
    S.userChoice = true;
    S.selected = slug === '__all__' ? null : slug;
    renderChips(document.getElementById('canvas-chips'));
    // Filtro server-side: re-renderiza o canvas com só o subgraph do projeto
    // (sem arestas órfãs de outros projetos — o hack de display:none foi removido).
    var url = S.selected ? '/api/canvas?project=' + encodeURIComponent(S.selected) : '/api/canvas';
    fetch(url).then(function(r){ return r.json(); }).then(function(d){
      if (!d || !d.mermaid){ return; }
      renderCanvasMermaid(d.mermaid, d.age || '');
    }).catch(function(){});
  }

  // Re-render do mermaid (filtro por projeto / Todos). Robusto: limpa o
  // conteúdo anterior antes, usa id único, e captura erro de render.
  function renderCanvasMermaid(mermaidSrc, ageText){
    var el = document.getElementById('mermaid-render');
    var age = document.getElementById('canvas-age');
    if (!el) return;
    el.innerHTML = '<div style="color:var(--ink-muted);text-align:center;padding:2rem">renderizando canvas...</div>';
    var id = 'mmd-' + Date.now() + '-' + Math.floor(Math.random() * 1e6);
    mermaid.render(id, mermaidSrc).then(function(res){
      el.innerHTML = res.svg;
      var s = el.querySelector('svg');
      if (s && s.viewBox && s.viewBox.baseVal && s.viewBox.baseVal.width > 0){
        s.style.width = s.viewBox.baseVal.width + 'px';
        s.style.height = s.viewBox.baseVal.height + 'px';
        s.style.maxWidth = 'none';
      }
      // re-registra os handlers de clique nos nós (sem re-carregar chips)
      el.querySelectorAll('.node').forEach(function(n){
        n.style.cursor = 'pointer';
        n.onclick = function(e){ handleCanvasClick(e); };
      });
      if (age && ageText !== undefined) age.textContent = ageText;
      if (typeof resetCanvasState === 'function') resetCanvasState();
      if (typeof setupCanvasStage === 'function') setupCanvasStage();
      setTimeout(function(){ if (typeof fitCanvas === 'function') fitCanvas(); }, 60);
    }).catch(function(err){
      el.innerHTML = '<div style="color:#ef4444;text-align:center;padding:2rem">Erro ao renderizar canvas: ' +
        (err && err.message ? esc(err.message.slice(0, 120)) : 'desconhecido') + '</div>';
    });
  }

  function addCanvasCrossLink(e){
    var target = e.target.closest('.node');
    if (!target) return;
    var cluster = target.closest('g.cluster');
    if (!cluster) return;
    var label = clusterLabel(cluster);
    var chip = null;
    for (var i = 0; i < S.chips.length; i++){
      if (labelMatches(label, S.chips[i].name)){ chip = S.chips[i]; break; }
    }
    if (!chip) return;
    var panel = document.getElementById('canvas-detail');
    if (!panel || panel.querySelector('.pm-canvas-link')) return;
    var btn = document.createElement('button');
    btn.className = 'btn-primary pm-canvas-link';
    btn.style.cssText = 'margin-top:10px;font-size:12px;padding:6px 12px';
    btn.textContent = '🗂️ ver painel do projeto';
    btn.onclick = function(){ gotoProjectCanvas(chip.slug); };
    panel.appendChild(btn);
  }

  function gotoProjectCanvas(slug){
    if (window.showProjects) showProjects();
    if (window.selectPMProject) setTimeout(function(){ selectPMProject(slug); }, 50);
  }

  window.setupCanvasExtras = setupCanvasExtras;
  window.selectCanvasFilter = selectCanvasFilter;
  window.gotoProjectCanvas = gotoProjectCanvas;
})();
