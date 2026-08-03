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

      <h3 style="font-size:13px;font-weight:600;color:var(--ink-muted);text-transform:uppercase;letter-spacing:.05em;margin-bottom:10px">Kanban</h3>
      <div id="pm-kanban" style="display:grid;grid-template-columns:repeat(3,1fr);gap:12px;margin-bottom:20px">${renderKanban(events)}</div>

      <h3 style="font-size:13px;font-weight:600;color:var(--ink-muted);text-transform:uppercase;letter-spacing:.05em;margin-bottom:10px">Timeline</h3>
      <div style="background:var(--surface-1);border:1px solid var(--hairline);border-radius:var(--radius-md);padding:14px 16px;overflow-x:auto">
        ${renderTimeline(events)}
      </div>`;
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
    const c = TYPE_COLOR[ev.event_type] || '#94a3b8';
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
    void c;
  }

  function closePMDrawer(){
    const drawer = document.getElementById('projects-drawer');
    drawer.style.width = '0';
    drawer.setAttribute('aria-hidden', 'true');
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
  });

  window.loadPMBoards = loadPMBoards;
  window.selectPMProject = selectPMProject;
  window.openPMDrawer = openPMDrawer;
  window.closePMDrawer = closePMDrawer;
  window.loadPresenceLoop = loadPresenceLoop;
  window.loadPMBoardsPresence = loadPMBoardsPresence;
  window.clearPMPolling = clearPMPolling;
  window.PMState = S;
})();
