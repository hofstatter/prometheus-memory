/* Prometheus Memory — i18n (EN/PT/ES/ZH)
   Auto-detecta navegador · seletor 🌐 · ?lang= · MutationObserver.
   Substituição por substring (chaves mais longas primeiro) + padrões dinâmicos. */
(function(){
  const T = {
    // nav + busca
    'Buscar memórias...': {en:'Search memories...', es:'Buscar memorias...', zh:'搜索记忆...'},
    'Todas as coleções': {en:'All collections', es:'Todas las colecciones', zh:'所有集合'},
    'Todas': {en:'All', es:'Todas', zh:'全部'},
    'Todos': {en:'All', es:'Todos', zh:'全部'},
    '📐 Canvas': {en:'📐 Canvas', es:'📐 Lienzo', zh:'📐 画布'},
    '📄 RAG': {en:'📄 RAG', es:'📄 RAG', zh:'📄 检索增强'},
    // projetos comuns (dados — traduzidos so no sidebar/grafo, nunca no conteudo)
    'default': {en:'default', es:'predeterminado', zh:'默认'},
    'geral': {en:'general', es:'general', zh:'通用'},
    // canvas (acoes geradas pelo aggregator)
    'buscar': {en:'search', es:'buscar', zh:'搜索'},
    'extrair': {en:'extract', es:'extraer', zh:'提取'},
    'varrer': {en:'scan', es:'escanear', zh:'扫描'},
    'processar': {en:'process', es:'procesar', zh:'处理'},
    'Concluido': {en:'Done', es:'Completado', zh:'已完成'},
    'Nenhuma atividade recente': {en:'No recent activity', es:'Sin actividad reciente', zh:'暂无近期活动'},
    'Conteúdo offloaded não encontrado': {en:'Offloaded content not found', es:'Contenido offloaded no encontrado', zh:'未找到卸载内容'},
    'Start': {en:'Start', es:'Inicio', zh:'开始'},
    'Idle': {en:'Idle', es:'Inactivo', zh:'空闲'},
    '📋 Timeline': {en:'📋 Timeline', es:'📋 Timeline', zh:'📋 时间线'},
    '🕸️ Grafo': {en:'🕸️ Graph', es:'🕸️ Grafo', zh:'🕸️ 图谱'},
    '📐 Canvas — Fluxo do Agente': {en:'📐 Canvas — Agent Flow', es:'📐 Canvas — Flujo del Agente', zh:'📐 画布 — 智能体流程'},
    '📄 RAG — Documentos': {en:'📄 RAG — Documents', es:'📄 RAG — Documentos', zh:'📄 检索增强 — 文档'},
    '📝 Notes — Captura Inteligente': {en:'📝 Notes — Smart Capture', es:'📝 Notas — Captura Inteligente', zh:'📝 笔记 — 智能捕获'},
    '📝 Notes': {en:'📝 Notes', es:'📝 Notas', zh:'📝 笔记'},
    // sidebar
    '📂 Projetos': {en:'📂 Projects', es:'📂 Proyectos', zh:'📂 项目'},
    '📁 Coleções': {en:'📁 Collections', es:'📁 Colecciones', zh:'📁 集合'},
    '📅 Documentos Recentes': {en:'📅 Recent Documents', es:'📅 Documentos Recientes', zh:'📅 最近文档'},
    '📂 Temas': {en:'📂 Topics', es:'📂 Temas', zh:'📂 主题'},
    '📁 Temas': {en:'📁 Topics', es:'📁 Temas', zh:'📁 主题'},
    '📅 Datas': {en:'📅 Dates', es:'📅 Fechas', zh:'📅 日期'},
    '📊 Stats': {en:'📊 Stats', es:'📊 Estadísticas', zh:'📊 统计'},
    '📑 Biblioteca': {en:'📑 Library', es:'📑 Biblioteca', zh:'📑 库'},
    'Projetos:': {en:'Projects:', es:'Proyectos:', zh:'项目：'},
    'Esta semana:': {en:'This week:', es:'Esta semana:', zh:'本周：'},
    'Total:': {en:'Total:', es:'Total:', zh:'总计：'},
    'Docs:': {en:'Docs:', es:'Docs:', zh:'文档：'},
    'Chunks:': {en:'Chunks:', es:'Chunks:', zh:'块：'},
    'Notas:': {en:'Notes:', es:'Notas:', zh:'笔记：'},
    'Temas:': {en:'Topics:', es:'Temas:', zh:'主题：'},
    // unidades: so em contadores/estatisticas, nunca no conteudo das memorias
    'memórias': {en:'memories', es:'memorias', zh:'条记忆'},
    'notas': {en:'notes', es:'notas', zh:'条笔记'},
    'docs': {en:'docs', es:'docs', zh:'个文档'},
    'carregando...': {en:'loading...', es:'cargando...', zh:'加载中...'},
    'Carregando memórias...': {en:'Loading memories...', es:'Cargando memorias...', zh:'正在加载记忆...'},
    'sem data': {en:'no date', es:'sin fecha', zh:'无日期'},
    // canvas
    'atualizado agora': {en:'updated now', es:'actualizado ahora', zh:'刚刚更新'},
    'Canvas indisponível': {en:'Canvas unavailable', es:'Canvas no disponible', zh:'画布不可用'},
    'Scroll = zoom · Clique nos nós = detalhes': {en:'Scroll = zoom · Click nodes = details', es:'Scroll = zoom · Clic en nodos = detalles', zh:'滚轮 = 缩放 · 点击节点 = 详情'},
    // grafo
    '🔍 Centralizar': {en:'🔍 Center', es:'🔍 Centrar', zh:'🔍 居中'},
    '⏸️ Physics': {en:'⏸️ Physics', es:'⏸️ Física', zh:'⏸️ 物理模拟'},
    'G6 não carregou': {en:'G6 failed to load', es:'G6 no se cargó', zh:'G6 加载失败'},
    'Detalhes': {en:'Details', es:'Detalles', zh:'详情'},
    'Clique em um nó para ver detalhes.': {en:'Click a node to see details.', es:'Haz clic en un nodo para ver detalles.', zh:'点击节点查看详情。'},
    '✏️ Editar memória': {en:'✏️ Edit memory', es:'✏️ Editar memoria', zh:'✏️ 编辑记忆'},
    // RAG
    'Buscar nos documentos...': {en:'Search documents...', es:'Buscar en documentos...', zh:'搜索文档...'},
    'ou arraste um arquivo aqui': {en:'or drag a file here', es:'o arrastra un archivo aquí', zh:'或拖放文件到此处'},
    'Nova coleção': {en:'New collection', es:'Nueva colección', zh:'新建集合'},
    // notes
    '📥 Importar': {en:'📥 Import', es:'📥 Importar', zh:'📥 导入'},
    'Importar': {en:'Import', es:'Importar', zh:'导入'},
    'Buscar nas notas...': {en:'Search notes...', es:'Buscar en notas...', zh:'搜索笔记...'},
    'Cole um link (GitHub, X, Kimi, site...) para importar...': {en:'Paste a link (GitHub, X, Kimi, site...) to import...', es:'Pega un enlace (GitHub, X, Kimi, sitio...) para importar...', zh:'粘贴链接（GitHub、X、Kimi、网站...）进行导入...'},
    // genéricos
    'Buscar': {en:'Search', es:'Buscar', zh:'搜索'},
    'Salvar': {en:'Save', es:'Guardar', zh:'保存'},
    'Cancelar': {en:'Cancel', es:'Cancelar', zh:'取消'},
    'limpar': {en:'clear', es:'limpiar', zh:'清除'},
    '🔍 Filtro:': {en:'🔍 Filter:', es:'🔍 Filtro:', zh:'🔍 筛选：'},
    '💰 Tokens economizados:': {en:'💰 Tokens saved:', es:'💰 Tokens ahorrados:', zh:'💰 已节省 token：'},
    '⚡ Recursos': {en:'⚡ Resources', es:'⚡ Recursos', zh:'⚡ 资源'},
    '· ao vivo': {en:'· live', es:'· en vivo', zh:'· 实时'},
    'indisponível': {en:'unavailable', es:'no disponible', zh:'不可用'},
    'Prometheus:': {en:'Prometheus:', es:'Prometheus:', zh:'Prometheus：'},
    'RAM': {en:'RAM', es:'RAM', zh:'内存'},
    'HD': {en:'Disk', es:'Disco', zh:'磁盘'},
    'GPU': {en:'GPU', es:'GPU', zh:'显卡'},
    'offloading + compressão L0→L3': {en:'offloading + L0→L3 compression', es:'offloading + compresión L0→L3', zh:'卸载 + L0→L3 压缩'},
    // login modal
    'Área protegida — entre com a senha para continuar. A sessão dura 30 dias neste navegador.': {en:'Protected area — enter your password to continue. The session lasts 30 days in this browser.', es:'Área protegida — ingresa tu contraseña para continuar. La sesión dura 30 días en este navegador.', zh:'受保护区域——请输入密码继续。会话在此浏览器中持续 30 天。'},
    'Senha': {en:'Password', es:'Contraseña', zh:'密码'},
    'Entrar': {en:'Sign in', es:'Entrar', zh:'登录'},
    'Sair da sessão?': {en:'Sign out?', es:'¿Cerrar sesión?', zh:'退出登录？'},
  };

  // padrões dinâmicos (regex PT → função por idioma)
  const PATTERNS = [
    {re: /atualizado há (\d+)min/g, en:'updated $1min ago', es:'actualizado hace $1min', zh:'$1 分钟前更新'},
    {re: /atualizado há (\d+)h/g, en:'updated $1h ago', es:'actualizado hace $1h', zh:'$1 小时前更新'},
    {re: /(\d+) memória\b/g, en:'$1 memory', es:'$1 memoria', zh:'$1 条记忆'},
  ];

  // chaves sensiveis: so dentro do Canvas/Mermaid (evita traduzir CONTEUDO das memorias)
  const CANVAS_ONLY = ['buscar','extrair','varrer','processar','Concluido','Nenhuma atividade recente','Start','Idle','Conteúdo offloaded não encontrado'];
  // nomes de projeto: so no sidebar/grafo/badge, nunca no texto das memorias
  const PROJECT_NAMES = ['default','geral'];
  // unidades: so em contadores, nunca no conteudo
  const UNIT_WORDS = ['memórias','notas','docs'];

  const LANGS = ['en','pt','es','zh'];
  const KEYS = Object.keys(T).filter(k=>!CANVAS_ONLY.includes(k) && !PROJECT_NAMES.includes(k) && !UNIT_WORDS.includes(k)).sort((a,b)=>b.length-a.length);
  const CKEYS = CANVAS_ONLY.filter(k=>T[k]).sort((a,b)=>b.length-a.length);
  const ORIG = new WeakMap();

  function inCanvas(node){
    let p = node.parentElement;
    while(p){
      if(p.id === 'canvas-view' || p.id === 'canvas-mermaid' || p.tagName === 'svg' || (p.classList && p.classList.contains('mermaid'))) return true;
      p = p.parentElement;
    }
    return false;
  }

  function inProjectCtx(node){
    let p = node.parentElement;
    while(p){
      if(p.id === 'project-list' || p.id === 'g6-canvas' || p.id === 'rag-sidebar-collections' || (p.classList && p.classList.contains('project-badge'))) return true;
      p = p.parentElement;
    }
    return false;
  }

  function inCounterCtx(node){
    let p = node.parentElement;
    while(p){
      if(p.id && ['memory-count','sidebar-stats','notes-stats','rag-sidebar-stats','sidebar-savings','date-list'].includes(p.id)) return true;
      if(p.classList && (p.classList.contains('timeline-date') || p.classList.contains('count'))) return true;
      p = p.parentElement;
    }
    return false;
  }

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

  function translateText(orig, lang, canvasCtx, projCtx, counterCtx){
    if(lang === 'pt') return orig;
    inProjectCtx._hit = projCtx;
    let out = orig;
    for(const key of KEYS){
      if(out.includes(key)) out = out.split(key).join(tr(key, lang));
    }
    if(counterCtx){
      for(const key of UNIT_WORDS){
        out = out.replace(new RegExp('\\b'+key+'\\b', 'g'), tr(key, lang));
      }
    }
    if(canvasCtx){
      for(const key of CKEYS){
        if(out.includes(key)) out = out.split(key).join(tr(key, lang));
      }
    }
    if(inProjectCtx._hit){
      for(const key of PROJECT_NAMES){
        const re = new RegExp('\\b'+key+'\\b', 'g');
        out = out.replace(re, tr(key, lang));
      }
    }
    for(const p of PATTERNS){
      out = out.replace(p.re, (m, g1)=> (p[lang]||m).replace('$1', g1));
    }
    return out;
  }

  function walk(node, lang){
    if(node.nodeType === 3){
      if(!ORIG.has(node)) ORIG.set(node, node.nodeValue);
      const orig = ORIG.get(node);
      if(!orig.trim()) return;
      const next = translateText(orig, lang, inCanvas(node), inProjectCtx(node), inCounterCtx(node));
      if(next !== node.nodeValue) node.nodeValue = next;
      return;
    }
    if(node.nodeType !== 1) return;
    const el = node;
    ['placeholder','title'].forEach(attr=>{
      if(!el.getAttribute) return;
      const dk = 'orig_'+attr;
      if(!el.dataset[dk] && el.getAttribute(attr)) el.dataset[dk] = el.getAttribute(attr);
      if(el.dataset[dk]) el.setAttribute(attr, translateText(el.dataset[dk], lang, inCanvas(el), inProjectCtx(el), inCounterCtx(el)));
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
