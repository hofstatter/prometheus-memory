# ⚡ Prometheus Memory

> Pipeline de memória L0→L3 para Agentes IA.
> Transforma conversas brutas em personas, skills e diagramas.
> Baseado em [Mnemosyne](https://github.com/abdiasrj/mnemosyne) (BEAM) + arquitetura inspirada no TencentDB-Agent-Memory (pirâmide L0→L3).

[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](../../LICENSE)
[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/)
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
- 📐 **Mermaid Canvas** — diagrama de estado do agente gerado automaticamente, zoom, clique → conteúdo offloaded
- 📄 **RAG local multimodal** — upload de PDF, TXT, MD, DOCX, PNG, JPG com OCR automático (Tesseract), busca vetorial
- 📝 **Notes** — importação por URL (GitHub, X/Twitter, sites) com sanitização e renderizador Markdown próprio
- ✏️ **Editor inline** — edição e exclusão de memórias direto na UI
- 💾 **Offloading de logs** — outputs grandes de ferramentas viram refs (até 61% de redução de tokens)
- 🧠 **Skill generation** — detecta padrões recorrentes nas cenas e gera skills reutilizáveis
- 🎨 Dark mode, responsivo, zero build step (sem node_modules)

## Arquitetura

```
┌─────────────────────────────────────────────────────┐
│              Prometheus Web UI (:8777)               │
│  Timeline │ Grafo │ Canvas │ Documents │ Notes │ ✏️  │
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

- Python 3.9+
- Linux com systemd (para serviço 24/7 — opcional)
- DeepSeek API key (para consolidação L2/L3)
- Tesseract OCR (opcional, para PDFs escaneados e imagens)

### Instalação (1 comando)

```bash
git clone https://github.com/hofstatter/prometheus-memory.git
cd prometheus-memory
bash setup.sh
```

O `setup.sh` instala dependências, copia os scripts do pipeline, instala a
skill auto-memory, cria cron jobs e ativa o serviço systemd da Web UI.

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
- Proteção contra path traversal nos endpoints de Notes
- Proteção SSRF na importação de URLs (só http/https públicos)
- Nenhuma chave no código — tudo via variáveis de ambiente
- Sanitização de HTML/JS na renderização (XSS)

## Integrações

Funciona com qualquer agente compatível com MCP:

- **OpenCode** (nativo — skill `auto-memory` incluída)
- **Claude Code**, **Cursor**, **Codex CLI** (via MCP do Mnemosyne)

## Comparação

Ver [COMPARISON.md](../../COMPARISON.md) — Mnemosyne vs MemPalace vs TencentDB vs Prometheus.

## Autor

**Herbert Hofstatter** — [@hofstatter](https://github.com/hofstatter) · [X @hofstatter](https://x.com/hofstatter)

## Licença

MIT — ver [LICENSE](../../LICENSE) e [NOTICE](../../NOTICE).
