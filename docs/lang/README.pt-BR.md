# ⚡ Prometheus Memory

> 🌐 [English](../../README.md) · **Português** · [Español](README.es.md) · [中文](README.zh-CN.md)

> Pipeline de memória L0→L3 para Agentes IA.
> Transforma conversas brutas em personas, skills e diagramas.
> Baseado em [Mnemosyne](https://github.com/abdiasrj/mnemosyne) (BEAM) + arquitetura inspirada no TencentDB-Agent-Memory (pirâmide L0→L3).

[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](../../LICENSE)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/)
[![Mnemosyne 3.12+](https://img.shields.io/badge/mnemosyne-3.12+-blueviolet.svg)](https://github.com/abdiasrj/mnemosyne)

🌐 [English](../../README.md) | **Português** | [中文](README.zh-CN.md)

## Por que "Prometheus"

Na mitologia grega, Prometheus é filho de Mnemosyne (deusa da memória) — e é o
titã que trouxe o **fogo do conhecimento** aos humanos. O Mnemosyne armazena
(memória); o Prometheus transforma dados brutos em **conhecimento acionável**
(persona, skills, diagramas).

## 🧠 O Segundo Cérebro dos seus Agentes

**Um cérebro, vários agentes.** O Prometheus Memory funciona como um
**segundo cérebro compartilhado** entre todos os seus agentes de IA.
OpenCode, Claude Code, Cursor, Codex e agentes customizados leem e gravam na
**mesma memória** via MCP. Uma decisão tomada pelo agente A de manhã está
disponível para o agente B à tarde — nada se perde entre sessões, ferramentas
ou máquinas.

### 🔁 Feito para Loop-Agents

Projetado para **agentes em loop contínuo** (triage diário, monitoramento,
automações 24/7): cada iteração do loop recupera o que as anteriores
aprenderam (`mnemosyne recall`) e grava novos fatos ao final
(`mnemosyne remember`). O pipeline L0→L3 consolida tudo automaticamente —
a cada 6h os fatos viram cenas, semanalmente viram persona e skills. O agente
literalmente **fica mais inteligente a cada ciclo**, sem intervenção humana.

## Casos de Uso

- 🔁 **Loop-agents 24/7** — triage diário, monitores de X/Twitter, watchers que aprendem a cada execução
- 🤝 **Times multi-agente** — contexto compartilhado entre agentes com papéis diferentes
- 📅 **Projetos longos** — dezenas de sessões, zero perda de contexto
- 🛠️ **Múltiplas ferramentas de IA** — uma camada de memória para toda a stack

## Features

- 🔍 **Timeline hierárquica** — L3→L2→L1 com drill-down, sidebar de projetos/datas/stats
- 🕸️ **Grafo de conhecimento** — G6.js d3-force estilo Obsidian: glow, hover-activate, clique → detalhes
- 📐 **Mermaid Canvas** — diagrama de estado do agente gerado automaticamente, zoom, clique → conteúdo offloaded; **v2: multi-projeto** (um bloco por projeto com o fluxo de eventos Backlog→Doing→Done, chips de projeto, legenda e link para a aba Projetos)
- 📄 **RAG local multimodal** — upload de PDF, TXT, MD, DOCX, PNG, JPG com OCR automático (Tesseract), busca vetorial
- 📝 **Notes** — importação por URL (GitHub, X/Twitter, sites) com sanitização e renderizador Markdown próprio
- ✏️ **Editor inline** — edição e exclusão de memórias direto na UI (7 abas + editor modal)
- 💾 **Offloading de logs** — outputs grandes de ferramentas viram refs (até 61% de redução de tokens)
- ⚡ **Monitor de recursos ao vivo** — barras de GPU/RAM/HD em tempo real + consumo do processo na sidebar da Timeline (atualiza a cada 3s)
- 🧠 **Skill generation** — detecta padrões recorrentes nas cenas e gera skills reutilizáveis
- 🗂️ **Aba Projetos (v0.2)** — painel operacional por projeto: kanban, timeline, barra de progresso e **presença de agentes em tempo real** (active/idle/stale via heartbeat), com lanes `sess:*`/`proj:*`/`agent:*` e `/api/pm/*` (idempotência por `client_event_id`, Project Resolver com confidence)
- 🔑 **Conexões & Custos (v0.2)** — chaves API/MCPs/assinaturas por projeto: scan read-only do `.env` (fingerprint SHA-256, **valor nunca armazenado/exposto**), alertas "pago e sem uso"/"expirando", chave compartilhada, resumo de custo mensal global
- 🧱 **Stack & Runtime (v0.2)** — barra de linguagens estilo GitHub (por bytes, docs/config separados), frameworks (monorepo-aware), bancos (compose/DATABASE_URL), containers e git (branch/commits/dirty ou "não versionado")
- 🧩 **Skills por projeto (v0.2)** — Skill Builder detecta padrões nos eventos → **draft** com evidências → aprovação humana → `active` → candidata a global
- 🧬 **Padrões Mem0 V3 (v0.2)** — extração LLM single-pass com grounding temporal ("hoje/ontem" → datas absolutas), dedup SHA-256 scoped por channel, linking de entidades e threshold no recall
- 🎨 Dark mode, responsivo, zero build step (sem node_modules)

## Arquitetura

```
┌─────────────────────────────────────────────────────┐
│              Prometheus Web UI (:8777)               │
│  Timeline │ Grafo │ Canvas │ Documents │ Notes │ Skills │ Projetos │ ✏️  │
└─────────────────────────────────────────────────────┘
                          │
          ┌───────────────┼───────────────┐
          ▼               ▼               ▼
 ┌─────────────┐  ┌─────────────┐  ┌─────────────┐
 │ L3 Persona  │  │ L2 Scenes   │  │ L0 Sessions │
 │ (semanal)   │  │ (a cada 6h) │  │ (fim sessão)│
 └─────────────┘  └─────────────┘  └─────────────┘
                          │
                     ┌────▼────┐
                     │   L1    │
                     │  Fatos  │
                     │(auto-mem)│
                     └────┬────┘
                          │
               ┌──────────▼──────────┐
               │    Mnemosyne 3.12+  │
               │  SQLite + sqlite-vec│
               │  FTS5 + BEAM        │
               └─────────────────────┘
```

Detalhes completos em [ARCHITECTURE.md](../../ARCHITECTURE.md).

## Quick Start

### Pré-requisitos

- Python 3.10+
- Linux com systemd (para serviço 24/7 — opcional)
- DeepSeek API key (para consolidação L2/L3)
- Tesseract OCR (opcional, para PDFs escaneados e imagens)

### Instalação (1 comando)

```bash
git clone https://github.com/hofstatter/prometheus-memory.git
cd prometheus-memory
python setup.py          # universal: Windows / macOS / Linux / Raspberry Pi
# ou: bash setup.sh      (wrapper Unix)
```

O instalador detecta seu SO/arquitetura, pergunta o **idioma** (en/pt/es/zh),
instala dependências e registra a Web UI por plataforma (systemd no Linux,
launchd no macOS, instruções de Task Scheduler no Windows).

### Plataformas suportadas

| Plataforma | Status |
|---|---|
| Linux x86_64 | ✅ |
| Linux ARM64 / Raspberry Pi 5 | ✅ |
| macOS (Intel + Apple Silicon) | ✅ |
| Windows 10/11 (x64) | ✅ |

### Idiomas da UI 🌐

A Web UI detecta automaticamente o idioma do navegador — **English, Português,
Español e 中文** — e troca a qualquer momento pelo seletor 🌐 na barra superior
(persiste por navegador). Defina `PROMETHEUS_LANG` no `.env` para forçar um padrão. (A aba RAG aparece como 检索增强 em chinês.)

Depois configure suas chaves:

```bash
nano ~/prometheus-memory/.env   # DEEPSEEK_API_KEY obrigatória
systemctl --user restart prometheus-web
```

Acesse: **http://localhost:8777**

### Instalação manual

```bash
pip install "mnemosyne-memory[all]>=3.12"
pip install -r requirements.txt
cp .env.example .env   # edite com suas chaves
set -a; . ./.env; set +a
python3 web/app.py     # http://localhost:8777
```

## Configuração

Todas as opções são variáveis de ambiente — ver [.env.example](../../.env.example):

| Variável | Padrão | Função |
|---|---|---|
| `DEEPSEEK_API_KEY` | — | **Obrigatória** p/ L2/L3 (cenas, persona, skills) |
| `PROMETHEUS_HOST` | `127.0.0.1` | Bind da Web UI (use `0.0.0.0` p/ LAN, por sua conta) |
| `PROMETHEUS_PORT` | `8777` | Porta da Web UI |
| `MNEMOSYNE_HOME` | `~/.hermes/mnemosyne` | Diretório de dados do Mnemosyne |
| `PROMETHEUS_NOTES_DIR` | `~/notes` | Diretório das notas |
| `PROMETHEUS_USER` | `$USER` | Nome usado nas memórias de persona |
| `PROMETHEUS_PROJECT` | `geral` | Projeto padrão das memórias |
| `PROMETHEUS_PASSWORD` | — | **Senha do login da UI** (obrigatória quando bind ≠ localhost) |
| `PROMETHEUS_TOKEN` | — | Token Bearer da API p/ agentes/scripts |
| `PROMETHEUS_PROTECT_READS` | `false` | `true` = UI inteira exige login |
| `PROMETHEUS_PROJECTS` | — | Projetos conhecidos (vírgula) |
| `PROMETHEUS_EXCLUDE` | — | Conteúdos a excluir da UI (vírgula) |
| `FIRECRAWL_API_KEY` | — | Fallback de scraping (opcional) |

## Pipeline L0→L3

| Camada | Script | Frequência | Output |
|---|---|---|---|
| **L0** Sessions | `scripts/session_logger.py` | Fim de cada sessão | Markdown por sessão |
| **L1** Fatos | skill `auto-memory` | Durante a sessão | `mnemosyne remember` |
| **L2** Cenas | `scripts/memory_aggregator.py` | Cron a cada 6h | Cenas temáticas + Canvas |
| **L3** Persona | `scripts/persona_synthesizer.py` | Cron semanal | `persona.md` + L3 facts |
| **Skills** | `scripts/skill_generator.py` | Semanal (junto L3) | Skills em `~/.opencode/skills/generated/` |
| **Offloading** | `scripts/ref_manager.py` | Sob demanda | `refs/*.md` com node_id |

## Segurança

- Bind padrão em `127.0.0.1` (sem exposição de rede)
- **Login**: quando `PROMETHEUS_HOST != 127.0.0.1`, a UI pede a `PROMETHEUS_PASSWORD` uma vez por navegador (modal) e emite sessão HMAC de 30 dias. Endpoint de login com rate limit (5 tentativas/min/IP — até a senha correta aguarda na janela)
- **Token da API**: agentes/scripts usam `Authorization: Bearer $PROMETHEUS_TOKEN` em vez do login
- **Escopos**: padrão protege só escritas (leituras abertas); `PROMETHEUS_PROTECT_READS=true` protege a API inteira (o HTML da página fica público para o modal renderizar)
- **Single-user, store compartilhado**: sem isolamento por agente (trust boundary = máquina local). Multi-tenant na v0.2
- Proteção contra path traversal nos endpoints de Notes
- Proteção SSRF na importação de URLs, revalidada a cada redirect
- XSS: IDs de coleção sanitizados, code blocks escapados, headers CSP estritos
- Nenhuma chave no código — tudo via variáveis de ambiente
- Sanitização de HTML/JS na renderização (XSS)

## Memória Multi-Agente (isolamento)

Cada agente tem um canal de memória isolado (`agent-<id>`) — memórias não vazam entre agentes:

```bash
# escrever (isolado por agente)
curl -X POST localhost:8777/api/memory/remember -H "Authorization: Bearer $TOKEN" \
  -d '{"agent_id": "atlas", "content": "atlas prefere python assíncrono"}'
# recall (atlas vê só as memórias do atlas)
curl -X POST localhost:8777/api/memory/recall -H "Authorization: Bearer $TOKEN" \
  -d '{"agent_id": "atlas", "query": "python"}'
# listar agentes com memória
curl localhost:8777/api/agents -H "Authorization: Bearer $TOKEN"
```

Contexto compartilhado? Use `agent_id: ""` (canal padrão).

## Skill Registry (Camada 1 — privada)

O Prometheus é também um **registry privado de skills** — sua "oficina" onde você cria, edita e itera skills pela UI, e qualquer IDE (OpenCode, Cursor, VSCode) sincroniza dele:

```bash
# inserir skill via API
curl -X POST localhost:8777/api/skills -H "Authorization: Bearer $TOKEN" \
  -d '{"name":"minha-skill","content":"# Minha Skill\nconteúdo"}'
# sincronizar p/ IDEs
prometheus-skills sync            # OpenCode (~/.config/opencode/skills/)
prometheus-skills sync --ide cursor
prometheus-skills list
```

- **Camada 1 (privada):** skills suas, editáveis pela UI (aba 🧩 Skills), só você escreve
- **UI da aba 🧩 Skills:** sidebar esquerda (lista de skills, 📅 datas, 📊 stats) + visualizador de conteúdo com download raw e delete
- **Camada 2 (pública/GitHub):** publicar com `prometheus-skills publish <name>` quando estiver pronta
- **Contribuição externa:** via Pull Request no repo (você aprova o merge)

### Skill `ai-company` (16 analistas sêniors + pipeline de desenvolvimento)

Incluída no registry e em `skills/ai-company/`: 16 analistas sêniors que conduzem o usuário pelo pipeline **PRD (entrevista grill-me com checkpointing) → aprovação → Tech Spec (Frontend, Backend, Banco de Dados) → Design Review → validação → Sprints → validação → entrega**, com gates de aprovação humanos. Templates: `PRD.md`, `TECH_SPEC.md`, `SPRINT.md`, `VALIDATION.md`. Instalada globalmente no OpenCode (`~/.config/opencode/skills/ai-company/`) — funciona em todos os projetos e sessões.

**Skills embutidas:**

| Arquivo | O que é | Crédito |
|---|---|---|
| `design/super-designer/` | **Autoridade única de design** — 20 mandamentos, 46 anti-padrões, 35 checks preflight, 3 dials (VARIANCE/MOTION/DENSITY). Toda UI passa por um gate de Design Review obrigatório | baseada em emilkowalski/skills, impeccable.style, tasteskill.dev |
| `GRILL.md` | Entrevista implacável do PRD (1 pergunta por vez) + **checkpointing por resposta** em `brainstorms/` | mattpocock/skills |
| `VIRAL.md` | 31 Princípios de um Produto Viral — bússola de launch, **brand lane only** (landing/pricing/marketing) | Marc Lou |
| `REVENUE.md` | Revenue-Centric Design — 101 princípios de conversão/pricing/churn. **Licença: atribuição, proibido gambling** | @richardrx (heliocosta-dev) |
| `design/emil-design-eng.md` | Apêndice de referência — animação, gestos, clip-path, toasts, performance, a11y. **Em divergência, super-designer vence** | emilkowalski |

**Hierarquia de decisão:** super-designer (visual/UX) > VIRAL (copy/estrutura de landing) > REVENUE (estratégia de receita). **Lane rules:** product lane (dashboards/apps) = super-designer sozinha; brand lane (landing/pricing) = super-designer + VIRAL + REVENUE.

## Integrações

Funciona com qualquer agente compatível com MCP — **uma memória compartilhada para todas as suas ferramentas**:

```
OpenCode ─┐
Claude Code ─┼──► Mnemosyne MCP (:8765) ──► Prometheus Memory (mesmo store)
Cursor ─────┤        ▲
Codex CLI ──┘   REST API (:8777) — /api/context/briefing, /api/memory/*
```

### Setup por ferramenta

| Ferramenta | Setup |
|---|---|
| **OpenCode** | Nativo — copie a skill incluída: `cp -r skills/auto-memory ~/.opencode/skills/` |
| **Claude Code** | `claude mcp add mnemosyne --transport sse http://localhost:8765/sse` |
| **Cursor** | `.cursor/mcp.json` → `{"mcpServers": {"prometheus": {"url": "http://localhost:8765/sse"}}}` |
| **Codex CLI** | `~/.codex/config.toml` → `[mcp_servers.mnemosyne]` `url = "http://localhost:8765/sse"` |
| **Qualquer agente** | REST: `GET /api/context/briefing` (início de sessão, ~500 tokens) + CLI/MCP do Mnemosyne p/ escritas |

Uma decisão tomada pelo agente A de manhã fica disponível para o agente B à tarde — ferramentas diferentes, mesma memória.

## Economia de Tokens

O Prometheus foi feito para **reduzir gasto de tokens**, não só guardar memórias:

| Mecanismo | Como economiza |
|---|---|
| **Offloading** (`scripts/ref_manager.py`) | Outputs grandes (>500 chars) viram refs `[ref:id]` — até **61% de redução de tokens** no contexto |
| **Compressão L0→L3** | Fatos crus consolidam em cenas e persona — cada recall injeta ~40 tokens a menos por fato consolidado |
| **Context Briefing** | `GET /api/context/briefing` retorna resumo comprimido de ~500 tokens (persona + cenas + fatos) — inicie cada sessão com contexto máximo a custo mínimo |
| **Medidor de economia** | `GET /api/stats/savings` estima o total economizado (bytes offloaded ÷ 4 + compressão) e mostra um card 💰 na sidebar da UI |

## Comparação

Ver [COMPARISON.md](../../COMPARISON.md) — Mnemosyne vs MemPalace vs TencentDB vs Prometheus.

## Autor

**Herbert Hofstatter** — [@hofstatter](https://github.com/hofstatter) · [X @hofstatter](https://x.com/hofstatter)

## Licença

MIT — ver [LICENSE](../../LICENSE) e [NOTICE](../../NOTICE).
