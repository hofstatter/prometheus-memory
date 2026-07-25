# ARCHITECTURE — Prometheus Memory

## Visão Geral

Prometheus Memory é um add-on para o Mnemosyne que implementa memória
hierárquica **L0→L3** com compressão simbólica (Mermaid Canvas), offloading
de logs, geração automática de skills e RAG local multimodal.

## Componentes

### 1. Pipeline L0→L3 (`scripts/`)

| Script | Camada | Função |
|---|---|---|
| `session_logger.py` | L0 | Captura sessões do agente como Markdown |
| `memory_aggregator.py` | L1→L2 | Agrupa fatos em cenas temáticas via LLM + gera Canvas Mermaid |
| `persona_synthesizer.py` | L2→L3 | Sintetiza cenas em perfil de persona via LLM |
| `skill_generator.py` | L2→Skills | Detecta padrões recorrentes (3+ ocorrências) → skills |
| `ref_manager.py` | Offloading | Salva outputs grandes (>500 chars) em `refs/*.md` com node_id |

**Fluxo de dados:**

```
Sessão do agente
   │ (auto-memory skill, durante a sessão)
   ▼
mnemosyne remember → L1 fatos (working memory)
   │ (cron a cada 6h)
   ▼
memory_aggregator → L2 cenas (episodic) + canvas.mmd
   │ (cron semanal)
   ▼
persona_synthesizer → L3 persona (importance 0.95) + persona.md
   │
   ▼
skill_generator → ~/.opencode/skills/generated/*.md
```

### 2. Web UI (`web/`)

Flask single-page app, porta 8777 (configurável). Sem build step: Tailwind
via CDN, Alpine.js, HTMX, G6.js (grafo), Mermaid.js (canvas).

| Arquivo | Função |
|---|---|
| `app.py` | Rotas principais: Timeline, Grafo, Canvas, Search, Stats, Memory detail |
| `rag_engine.py` | Engine RAG: chunking (langchain), embeddings (fastembed, 384d multilíngue), OCR (PyMuPDF + Tesseract) |
| `rag_routes.py` | Blueprint `/api/rag`: upload, busca, coleções, documentos |
| `notes_routes.py` | Blueprint `/api/notes`: import por URL, sanitização, CRUD, busca |
| `editor_routes.py` | Blueprint `/api/memory`: update/delete de memórias |
| `templates/index.html` | SPA com 5 abas + editor modal |

**Comunicação com o Mnemosyne:** a UI lê o banco SQLite diretamente
(detalhes de memória) e usa o CLI `mnemosyne` via subprocess para
recall/stats/update/delete. O RAG usa tabelas próprias (`rag_collections`,
`rag_documents`, `rag_chunks`) no mesmo banco SQLite, com sqlite-vec
disponível e busca por similaridade de cosseno (numpy).

### 3. Skill auto-memory (`skills/auto-memory/`)

Instruções carregadas pelo agente em toda sessão:
1. **Início:** recall de contexto relevante
2. **Durante:** gravação automática de decisões/implementações (L1)
3. **Offloading:** outputs >500 chars → `ref_manager.py`
4. **Fim:** resumo consolidado + `session_logger.py` (L0)

## Decisões de Design

| Decisão | Motivo |
|---|---|
| Sem build step no frontend | Simplicidade de deploy e contribuição |
| SQLite compartilhado com Mnemosyne | Zero infra extra; backup único |
| CLI do Mnemosyne via subprocess | Desacoplamento de versões da API Python |
| Embeddings locais (MiniLM-L12 multilíngue) | R$ 0, privacidade, PT-BR nativo |
| DeepSeek para síntese L2/L3 | Melhor custo-benefício (~$0.01/sessão) |
| Fallbacks sem LLM | Pipeline funciona (degradado) sem API key |
| Cron em vez de daemon | Simplicidade; systemd só para a Web UI |

## Segurança

- Bind `127.0.0.1` por padrão (`PROMETHEUS_HOST` para alterar)
- Path traversal: `note_id` resolvido e validado dentro de `NOTES_DIR`
- SSRF: import de URLs só aceita http/https com resolução pública
  (bloqueia loopback, privados, link-local, reservados)
- Upload: allowlist de extensões + limite de 50MB
- XSS: escape de HTML em todos os pontos de renderização dinâmica;
  Mermaid com `securityLevel: 'strict'`
- Secrets: exclusivamente via variáveis de ambiente

## Diretórios em runtime

```
~/.hermes/mnemosyne/          # MNEMOSYNE_HOME
├── data/mnemosyne.db         # Banco SQLite (memórias + RAG)
├── canvas.mmd                # Canvas Mermaid atual
├── persona.md                # Persona L3 atual
├── refs/YYYY-MM-DD/*.md      # Logs offloaded
└── uploads/                  # Staging de uploads (auto-limpo)

~/notes/                      # PROMETHEUS_NOTES_DIR
├── github/  kimi/  x/  web/  # Notas por fonte

~/.opencode/skills/
├── auto-memory/SKILL.md      # Skill instalada
└── generated/*.md            # Skills auto-geradas
```
