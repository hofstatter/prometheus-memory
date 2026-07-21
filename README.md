# ⚡ Prometheus Memory

> L0→L3 memory pipeline for AI Agents.
> Turns raw conversations into personas, skills and diagrams.
> Built on [Mnemosyne](https://github.com/abdiasrj/mnemosyne) (BEAM) + architecture inspired by TencentDB-Agent-Memory (L0→L3 pyramid).

[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/)
[![Mnemosyne 3.12+](https://img.shields.io/badge/mnemosyne-3.12+-blueviolet.svg)](https://github.com/abdiasrj/mnemosyne)

🌐 **English** | [Português](docs/lang/README.pt-BR.md) | [中文](docs/lang/README.zh-CN.md)

## Why "Prometheus"

In Greek mythology, Prometheus is the son of Mnemosyne (goddess of memory) —
the titan who brought the **fire of knowledge** to humanity. Mnemosyne stores
(memory); Prometheus transforms raw data into **actionable knowledge**
(persona, skills, diagrams).

## Features

- 🔍 **Hierarchical Timeline** — L3→L2→L1 drill-down, sidebar with projects/dates/stats
- 🕸️ **Knowledge Graph** — G6.js d3-force, Obsidian-style: glow, hover-activate, click → details
- 📐 **Mermaid Canvas** — auto-generated agent state diagram, zoom, click → offloaded content
- 📄 **Multimodal local RAG** — upload PDF, TXT, MD, DOCX, PNG, JPG with automatic OCR (Tesseract), vector search
- 📝 **Notes** — URL import (GitHub, X/Twitter, websites) with sanitization and custom Markdown renderer
- ✏️ **Inline Editor** — edit and delete memories directly in the UI
- 💾 **Log offloading** — large tool outputs become refs (up to 61% token reduction)
- 🧠 **Skill generation** — detects recurring patterns in scenes and generates reusable skills
- 🎨 Dark mode, responsive, zero build step (no node_modules)

## Architecture

```
┌─────────────────────────────────────────────────────┐
│              Prometheus Web UI (:8777)               │
│  Timeline │ Graph │ Canvas │ Documents │ Notes │ ✏️  │
└─────────────────────────────────────────────────────┘
                          │
          ┌───────────────┼───────────────┐
          ▼               ▼               ▼
 ┌─────────────┐  ┌─────────────┐  ┌─────────────┐
 │ L3 Persona  │  │ L2 Scenes   │  │ L0 Sessions │
 │ (weekly)    │  │ (every 6h)  │  │(session end)│
 └─────────────┘  └─────────────┘  └─────────────┘
                          │
                     ┌────▼────┐
                     │   L1    │
                     │  Facts  │
                     │(auto-mem)│
                     └────┬────┘
                          │
               ┌──────────▼──────────┐
               │    Mnemosyne 3.12+  │
               │  SQLite + sqlite-vec│
               │  FTS5 + BEAM        │
               └─────────────────────┘
```

Full details in [ARCHITECTURE.md](ARCHITECTURE.md).

## Quick Start

### Prerequisites

- Python 3.9+
- Linux with systemd (for 24/7 service — optional)
- DeepSeek API key (for L2/L3 consolidation)
- Tesseract OCR (optional, for scanned PDFs and images)

### Install (1 command)

```bash
git clone https://github.com/hofstatter/prometheus-memory.git
cd prometheus-memory
bash setup.sh
```

`setup.sh` installs dependencies, copies the pipeline scripts, installs the
auto-memory skill, creates cron jobs and enables the Web UI systemd service.

Then configure your keys:

```bash
nano ~/prometheus-memory/.env   # DEEPSEEK_API_KEY required
systemctl --user restart prometheus-web
```

Open: **http://localhost:8777**

### Manual install

```bash
pip install "mnemosyne-memory[all]>=3.12"
pip install -r requirements.txt
cp .env.example .env   # edit with your keys
set -a; . ./.env; set +a
python3 web/app.py     # http://localhost:8777
```

## Configuration

All options are environment variables — see [.env.example](.env.example):

| Variable | Default | Purpose |
|---|---|---|
| `DEEPSEEK_API_KEY` | — | **Required** for L2/L3 (scenes, persona, skills) |
| `PROMETHEUS_HOST` | `127.0.0.1` | Web UI bind (use `0.0.0.0` for LAN, at your own risk) |
| `PROMETHEUS_PORT` | `8777` | Web UI port |
| `MNEMOSYNE_HOME` | `~/.hermes/mnemosyne` | Mnemosyne data directory |
| `PROMETHEUS_NOTES_DIR` | `~/notes` | Notes directory |
| `PROMETHEUS_USER` | `$USER` | Name used in persona memories |
| `PROMETHEUS_PROJECT` | `geral` | Default project for memories |
| `PROMETHEUS_PROJECTS` | — | Known projects (comma-separated) |
| `PROMETHEUS_EXCLUDE` | — | Content to hide from the UI (comma-separated) |
| `FIRECRAWL_API_KEY` | — | Scraping fallback (optional) |

## L0→L3 Pipeline

| Layer | Script | Frequency | Output |
|---|---|---|---|
| **L0** Sessions | `scripts/session_logger.py` | End of each session | Markdown per session |
| **L1** Facts | `auto-memory` skill | During the session | `mnemosyne remember` |
| **L2** Scenes | `scripts/memory_aggregator.py` | Cron every 6h | Thematic scenes + Canvas |
| **L3** Persona | `scripts/persona_synthesizer.py` | Weekly cron | `persona.md` + L3 facts |
| **Skills** | `scripts/skill_generator.py` | Weekly (with L3) | Skills in `~/.opencode/skills/generated/` |
| **Offloading** | `scripts/ref_manager.py` | On demand | `refs/*.md` with node_id |

## Security

- Defaults to `127.0.0.1` bind (no network exposure)
- Path traversal protection on Notes endpoints
- SSRF protection on URL import (public http/https only)
- No keys in source code — environment variables only
- HTML/JS sanitization on rendering (XSS)

## Integrations

Works with any MCP-compatible agent:

- **OpenCode** (native — `auto-memory` skill included)
- **Claude Code**, **Cursor**, **Codex CLI** (via Mnemosyne MCP)

## Comparison

See [COMPARISON.md](COMPARISON.md) — Mnemosyne vs MemPalace vs TencentDB vs Prometheus.

## Author

**Herbert Hofstatter** — [@hofstatter](https://github.com/hofstatter)

## License

MIT — see [LICENSE](LICENSE) and [NOTICE](NOTICE).
