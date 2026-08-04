/* Canvas v2 — chips de projeto, legenda, highlight de subgraph e cross-link p/ aba Projetos. */
(function(){
  'use strict';
  var S = { chips: [], selected: null, origSet: false };

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
    S.selected = slug === '__all__' ? null : slug;
    renderChips(document.getElementById('canvas-chips'));
    var clusters = document.querySelectorAll('#mermaid-render g.cluster');
    clusters.forEach(function(g){
      if (!S.selected){ g.style.opacity = '1'; return; }
      var label = clusterLabel(g);
      var chip = S.chips.filter(function(c){ return c.slug === S.selected; })[0];
      g.style.opacity = (chip && labelMatches(label, chip.name)) ? '1' : '0.15';
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
