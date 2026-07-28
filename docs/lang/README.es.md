> 🌐 [English](../../README.md) · [Português](README.pt-BR.md) · **Español** · [中文](README.zh-CN.md)

> _Documentación completa en inglés en el README principal. Esta es la guía rápida en español._

# ⚡ Prometheus Memory

Pipeline de **memoria jerárquica L0→L3** para agentes de IA — el segundo cerebro compartido de tus agentes.

## ¿Qué hace?

- **Timeline jerárquica** L3→L2→L1 con proyectos, fechas y stats
- **Grafo de conocimiento** animado estilo Obsidian (física continua)
- **Canvas Mermaid** auto-generado del flujo del agente
- **RAG multimodal** — PDF, TXT, MD, DOCX, imágenes con OCR
- **Notes** — importa contenido de URLs (GitHub, X, sitios web) con sanitización
- **Offloading de logs** — hasta 61% menos tokens en contexto
- **Context Briefing** — `GET /api/context/briefing` (~500 tokens para iniciar sesión)
- **Login por contraseña** — sesión de 30 días, rate limit anti-fuerza-bruta

## Instalación (1 comando)

```bash
git clone https://github.com/hofstatter/prometheus-memory.git
cd prometheus-memory
python setup.py          # Windows / macOS / Linux / Raspberry Pi
# o: bash setup.sh       (Unix)
```

El instalador detecta tu SO y arquitectura, pregunta el **idioma** (en/pt/es/zh), instala dependencias y registra el servicio según la plataforma (systemd en Linux, launchd en macOS, Task Scheduler en Windows).

## Recursos en vivo

- ⚡ **Monitor de recursos en tiempo real** — barras de GPU/RAM/disco + consumo del proceso en la barra lateral (actualiza cada 3s)

## Plataformas soportadas

| Plataforma | Estado |
|---|---|
| Linux x86_64 | ✅ |
| Linux ARM64 / Raspberry Pi 5 | ✅ |
| macOS (Intel + Apple Silicon) | ✅ |
| Windows 10/11 (x64) | ✅ |

## Integraciones

| Herramienta | Configuración |
|---|---|
| **OpenCode** | Global: `~/.config/opencode/opencode.jsonc` (bloco `mcp` con url :8765/sse + header Bearer) + `cp -r skills/auto-memory ~/.config/opencode/skills/auto-memory/`. ⚠️ `~/.opencode/skills/` es la ruta **legada** (OpenCode ≤2025); la actual es `~/.config/opencode/skills/`. Por proyecto: `<proyecto>/.opencode/skills/` + mismo bloque `mcp`. El MCP (`:8765`) exige token Bearer (`MNEMOSYNE_MCP_TOKEN`). |
| **Claude Code** | `claude mcp add mnemosyne --transport sse http://localhost:8765/sse` |
| **Cursor** | `.cursor/mcp.json` → `{"mcpServers": {"mnemosyne": {"url": "http://localhost:8765/sse"}}}` |
| **Codex CLI** | `~/.codex/config.toml` → `[mcp_servers.mnemosyne]` |

## Ahorro de tokens

| Mecanismo | Cómo ahorra |
|---|---|
| **Offloading** | Outputs grandes → refs `[ref:id]` (hasta 61% menos) |
| **Compresión L0→L3** | Hechos → escenas → persona |
| **Context Briefing** | Resumen de ~500 tokens por sesión |
| **Medidor** | `GET /api/stats/savings` + tarjeta 💰 en la UI |

## Seguridad

- Bind por defecto `127.0.0.1`; cuando se expone, **login con contraseña** (`PROMETHEUS_PASSWORD`) con sesión de 30 días y rate limit (5/min)
- Protección SSRF revalidada en cada redirect; anti path-traversal; CSP estricta
- Single-user, store compartido (multi-tenant en v0.2)

📖 **Documentación completa:** [README en inglés](../../README.md)

## Idiomas de la UI 🌐

La Web UI detecta el idioma del navegador — **English, Português, Español y 中文** — con selector 🌐. `PROMETHEUS_LANG` en `.env` fuerza un idioma. (La pestaña RAG aparece como 检索增强 en chino.)


## Memoria Multi-Agente (aislamiento)

Cada agente tiene un canal de memoria aislado (`agent-<id>`) — las memorias no se filtran entre agentes:

```bash
curl -X POST localhost:8777/api/memory/remember -H "Authorization: Bearer $TOKEN" \
  -d '{"agent_id": "atlas", "content": "atlas prefiere python asíncrono"}'
curl -X POST localhost:8777/api/memory/recall -H "Authorization: Bearer $TOKEN" \
  -d '{"agent_id": "atlas", "query": "python"}'
```

Contexto compartido? Usa `agent_id: ""` (canal por defecto).

## Skill Registry (Capa 1 — privada)

Prometheus también es un **registry privado de skills** — tu "taller" donde creas, editas e iteras skills desde la UI, y cualquier IDE (OpenCode, Cursor, VSCode) sincroniza desde él:

```bash
curl -X POST localhost:8777/api/skills -H "Authorization: Bearer $TOKEN" \
  -d '{"name":"mi-skill","content":"# Mi Skill\ncontenido"}'
prometheus-skills sync            # OpenCode (~/.config/opencode/skills/)
prometheus-skills sync --ide cursor
prometheus-skills list
```

- **Capa 1 (privada):** tus skills, editables por la UI (pestaña 🧩 Skills), solo tú escribes
- **Capa 2 (pública/GitHub):** publica con `prometheus-skills publish <nombre>` cuando esté lista
- **Contribución externa:** vía Pull Request en el repo (tú apruebas el merge)

### Skill `ai-company` (16 analistas sêniors + pipeline de desarrollo)

Incluida en el registry: 16 analistas sêniors que guían al usuario por el pipeline **PRD → aprobación → Tech Spec (Frontend, Backend, Base de Datos) → validación → Sprints → validación → entrega**, con gates de aprobación humana. Templates: `PRD.md`, `TECH_SPEC.md`, `SPRINT.md`, `VALIDATION.md`. Instalada globalmente en OpenCode — funciona en todos los proyectos y sesiones.

## Google Antigravity y VSCode

Ambos soportan MCP (SSE + Bearer) — ver la sección de integraciones del README principal para los bloques de configuración listos.
