/* Prometheus Memory — Aba Projetos (Fase A)
   Kanban read-only + timeline + progresso + presença em tempo real.
   Consome /api/pm/* (window.fetch já injeta Bearer e abre login em 401). */
(function(){
  'use strict';

  const S = {
    projects: [],
    selected: null,
    events: [],
    presence: [],
    timer: null,
    active: false
  };

  const esc = (s) => {
    if (typeof window.escapeHtml === 'function') return window.escapeHtml(s);
    return String(s == null ? '' : s).replace(/[&<>"'`\\]/g, (c) => ({
      '&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;','`':'&#96;','\\':'&#92;'
    }[c]));
  };

  const TYPE_COLOR = {
    plan: '#94a3b8', decision: '#5e6ad2', implementation: '#22c55e',
    issue: '#ef4444', issue_resolved: '#22c55e', skill_created: '#0ea5e9',
    research: '#0ea5e9', note: '#94a3b8'
  };

  const STATUS_COLOR = {
    active: '#22c55e', idle: '#eab308', stale: '#6b7280', closed: '#374151'
  };

  function timeAgo(iso){
    if(!iso) return '';
    const t = new Date(iso.replace(' ', 'T')).getTime();
    if(isNaN(t)) return '';
    const s = Math.floor((Date.now() - t) / 1000);
    if(s < 60) return 'agora';
    if(s < 3600) return `há ${Math.floor(s/60)}min`;
    if(s < 86400) return `há ${Math.floor(s/3600)}h`;
    return `há ${Math.floor(s/86400)}d`;
  }

  function typeChip(t){
    const c = TYPE_COLOR[t] || '#94a3b8';
    return `<span style="font-size:10px;font-weight:600;color:${c};background:${c}1a;border:1px solid ${c}40;border-radius:999px;padding:2px 8px">${esc(t)}</span>`;
  }

  // ── Boards (sidebar) ────────────────────────────────────────────────
  function loadPMBoards(){
    S.active = true;
    fetch('/api/pm/projects').then(r => r.json()).then(d => {
      S.projects = d.projects || [];
      renderSidebar();
      if(!S.selected || !S.projects.some(p => p.slug === S.selected)){
        if(S.projects.length) selectPMProject(S.projects[0].slug);
      }
    }).catch(()=>{
      document.getElementById('projects-list').innerHTML = '<div style="color:#ef4444;font-size:12px">erro ao carregar projetos</div>';
    });
  }

  function renderSidebar(){
    const list = document.getElementById('projects-list');
    const stats = document.getElementById('projects-stats');
    if(!list || !stats) return;
    if(!S.projects.length){
      list.innerHTML = '<div style="color:var(--ink-muted);font-size:12px">Sem projetos ainda — registre um evento em /api/pm/events</div>';
      stats.innerHTML = '<div style="font-size:12px">0 projetos</div>';
      return;
    }
    const totalActive = S.projects.reduce((a,p)=>a+(p.active_sessions||0),0);
    stats.innerHTML = `<div style="font-size:12px">${S.projects.length} projetos · ${totalActive} sessões ativas</div>`;
    list.innerHTML = S.projects.map(p => {
      const sel = S.selected === p.slug ? 'background:var(--surface-2);border-color:var(--hairline-strong)' : 'background:transparent;border-color:transparent';
      const act = (p.active_sessions||0) > 0 ? `<span style="color:#22c55e;font-size:11px">● ${p.active_sessions} ativa(s)</span>` : '<span style="color:var(--ink-muted);font-size:11px">○ inativo</span>';
      const prog = Math.round(p.progress || 0);
      return `<div data-slug="${esc(p.slug)}" class="pm-board" style="cursor:pointer;border:1px solid;border-radius:var(--radius-md);padding:10px 12px;margin-bottom:8px;${sel}">
        <div style="display:flex;justify-content:space-between;align-items:center;gap:8px">
          <span style="font-weight:600;color:var(--ink);font-size:13px">${esc(p.name || p.slug)}</span>
          ${act}
        </div>
        <div style="height:5px;background:var(--surface-2);border-radius:999px;margin-top:8px;overflow:hidden">
          <div style="height:100%;width:${prog}%;background:var(--accent);border-radius:999px;transition:width .4s var(--ease-out)"></div>
        </div>
        <div style="font-size:11px;color:var(--ink-muted);margin-top:4px">${prog}% concluído</div>
      </div>`;
    }).join('');
  }

  // ── Projeto selecionado ─────────────────────────────────────────────
  function selectPMProject(slug){
    S.selected = slug;
    fetch('/api/pm/projects/' + encodeURIComponent(slug) + '/report').then(r => r.ok ? r.json() : null).then(rep => {
      fetch('/api/pm/projects/' + encodeURIComponent(slug) + '/events').then(r => r.json()).then(d => {
        S.events = d.events || [];
        renderDetail(rep, S.events);
        loadPMBoardsPresence();
        document.getElementById('projects-empty').style.display = 'none';
        document.getElementById('projects-detail').style.display = 'block';
        renderSidebar();
      });
    }).catch(()=>{});
  }

  function loadPMBoardsPresence(){
    fetch('/api/pm/presence?project=' + encodeURIComponent(S.selected)).then(r => r.json()).then(d => {
      S.presence = d.sessions || [];
      const el = document.getElementById('pm-presence');
      if(el) el.innerHTML = renderPresence();
    }).catch(()=>{});
  }

  function renderPresence(){
    const active = S.presence.filter(s => s.status === 'active');
    const idle = S.presence.filter(s => s.status === 'idle');
    const stale = S.presence.filter(s => s.status === 'stale');
    if(!S.presence.length) return '<span style="color:var(--ink-muted);font-size:12px">Nenhuma sessão ativa agora</span>';
    const chips = S.presence.map(s =>
      `<span style="display:inline-flex;align-items:center;gap:6px;background:var(--surface-2);border:1px solid var(--hairline);border-radius:999px;padding:3px 10px;font-size:12px;color:var(--ink);margin:0 4px 4px 0">
        <span style="width:8px;height:8px;border-radius:50%;background:${STATUS_COLOR[s.status]||'#6b7280'}"></span>
        ${esc(s.harness)} · ${esc(s.agent_id||'?')}
        ${s.current_action ? `<span style="color:var(--ink-muted);font-size:11px">— ${esc(s.current_action)}</span>` : ''}
      </span>`).join('');
    return `<div style="font-size:12px;color:var(--ink-muted);margin-bottom:6px">${active.length} sessão(ões) ativa(s) agora${idle.length ? ' · ' + idle.length + ' idle' : ''}${stale.length ? ' · ' + stale.length + ' stale' : ''}</div>${chips}`;
  }

  function renderDetail(rep, events){
    const slug = S.selected;
    const prog = rep && rep.progress != null ? Math.round(rep.progress) : 0;
    const active = rep && rep.active_sessions != null ? rep.active_sessions : 0;
    const kpi = (label, val) =>
      `<div style="flex:1;min-width:150px;background:var(--surface-1);border:1px solid var(--hairline);border-radius:var(--radius-md);padding:10px 14px">
        <div style="font-size:11px;color:var(--ink-muted);text-transform:uppercase;letter-spacing:.04em">${esc(label)}</div>
        <div style="font-size:15px;font-weight:600;color:var(--ink);margin-top:2px;overflow-wrap:anywhere">${esc(val == null || val === '' ? '—' : val)}</div>
      </div>`;

    document.getElementById('projects-detail').innerHTML = `
      <div style="display:flex;justify-content:space-between;align-items:center;gap:12px;flex-wrap:wrap;margin-bottom:16px">
        <h2 style="font-size:20px;font-weight:600;color:var(--ink)">🗂️ ${esc(slug)}</h2>
        <span style="font-size:12px;color:var(--ink-muted)">relatório atualizado ${timeAgo(rep && rep.updated_at)}</span>
      </div>

      <div style="background:var(--surface-1);border:1px solid var(--hairline);border-radius:var(--radius-md);padding:14px 16px;margin-bottom:14px">
        <div style="display:flex;justify-content:space-between;font-size:12px;color:var(--ink-muted);margin-bottom:6px">
          <span>${esc(rep ? rep.summary : '')}</span><span style="font-weight:600;color:var(--ink)">${prog}%</span>
        </div>
        <div style="height:8px;background:var(--surface-2);border-radius:999px;overflow:hidden">
          <div style="height:100%;width:${prog}%;background:var(--accent);border-radius:999px;transition:width .5s var(--ease-out)"></div>
        </div>
      </div>

      <div id="pm-presence" style="background:var(--surface-1);border:1px solid var(--hairline);border-radius:var(--radius-md);padding:12px 16px;margin-bottom:14px"></div>

      <div style="display:flex;gap:10px;flex-wrap:wrap;margin-bottom:18px">
        ${kpi('Eventos', events.length)}
        ${kpi('Issues abertas', rep ? rep.open_issues : 0)}
        ${kpi('Última decisão', rep ? rep.last_decision : '')}
        ${kpi('Última implementação', rep ? rep.last_implementation : '')}
      </div>

      <div id="pm-stack" style="margin-bottom:18px"></div>
      <div id="pm-connections" style="margin-bottom:18px"></div>

      <h3 style="font-size:13px;font-weight:600;color:var(--ink-muted);text-transform:uppercase;letter-spacing:.05em;margin-bottom:10px">Kanban</h3>
      <div id="pm-kanban" style="display:grid;grid-template-columns:repeat(3,1fr);gap:12px;margin-bottom:20px">${renderKanban(events)}</div>

      <h3 style="font-size:13px;font-weight:600;color:var(--ink-muted);text-transform:uppercase;letter-spacing:.05em;margin-bottom:10px">Timeline</h3>
      <div style="background:var(--surface-1);border:1px solid var(--hairline);border-radius:var(--radius-md);padding:14px 16px;overflow-x:auto">
        ${renderTimeline(events)}
      </div>`;
  loadPMStack(slug);
  loadPMConnections(slug);
  }

  function kanbanCol(title, items, color){
    return `<div style="background:var(--surface-1);border:1px solid var(--hairline);border-radius:var(--radius-md);padding:12px">
      <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:10px">
        <span style="font-size:12px;font-weight:600;color:var(--ink)">${esc(title)}</span>
        <span style="font-size:11px;color:${color};font-weight:600">${items.length}</span>
      </div>
      <div style="min-height:60px">${items.length ? items.map(cardHTML).join('') : '<div style="color:var(--ink-muted);font-size:12px;padding:8px 0">vazio</div>'}</div>
    </div>`;
  }

  function cardHTML(ev){
    const blocked = ev.status_hint === 'blocked';
    const border = blocked ? '1px solid #ef4444' : '1px solid var(--hairline)';
    return `<div onclick="openPMDrawer('${esc(ev.id)}')" style="cursor:pointer;background:var(--surface-2);border:${border};border-radius:var(--radius-md);padding:10px 12px;margin-bottom:8px;transition:transform .12s var(--ease-out);transform:scale(1)">
      <div style="display:flex;justify-content:space-between;align-items:center;gap:6px;margin-bottom:6px">
        ${typeChip(ev.event_type)}
        ${blocked ? '<span style="font-size:10px;font-weight:700;color:#ef4444">BLOQUEADO</span>' : ''}
      </div>
      <div style="font-size:13px;color:var(--ink);font-weight:500;line-height:1.35;overflow-wrap:anywhere">${esc(ev.title)}</div>
      <div style="display:flex;justify-content:space-between;font-size:11px;color:var(--ink-muted);margin-top:6px">
        <span>${esc(ev.harness || '')}${ev.agent_id ? ' · ' + esc(ev.agent_id) : ''}</span>
        <span>${timeAgo(ev.created_at)}</span>
      </div>
    </div>`;
  }

  function renderKanban(events){
    const todo = [], doing = [], done = [];
    events.forEach(ev => {
      const st = ev.status_hint || '';
      if(st === 'done' || st === 'resolved') done.push(ev);
      else if(st === 'doing' || st === 'blocked') doing.push(ev);
      else todo.push(ev);
    });
    return kanbanCol('Backlog', todo, 'var(--ink-muted)')
      + kanbanCol('Em andamento', doing, '#eab308')
      + kanbanCol('Concluído', done, '#22c55e');
  }

  function renderTimeline(events){
    if(!events.length) return '<div style="color:var(--ink-muted);font-size:12px">Sem eventos ainda</div>';
    const items = events.slice().reverse().map(ev => {
      const c = TYPE_COLOR[ev.event_type] || '#94a3b8';
      return `<div style="display:flex;flex-direction:column;align-items:center;min-width:130px;max-width:150px;padding:0 8px;position:relative">
        <div style="width:12px;height:12px;border-radius:50%;background:${c};box-shadow:0 0 0 3px ${c}22;margin-bottom:8px"></div>
        <div style="font-size:11px;font-weight:600;color:var(--ink);text-align:center;overflow-wrap:anywhere">${esc(ev.title)}</div>
        <div style="font-size:10px;color:var(--ink-muted);margin-top:3px;text-align:center">${timeAgo(ev.created_at)}</div>
      </div>`;
    }).join('');
    return `<div style="display:flex;gap:4px;align-items:flex-start;min-width:max-content">${items}</div>`;
  }

  // ── Drawer de detalhes ──────────────────────────────────────────────
  function openPMDrawer(eventId){
    const ev = S.events.find(e => e.id === eventId);
    if(!ev) return;
    const drawer = document.getElementById('projects-drawer');
    const body = document.getElementById('projects-drawer-body');
    body.innerHTML = `
      <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:12px">
        <span style="font-size:12px;font-weight:600;color:var(--ink-muted);text-transform:uppercase;letter-spacing:.05em">Detalhes do evento</span>
        <button onclick="closePMDrawer()" style="background:none;border:none;color:var(--ink-muted);font-size:16px;cursor:pointer;transform:scale(1)">✕</button>
      </div>
      <div style="margin-bottom:10px">${typeChip(ev.event_type)}</div>
      <h3 style="font-size:15px;font-weight:600;color:var(--ink);margin-bottom:8px">${esc(ev.title)}</h3>
      ${ev.summary ? `<p style="font-size:13px;color:var(--ink-muted);line-height:1.5;white-space:pre-wrap;margin-bottom:12px">${esc(ev.summary)}</p>` : ''}
      <div id="pm-drawer-memory" style="font-size:13px;color:var(--ink);line-height:1.6;white-space:pre-wrap"></div>
      <div style="border-top:1px solid var(--hairline);margin-top:12px;padding-top:10px;font-size:12px;color:var(--ink-muted);line-height:1.9">
        <div>Status: <b style="color:var(--ink)">${esc(ev.status_hint || '—')}</b></div>
        <div>Harness: <b style="color:var(--ink)">${esc(ev.harness || '—')}</b></div>
        <div>Agente: <b style="color:var(--ink)">${esc(ev.agent_id || '—')}</b></div>
        <div>Sessão: <b style="color:var(--ink)">${esc(ev.session_key || '—')}</b></div>
        <div>Data: <b style="color:var(--ink)">${esc(ev.created_at || '—')}</b></div>
        ${ev.memory_id ? `<div>Memória: <b style="color:var(--ink)">${esc(ev.memory_id)}</b></div>` : ''}
      </div>`;
    drawer.style.width = '320px';
    drawer.setAttribute('aria-hidden', 'false');
    if(ev.memory_id){
      fetch('/api/memory/' + encodeURIComponent(ev.memory_id)).then(r => r.ok ? r.json() : null).then(m => {
        if(m && m.content){
          document.getElementById('pm-drawer-memory').innerHTML =
            `<div style="background:var(--canvas);border:1px solid var(--hairline);border-radius:var(--radius-md);padding:10px;margin-bottom:10px;font-size:12px;color:var(--ink-muted);text-transform:uppercase;letter-spacing:.04em">Memória canônica</div>` +
            `<div style="background:var(--canvas);border:1px solid var(--hairline);border-radius:var(--radius-md);padding:12px;font-size:13px;color:var(--ink);line-height:1.6;white-space:pre-wrap;max-height:220px;overflow-y:auto">${esc(m.content)}</div>`;
        }
      }).catch(()=>{});
    }
  }

  function closePMDrawer(){
    const drawer = document.getElementById('projects-drawer');
    drawer.style.width = '0';
    drawer.setAttribute('aria-hidden', 'true');
  }

  // ── Stack & Runtime (Fase A3) ──────────────────────────────────────
  const LANG_COLOR = {
    'Python':'#3572A5','TypeScript':'#3178c6','JavaScript':'#f1e05a','HTML':'#e34c26',
    'CSS':'#563d7c','SCSS':'#c6538c','Shell':'#89e051','SQL':'#e38c00','Go':'#00ADD8',
    'Rust':'#dea584','Java':'#b07219','Ruby':'#701516','PHP':'#4F5D95','C':'#555555',
    'C++':'#f34b7d','Vue':'#41b883','Svelte':'#ff3e00','Astro':'#ff5d01'
  };

  function loadPMStack(slug){
    const el = document.getElementById('pm-stack');
    if(!el) return;
    el.innerHTML = '<div style="color:var(--ink-muted);font-size:12px">carregando stack...</div>';
    fetch('/api/pm/projects/' + encodeURIComponent(slug) + '/stack').then(r => {
      if(r.status === 404) return null;
      return r.json();
    }).then(prof => {
      if(!prof) renderStackEmpty(el, slug);
      else renderStack(el, prof);
    }).catch(() => renderStackEmpty(el, slug));
  }

  function scanPMStack(slug){
    const el = document.getElementById('pm-stack');
    el.innerHTML = '<div style="color:var(--ink-muted);font-size:12px">analisando...</div>';
    fetch('/api/pm/projects/' + encodeURIComponent(slug) + '/stack/scan', {method: 'POST'})
      .then(r => r.json()).then(prof => renderStack(el, prof)).catch(() => {});
  }

  function renderStackEmpty(el, slug){
    el.innerHTML = `
      <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:10px">
        <h3 style="font-size:13px;font-weight:600;color:var(--ink-muted);text-transform:uppercase;letter-spacing:.05em">🧱 Stack & Runtime</h3>
        <button data-pm-action="scan-stack" data-slug="${esc(slug)}" class="btn-primary" style="font-size:11px;padding:5px 10px">Analisar stack</button>
      </div>
      <div style="background:var(--surface-1);border:1px solid var(--hairline);border-radius:var(--radius-md);padding:14px 16px;color:var(--ink-muted);font-size:13px">
        Nenhuma análise ainda — clique em "Analisar stack" para detectar linguagens, frameworks, DBs, containers e git.
      </div>`;
  }

  function renderStack(el, prof){
    const langs = prof.languages || [];
    const totalBars = langs.map(l => `<div style="flex:${l.percent};background:${LANG_COLOR[l.language] || '#94a3b8'}" title="${esc(l.language)} ${l.percent}%"></div>`).join('') || '<div style="flex:1;background:var(--surface-2)"></div>';
    const legend = langs.map(l => `<span style="display:inline-flex;align-items:center;gap:5px;font-size:11px;color:var(--ink-muted);margin:0 10px 4px 0">
      <span style="width:9px;height:9px;border-radius:2px;background:${LANG_COLOR[l.language] || '#94a3b8'}"></span>${esc(l.language)} ${l.percent}%</span>`).join('') || '<span style="font-size:11px;color:var(--ink-muted)">sem código detectado</span>';
    const docsKb = Math.round((prof.docs_bytes || 0) / 1024);
    const cfgKb = Math.round((prof.config_bytes || 0) / 1024);
    const frameworks = (prof.frameworks || []).map(f => `<span style="display:inline-block;background:var(--surface-2);border:1px solid var(--hairline);border-radius:999px;padding:3px 10px;font-size:12px;color:var(--ink);margin:0 4px 4px 0">${esc(f.name)}${f.version ? ' <span style="color:var(--ink-muted);font-size:11px">'+esc(f.version)+'</span>' : ''}</span>`).join('') || '<span style="color:var(--ink-muted);font-size:12px">—</span>';
    const dbs = (prof.databases || []).map(db => `<span style="display:inline-block;background:#0ea5e91a;border:1px solid #0ea5e940;border-radius:999px;padding:3px 10px;font-size:12px;color:#0ea5e9;margin:0 4px 4px 0">🗄 ${esc(db)}</span>`).join('') || '<span style="color:var(--ink-muted);font-size:12px">—</span>';
    const containers = (prof.containers || []).map(c => `<div style="display:flex;justify-content:space-between;gap:10px;padding:6px 0;border-bottom:1px solid var(--hairline);font-size:12px">
      <span style="color:var(--ink);font-weight:500">🐳 ${esc(c.name)}</span>
      <span style="color:var(--ink-muted)">${esc(c.status)}</span>
      <span style="color:var(--ink-muted);font-family:var(--font-mono)">${esc(c.ports)}</span>
    </div>`).join('') || '<div style="color:var(--ink-muted);font-size:12px;padding:4px 0">nenhum container detectado</div>';
    const git = prof.git || {};
    const gitBlock = git.tracked ? `
      <div style="display:flex;gap:8px;flex-wrap:wrap;margin-bottom:6px">
        <span style="background:var(--surface-2);border:1px solid var(--hairline);border-radius:999px;padding:3px 10px;font-size:12px;color:var(--ink)">🌿 ${esc(git.branch || '?')}</span>
        ${git.remote ? `<span style="background:var(--surface-2);border:1px solid var(--hairline);border-radius:999px;padding:3px 10px;font-size:12px;color:var(--ink-muted)">${esc(git.remote)}</span>` : ''}
        ${git.dirty_count > 0 ? `<span style="background:#eab3081a;border:1px solid #eab30840;border-radius:999px;padding:3px 10px;font-size:12px;color:#eab308;font-weight:600">dirty (${git.dirty_count})</span>` : '<span style="background:#22c55e1a;border:1px solid #22c55e40;border-radius:999px;padding:3px 10px;font-size:12px;color:#22c55e">clean</span>'}
      </div>
      <div style="font-size:12px;color:var(--ink-muted);line-height:1.7">${(git.commits || []).map(c => esc(c)).join('<br>')}</div>`
      : `<div style="background:#ef44441a;border:1px solid #ef444440;color:#ef4444;border-radius:var(--radius-md);padding:8px 12px;font-size:12px;font-weight:600">⚠ Não versionado (sem repo git local)</div>`;

    el.innerHTML = `
      <div style="display:flex;justify-content:space-between;align-items:center;gap:10px;flex-wrap:wrap;margin-bottom:10px">
        <h3 style="font-size:13px;font-weight:600;color:var(--ink-muted);text-transform:uppercase;letter-spacing:.05em">🧱 Stack & Runtime</h3>
        <span style="font-size:11px;color:var(--ink-muted)">análise ${prof.scan_duration_ms ? prof.scan_duration_ms + 'ms' : ''}${prof.analyzed_at ? ' · ' + timeAgo(prof.analyzed_at) : ''}</span>
        <button data-pm-action="scan-stack" data-slug="${esc(prof.project_slug || S.selected)}" class="btn-secondary" style="font-size:11px;padding:5px 10px">Re-scan</button>
      </div>
      <div style="background:var(--surface-1);border:1px solid var(--hairline);border-radius:var(--radius-md);padding:14px 16px;margin-bottom:12px">
        <div style="display:flex;height:10px;border-radius:999px;overflow:hidden;margin-bottom:8px">${totalBars}</div>
        <div>${legend}</div>
        <div style="font-size:11px;color:var(--ink-muted);margin-top:6px">docs: ${docsKb} KB · config: ${cfgKb} KB (fora do % de código)</div>
      </div>
      <div style="display:grid;grid-template-columns:1fr 1fr;gap:12px;margin-bottom:12px">
        <div style="background:var(--surface-1);border:1px solid var(--hairline);border-radius:var(--radius-md);padding:12px 14px">
          <div style="font-size:11px;color:var(--ink-muted);text-transform:uppercase;letter-spacing:.04em;margin-bottom:8px">Frameworks</div>
          <div>${frameworks}</div>
        </div>
        <div style="background:var(--surface-1);border:1px solid var(--hairline);border-radius:var(--radius-md);padding:12px 14px">
          <div style="font-size:11px;color:var(--ink-muted);text-transform:uppercase;letter-spacing:.04em;margin-bottom:8px">Bancos de dados</div>
          <div>${dbs}</div>
        </div>
      </div>
      <div style="background:var(--surface-1);border:1px solid var(--hairline);border-radius:var(--radius-md);padding:12px 14px;margin-bottom:12px">
        <div style="font-size:11px;color:var(--ink-muted);text-transform:uppercase;letter-spacing:.04em;margin-bottom:6px">Containers (runtime)</div>
        ${containers}
      </div>
      <div style="background:var(--surface-1);border:1px solid var(--hairline);border-radius:var(--radius-md);padding:12px 14px">
        <div style="font-size:11px;color:var(--ink-muted);text-transform:uppercase;letter-spacing:.04em;margin-bottom:6px">Git</div>
        ${gitBlock}
      </div>`;
  }

  // ── Conexões & Custos (Fase A2) ────────────────────────────────────
  function loadPMConnections(slug){
    const el = document.getElementById('pm-connections');
    if(!el) return;
    el.innerHTML = '<div style="color:var(--ink-muted);font-size:12px">carregando conexões...</div>';
    Promise.all([
      fetch('/api/pm/projects/' + encodeURIComponent(slug) + '/connections').then(r => r.json()).catch(() => ({connections: [], alerts: []})),
      fetch('/api/pm/connections/summary').then(r => r.json()).catch(() => ({}))
    ]).then(([data, summ]) => {
      S.connections = data.connections || [];
      renderConnections(el, slug, S.connections, data.alerts || [], summ || {});
    });
  }

  const CONN_FIELD = (id, ph, w) => `<input id="${id}" placeholder="${esc(ph)}" style="width:${w||'100%'};background:var(--canvas);border:1px solid var(--hairline);border-radius:var(--radius-md);padding:7px 10px;font-size:12px;color:var(--ink);outline:none">`;

  function billingBadge(t){
    const map = {subscription:['#eab308','assinatura'], paygo:['#0ea5e9','paygo'], free:['#6b7280','grátis'], unknown:['#6b7280','?']};
    const [c, label] = map[t] || map.unknown;
    return `<span style="font-size:10px;font-weight:600;color:${c};background:${c}1a;border:1px solid ${c}40;border-radius:999px;padding:2px 8px">${label}</span>`;
  }

  function connAlertBadges(id, alerts){
    const a = alerts.filter(x => x.id === id);
    if(!a.length) return '';
    const color = {error:'#ef4444', warn:'#eab308', info:'#0ea5e9'};
    return a.map(x => `<div style="font-size:10px;font-weight:600;color:${color[x.level]||'#0ea5e9'};margin-top:4px">⚠ ${esc(x.text)}</div>`).join('');
  }

  function renderConnections(el, slug, conns, alerts, summ){
    const rows = conns.map(c => `<tr style="border-bottom:1px solid var(--hairline)">
      <td style="padding:8px 6px;font-size:13px;color:var(--ink);font-weight:500">${esc(c.name)}</td>
      <td style="padding:8px 6px;font-size:12px;color:var(--ink-muted)">${esc(c.provider || '—')}</td>
      <td style="padding:8px 6px;font-size:12px;color:var(--ink-muted);font-family:var(--font-mono)">${esc(c.masked || '—')}</td>
      <td style="padding:8px 6px">${billingBadge(c.billing_type)}</td>
      <td style="padding:8px 6px;font-size:12px;color:var(--ink)">${c.cost_usd_month != null ? '$' + Number(c.cost_usd_month).toFixed(2) + '/mês' : '—'}</td>
      <td style="padding:8px 6px;font-size:12px;color:var(--ink-muted)">${esc(c.expires_at || '—')}</td>
      <td style="padding:8px 6px;font-size:11px">${connAlertBadges(c.id, alerts)}</td>
      <td style="padding:8px 6px"><button onclick="editPMConnection('${esc(c.id)}')" style="background:none;border:1px solid var(--hairline);border-radius:var(--radius-sm);color:var(--ink-muted);font-size:11px;cursor:pointer;padding:3px 8px">✏️</button></td>
    </tr>`).join('') || '<tr><td colspan="8" style="padding:10px 6px;font-size:12px;color:var(--ink-muted)">Nenhuma conexão registrada — use "Re-scan .env"</td></tr>';

    el.innerHTML = `
      <div style="display:flex;justify-content:space-between;align-items:center;gap:10px;flex-wrap:wrap;margin-bottom:10px">
        <h3 style="font-size:13px;font-weight:600;color:var(--ink-muted);text-transform:uppercase;letter-spacing:.05em">🔑 Conexões & Custos</h3>
        <div style="display:flex;gap:8px;align-items:center;flex-wrap:wrap">
          <span style="font-size:12px;color:var(--ink-muted)">Total: <b style="color:var(--ink)">${summ.total_cost_usd_month != null ? '$' + Number(summ.total_cost_usd_month).toFixed(2) + '/mês' : '—'}</b></span>
          ${(summ.unused_keys || 0) > 0 ? `<span style="font-size:11px;color:#ef4444;font-weight:600">${summ.unused_keys} sem uso</span>` : ''}
          ${(summ.expiring_keys || 0) > 0 ? `<span style="font-size:11px;color:#eab308;font-weight:600">${summ.expiring_keys} expirando</span>` : ''}
          <button data-pm-action="scan-conn" data-slug="${esc(slug)}" class="btn-secondary" style="font-size:11px;padding:5px 10px">Re-scan .env</button>
          <button onclick="togglePMConnForm()" class="btn-primary" style="font-size:11px;padding:5px 10px">➕</button>
        </div>
      </div>
      <div id="pm-conn-form" style="display:none;background:var(--surface-1);border:1px solid var(--hairline);border-radius:var(--radius-md);padding:12px;margin-bottom:10px">
        <div style="display:grid;grid-template-columns:1fr 1fr;gap:8px;margin-bottom:8px">
          ${CONN_FIELD('conn-name', 'nome (ex: DEEPSEEK_API_KEY)')}
          ${CONN_FIELD('conn-provider', 'provedor (ex: DeepSeek)')}
        </div>
        <div style="display:grid;grid-template-columns:1fr 1fr 1fr;gap:8px;margin-bottom:8px">
          ${CONN_FIELD('conn-cost', 'custo $/mês')}
          ${CONN_FIELD('conn-expires', 'expira (YYYY-MM-DD)')}
          <select id="conn-billing" style="background:var(--canvas);border:1px solid var(--hairline);border-radius:var(--radius-md);padding:7px 10px;font-size:12px;color:var(--ink);outline:none">
            <option value="subscription">assinatura</option><option value="paygo">paygo</option>
            <option value="free">grátis</option><option value="unknown">desconhecido</option>
          </select>
        </div>
        <div style="display:flex;gap:8px">
          ${CONN_FIELD('conn-notes', 'notas')}
          <button data-pm-action="create-conn" data-slug="${esc(slug)}" class="btn-primary" style="font-size:12px;white-space:nowrap">Salvar</button>
          <button onclick="togglePMConnForm()" class="btn-secondary" style="font-size:12px">Cancelar</button>
        </div>
      </div>
      <div id="pm-conn-edit" style="display:none;background:var(--surface-1);border:1px solid var(--hairline);border-radius:var(--radius-md);padding:12px;margin-bottom:10px"></div>
      <div style="background:var(--surface-1);border:1px solid var(--hairline);border-radius:var(--radius-md);overflow:auto">
        <table style="width:100%;border-collapse:collapse;min-width:760px">${rows}</table>
      </div>`;
  }

  function scanPMConnections(slug){
    fetch('/api/pm/projects/' + encodeURIComponent(slug) + '/connections/scan', {method: 'POST'})
      .then(r => r.json()).then(() => loadPMConnections(slug)).catch(() => {});
  }

  function togglePMConnForm(){
    const f = document.getElementById('pm-conn-form');
    f.style.display = f.style.display === 'none' ? 'block' : 'none';
  }

  function createPMConnection(slug){
    const body = {
      project_slug: slug,
      name: document.getElementById('conn-name').value.trim(),
      provider: document.getElementById('conn-provider').value.trim(),
      billing_type: document.getElementById('conn-billing').value,
      cost_usd_month: document.getElementById('conn-cost').value || null,
      expires_at: document.getElementById('conn-expires').value.trim(),
      notes: document.getElementById('conn-notes').value.trim()
    };
    if(!body.name) return;
    fetch('/api/pm/connections', {method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify(body)})
      .then(r => r.json()).then(() => { togglePMConnForm(); loadPMConnections(slug); }).catch(() => {});
  }

  function editPMConnection(cid){
    const c = (S.connections || []).find(x => x.id === cid);
    if(!c) return;
    const ed = document.getElementById('pm-conn-edit');
    ed.style.display = 'block';
    ed.innerHTML = `
      <div style="font-size:12px;font-weight:600;color:var(--ink);margin-bottom:8px">✏️ ${esc(c.name)}</div>
      <div style="display:grid;grid-template-columns:1fr 1fr 1fr;gap:8px;margin-bottom:8px">
        <select id="edit-billing" style="background:var(--canvas);border:1px solid var(--hairline);border-radius:var(--radius-md);padding:7px 10px;font-size:12px;color:var(--ink);outline:none">
          ${['subscription','paygo','free','unknown'].map(t => `<option value="${t}" ${c.billing_type === t ? 'selected' : ''}>${t}</option>`).join('')}
        </select>
        ${CONN_FIELD('edit-cost', 'custo $/mês', '100%').replace('>', ` value="${esc(c.cost_usd_month != null ? c.cost_usd_month : '')}">`)}
        ${CONN_FIELD('edit-expires', 'expira (YYYY-MM-DD)', '100%').replace('>', ` value="${esc(c.expires_at || '')}">`)}
      </div>
      <div style="display:flex;gap:8px">
        ${CONN_FIELD('edit-status', 'status (active|unused|expired|revoked)', '100%').replace('>', ` value="${esc(c.status || 'active')}">`)}
        ${CONN_FIELD('edit-last', 'último uso (YYYY-MM-DD HH:MM:SS)', '100%').replace('>', ` value="${esc(c.last_used_at || '')}">`)}
        <button onclick="savePMConnection('${esc(cid)}')" class="btn-primary" style="font-size:12px;white-space:nowrap">Salvar</button>
        <button onclick="cancelPMConnEdit()" class="btn-secondary" style="font-size:12px">Cancelar</button>
      </div>`;
  }

  function savePMConnection(cid){
    const body = {
      billing_type: document.getElementById('edit-billing').value,
      cost_usd_month: document.getElementById('edit-cost').value || null,
      expires_at: document.getElementById('edit-expires').value.trim(),
      status: document.getElementById('edit-status').value.trim(),
      last_used_at: document.getElementById('edit-last').value.trim()
    };
    fetch('/api/pm/connections/' + encodeURIComponent(cid), {method: 'PUT', headers: {'Content-Type': 'application/json'}, body: JSON.stringify(body)})
      .then(r => r.json()).then(() => { cancelPMConnEdit(); loadPMConnections(S.selected); }).catch(() => {});
  }

  function cancelPMConnEdit(){
    document.getElementById('pm-conn-edit').style.display = 'none';
  }

  // ── Presença em tempo real (polling 10s) ───────────────────────────
  function loadPresenceLoop(){
    if(S.timer) return;
    S.timer = setInterval(() => {
      if(currentView === 'projects' && S.selected) loadPMBoardsPresence();
    }, 10000);
  }

  function clearPMPolling(){
    if(S.timer){ clearInterval(S.timer); S.timer = null; }
  }

  document.addEventListener('DOMContentLoaded', function(){
    const list = document.getElementById('projects-list');
    if(list){
      list.addEventListener('click', function(e){
        const card = e.target.closest('.pm-board');
        if(card && card.dataset.slug) selectPMProject(card.dataset.slug);
      });
    }
    document.addEventListener('click', function(e){
      const t = e.target.closest('[data-pm-action]');
      if(!t) return;
      const slug = t.getAttribute('data-slug');
      const action = t.getAttribute('data-pm-action');
      if(action === 'scan-stack') scanPMStack(slug);
      else if(action === 'scan-conn') scanPMConnections(slug);
      else if(action === 'create-conn') createPMConnection(slug);
    });
  });

  window.loadPMBoards = loadPMBoards;
  window.selectPMProject = selectPMProject;
  window.openPMDrawer = openPMDrawer;
  window.closePMDrawer = closePMDrawer;
  window.loadPresenceLoop = loadPresenceLoop;
  window.loadPMBoardsPresence = loadPMBoardsPresence;
  window.clearPMPolling = clearPMPolling;
  window.loadPMConnections = loadPMConnections;
  window.loadPMStack = loadPMStack;
  window.scanPMStack = scanPMStack;
  window.scanPMConnections = scanPMConnections;
  window.togglePMConnForm = togglePMConnForm;
  window.createPMConnection = createPMConnection;
  window.editPMConnection = editPMConnection;
  window.savePMConnection = savePMConnection;
  window.cancelPMConnEdit = cancelPMConnEdit;
  window.PMState = S;
})();
