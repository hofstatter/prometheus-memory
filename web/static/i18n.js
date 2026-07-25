/* Prometheus Memory — i18n (EN/PT/ES/ZH)
   Auto-detecta idioma do navegador; troca em runtime via seletor 🌐.
   Fonte das strings: PT-BR (legado); dicionário traduz para os demais. */
(function(){
  const T = {
    'Buscar memórias...': {en:'Search memories...', es:'Buscar memorias...', zh:'搜索记忆...'},
    'Todos': {en:'All', es:'Todos', zh:'全部'},
    '📋 Timeline': {en:'📋 Timeline', es:'📋 Timeline', zh:'📋 时间线'},
    '🕸️ Grafo': {en:'🕸️ Graph', es:'🕸️ Grafo', zh:'🕸️ 图谱'},
    '📐 Canvas': {en:'📐 Canvas', es:'📐 Canvas', zh:'📐 画布'},
    '📄 RAG': {en:'📄 RAG', es:'📄 RAG', zh:'📄 RAG'},
    '📝 Notes': {en:'📝 Notes', es:'📝 Notas', zh:'📝 笔记'},
    'carregando...': {en:'loading...', es:'cargando...', zh:'加载中...'},
    'memórias': {en:'memories', es:'memorias', zh:'条记忆'},
    'notas': {en:'notes', es:'notas', zh:'条笔记'},
    'docs': {en:'docs', es:'docs', zh:'个文档'},
    '📂 PROJETOS': {en:'📂 PROJECTS', es:'📂 PROYECTOS', zh:'📂 项目'},
    '📅 Datas': {en:'📅 Dates', es:'📅 Fechas', zh:'📅 日期'},
    '📊 Stats': {en:'📊 Stats', es:'📊 Estadísticas', zh:'📊 统计'},
    'Total:': {en:'Total:', es:'Total:', zh:'总计：'},
    'Projetos:': {en:'Projects:', es:'Proyectos:', zh:'项目：'},
    'Esta semana:': {en:'This week:', es:'Esta semana:', zh:'本周：'},
    'limpar': {en:'clear', es:'limpiar', zh:'清除'},
    '🔍 Filtro:': {en:'🔍 Filter:', es:'🔍 Filtro:', zh:'🔍 筛选：'},
    'Detalhes': {en:'Details', es:'Detalles', zh:'详情'},
    'Clique em um nó para ver detalhes.': {en:'Click a node to see details.', es:'Haz clic en un nodo para ver detalles.', zh:'点击节点查看详情。'},
    '✏️ Editar memória': {en:'✏️ Edit memory', es:'✏️ Editar memoria', zh:'✏️ 编辑记忆'},
    '🔍 Centralizar': {en:'🔍 Center', es:'🔍 Centrar', zh:'🔍 居中'},
    '⏸️ Physics': {en:'⏸️ Physics', es:'⏸️ Física', zh:'⏸️ 物理模拟'},
    'Canvas — Fluxo do Agente': {en:'Canvas — Agent Flow', es:'Canvas — Flujo del Agente', zh:'画布 — 智能体流程'},
    'Notes — Captura Inteligente': {en:'Notes — Smart Capture', es:'Notas — Captura Inteligente', zh:'笔记 — 智能捕获'},
    'Cole um link (GitHub, X, Kimi, site...) para importar...': {en:'Paste a link (GitHub, X, Kimi, site...) to import...', es:'Pega un enlace (GitHub, X, Kimi, sitio...) para importar...', zh:'粘贴链接（GitHub、X、Kimi、网站...）进行导入...'},
    'Importar': {en:'Import', es:'Importar', zh:'导入'},
    'Buscar nas notas...': {en:'Search notes...', es:'Buscar en notas...', zh:'搜索笔记...'},
    'Buscar': {en:'Search', es:'Buscar', zh:'搜索'},
    '📁 Temas': {en:'📁 Topics', es:'📁 Temas', zh:'📁 主题'},
    'Notas:': {en:'Notes:', es:'Notas:', zh:'笔记：'},
    'Temas:': {en:'Topics:', es:'Temas:', zh:'主题：'},
    'Docs:': {en:'Docs:', es:'Docs:', zh:'文档：'},
    'Chunks:': {en:'Chunks:', es:'Chunks:', zh:'块：'},
    'Área protegida — entre com a senha para continuar. A sessão dura 30 dias neste navegador.': {en:'Protected area — enter your password to continue. The session lasts 30 days in this browser.', es:'Área protegida — ingresa tu contraseña para continuar. La sesión dura 30 días en este navegador.', zh:'受保护区域——请输入密码继续。会话在此浏览器中持续 30 天。'},
    'Senha': {en:'Password', es:'Contraseña', zh:'密码'},
    'Entrar': {en:'Sign in', es:'Entrar', zh:'登录'},
    'Sair da sessão?': {en:'Sign out?', es:'¿Cerrar sesión?', zh:'退出登录？'},
    'Canvas indisponível': {en:'Canvas unavailable', es:'Canvas no disponible', zh:'画布不可用'},
    'G6 não carregou': {en:'G6 failed to load', es:'G6 no se cargó', zh:'G6 加载失败'},
    'Scroll = zoom · Clique nos nós = detalhes': {en:'Scroll = zoom · Click nodes = details', es:'Scroll = zoom · Clic en nodos = detalles', zh:'滚轮 = 缩放 · 点击节点 = 详情'},
    'Nenhuma memória ainda': {en:'No memories yet', es:'Aún no hay memorias', zh:'暂无记忆'},
    'atualizado agora': {en:'updated now', es:'actualizado ahora', zh:'刚刚更新'},
    '💰 Tokens economizados:': {en:'💰 Tokens saved:', es:'💰 Tokens ahorrados:', zh:'💰 已节省 token：'},
    'offloading + compressão L0→L3': {en:'offloading + L0→L3 compression', es:'offloading + compresión L0→L3', zh:'卸载 + L0→L3 压缩'},
    'Nova coleção': {en:'New collection', es:'Nueva colección', zh:'新建集合'},
    'Enviar documento': {en:'Upload document', es:'Subir documento', zh:'上传文档'},
    'Salvar': {en:'Save', es:'Guardar', zh:'保存'},
    'Cancelar': {en:'Cancel', es:'Cancelar', zh:'取消'},
    'sem data': {en:'no date', es:'sin fecha', zh:'无日期'},
  };

  const LANGS = ['en','pt','es','zh'];
  const ORIG = new WeakMap();

  function detect(){
    const url = new URLSearchParams(location.search).get('lang');
    if(url && LANGS.includes(url)){ localStorage.setItem('prometheus_lang', url); return url; }
    const saved = localStorage.getItem('prometheus_lang');
    if(saved && LANGS.includes(saved)) return saved;
    const nav = (navigator.language || 'en').toLowerCase();
    if(nav.startsWith('pt')) return 'pt';
    if(nav.startsWith('es')) return 'es';
    if(nav.startsWith('zh')) return 'zh';
    return 'en';
  }

  function tr(str, lang){
    if(lang === 'pt') return str;
    const hit = T[str];
    return hit && hit[lang] ? hit[lang] : str;
  }

  function walk(node, lang){
    if(node.nodeType === 3){
      const cur = node.nodeValue;
      const key = cur.trim();
      if(!ORIG.has(node)) ORIG.set(node, cur);
      const orig = ORIG.get(node);
      const origKey = orig.trim();
      if(T[origKey]){
        const rep = tr(origKey, lang);
        node.nodeValue = cur.replace(origKey, rep);
      }
      return;
    }
    if(node.nodeType !== 1) return;
    const el = node;
    ['placeholder','title'].forEach(attr=>{
      const v = el.getAttribute && el.getAttribute(attr);
      if(v && T[v.trim()]){
        if(!el.dataset['orig'+attr]) el.dataset['orig'+attr] = v;
        el.setAttribute(attr, tr(el.dataset['orig'+attr].trim(), lang));
      }
    });
    for(const child of el.childNodes) walk(child, lang);
  }

  function applyLang(lang){
    document.documentElement.lang = lang === 'pt' ? 'pt-BR' : lang;
    walk(document.body, lang);
    const sel = document.getElementById('lang-select');
    if(sel) sel.value = lang;
  }

  window.setLang = function(lang){
    if(!LANGS.includes(lang)) return;
    localStorage.setItem('prometheus_lang', lang);
    applyLang(lang);
  };

  const observer = new MutationObserver(muts=>{
    const lang = localStorage.getItem('prometheus_lang') || detect();
    if(lang === 'pt') return;
    muts.forEach(m=>m.addedNodes.forEach(n=>walk(n, lang)));
  });

  document.addEventListener('DOMContentLoaded', ()=>{
    // seletor no nav
    const nav = document.querySelector('nav');
    if(nav && !document.getElementById('lang-select')){
      const sel = document.createElement('select');
      sel.id = 'lang-select';
      sel.className = 'btn-inactive';
      sel.style.cssText = 'padding:4px 8px;font-size:12px;background:var(--surface-2);border:1px solid var(--hairline);border-radius:var(--radius-md);color:var(--ink);cursor:pointer';
      sel.innerHTML = '<option value="en">🌐 EN</option><option value="pt">🌐 PT</option><option value="es">🌐 ES</option><option value="zh">🌐 中文</option>';
      sel.onchange = ()=>window.setLang(sel.value);
      const count = document.getElementById('memory-count');
      nav.insertBefore(sel, count);
    }
    observer.observe(document.body, {childList:true, subtree:true});
    applyLang(detect());
  });
})();
