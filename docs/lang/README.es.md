> 🌐 [English](../../README.md) · [Português](README.pt-BR.md) · **Español** · [中文](README.zh-CN.md)

> _Documentación completa en inglés en el README principal. Esta es la guía rápida en español._

# ⚡ Prometheus Memory

Pipeline de **memoria jerárquica L0→L3** para agentes de IA — el segundo cerebro compartido de tus agentes.

## ¿Qué hace?

- **Timeline jerárquica** L3→L2→L1 con proyectos, fechas y stats
- **Grafo de conocimiento** animado estilo Obsidian (física continua); **aristas reales** (`ctx`, `references`, `mentions`, `executou`) con **PageRank + degree centrality** en Python puro y modo denso que colapsa al subgrafo de hubs
- **Canvas Mermaid** auto-generado del flujo del agente — **v2: multi-proyecto** (un bloque por proyecto con flujo Backlog→Doing→Done, chips, leyenda y enlace a la pestaña Proyectos)
- **RAG multimodal** — PDF, TXT, MD, DOCX, imágenes con OCR
- **Notes** — importa contenido de URLs (GitHub, X, sitios web) con sanitización
- **Offloading de logs** — hasta 61% menos tokens en contexto
- **Context Briefing** — `GET /api/context/briefing` (~500 tokens para iniciar sesión)
- **Login por contraseña** — sesión de 30 días, rate limit anti-fuerza-bruta
- **Pestaña 🗂️ Proyectos (v0.2)** — kanban, timeline, progreso y **presencia de agentes en tiempo real** por proyecto (multi-sesión/multi-harness vía `/api/pm/*`)
- **Conexiones & Costos (v0.2)** — claves API/MCP/suscripciones por proyecto: scan `.env` solo-lectura con huella SHA-256 (**el valor nunca se expone**), alertas "pagado sin uso"/"por expirar"
- **Stack & Runtime (v0.2)** — barra de lenguajes estilo GitHub, frameworks, bases de datos, contenedores y git por proyecto
- **Skills por proyecto (v0.2)** — borrador → aprobación humana → activa → candidata a global
- **Patrones Mem0 V3 (v0.2)** — extracción LLM single-pass con fechas absolutas + dedup SHA-256 + entidades

## Instalación (1 comando)

```bash
git clone https://github.com/hofstatter/prometheus-memory.git
cd prometheus-memory
python setup.py          # Windows / macOS / Linux / Raspberry Pi
# o: bash setup.sh       (Unix)
```

El instalador detecta tu SO y arquitectura, pregunta el **idioma** (en/pt/es/zh), instala dependencias y registra el servicio según la plataforma (systemd en Linux, launchd en macOS, Task Scheduler en Windows).

### Docker (todo-en-uno)

Recomendado para servidores — un único contenedor ejecuta la Web UI, el servidor MCP y la API REST (supervisord):

```bash
git clone https://github.com/hofstatter/prometheus-memory.git
cd prometheus-memory
docker compose up -d          # http://localhost:8777 · MCP :8765 · REST :8766
```

Los datos viven en el volumen nombrado `prometheus-data` (nunca salen del host). Migración única de un store `~/.hermes/mnemosyne` existente: `./scripts/migrate_to_docker.sh`. Detalles en [docs/PLAN_P6_DOCKER.md](../PLAN_P6_DOCKER.md).

## Recursos en vivo

- ⚡ **Monitor de recursos en tiempo real** — barras de GPU/CPU/RAM/disco + consumo del proceso en la barra lateral (actualiza cada 3s)
- 🧠 **Checkpoints automáticos de sesión** — cada 3 min, todo lo conversado se resume (DeepSeek) y se guarda verbatim en la memoria de Mnemosyne (`source=checkpoint`/`checkpoint-verbatim`, tag `[checkpoint-cycle:...]`); la **pestaña Checkpoints** renderiza briefings + verbatim con **auto-refresco cada 1 min**; las credenciales se enmascaran en la visualización (`***(senha)***`)

## Plataformas soportadas

| Plataforma | Estado |
|---|---|
| Linux x86_64 | ✅ |
| Linux ARM64 / Raspberry Pi 5 | ✅ |
| macOS (Intel + Apple Silicon) | ✅ |
| Windows 10/11 (x64) | ✅ |

## Configuración

Todas las opciones son variables de entorno — ver [.env.example](../../.env.example):

| Variable | Valor por defecto | Función |
|---|---|---|
| `DEEPSEEK_API_KEY` | — | **Obligatoria** para L2/L3 (escenas, persona, skills) |
| `PROMETHEUS_HOST` | `127.0.0.1` | Bind de la Web UI (usa `0.0.0.0` para LAN, bajo tu responsabilidad) |
| `PROMETHEUS_PORT` | `8777` | Puerto de la Web UI |
| `MNEMOSYNE_HOME` | `~/.hermes/mnemosyne` | Directorio de datos de Mnemosyne |
| `PROMETHEUS_NOTES_DIR` | `~/notes` | Directorio de notas |
| `PROMETHEUS_USER` | `$USER` | Nombre usado en las memorias de persona |
| `PROMETHEUS_PROJECT` | `geral` | Proyecto por defecto de las memorias |
| `PROMETHEUS_PASSWORD` | — | **Contraseña de login de la UI** (obligatoria cuando bind ≠ localhost) |
| `PROMETHEUS_TOKEN` | — | Token Bearer de la API para agentes/scripts |
| `PROMETHEUS_PROTECT_READS` | `false` | `true` = toda la UI requiere login |
| `PROMETHEUS_PROJECTS` | — | Proyectos conocidos (separados por coma) |
| `PROMETHEUS_EXCLUDE` | — | Contenidos a ocultar de la UI (separados por coma) |
| `FIRECRAWL_API_KEY` | — | Fallback de scraping (opcional) |
| `MNEMOSYNE_LEXICAL_GATE_MIN` | *histórico* (0.3 para ≥4 tokens) | Perilla de calidad del recall (float 0.0–1.0). Sobrescribe el gate léxico mínimo: `0.0` admite candidatos puramente vectoriales (recall-first — PT hit@5 43.8%→71.9%); vacío mantiene los umbrales históricos |

## Integraciones

| Herramienta | Configuración |
|---|---|
| **OpenCode** | Global: `~/.config/opencode/opencode.jsonc` (bloco `mcp` con url :8765/sse + header Bearer) + `cp -r skills/auto-memory ~/.config/opencode/skills/auto-memory/`. ⚠️ `~/.opencode/skills/` es la ruta **legada** (OpenCode ≤2025); la actual es `~/.config/opencode/skills/`. Por proyecto: `<proyecto>/.opencode/skills/` + mismo bloque `mcp`. El MCP (`:8765`) exige token Bearer (`MNEMOSYNE_MCP_TOKEN`). |
| **Claude Code** | `claude mcp add mnemosyne --transport sse http://localhost:8765/sse` |
| **Cursor** | `.cursor/mcp.json` → `{"mcpServers": {"prometheus": {"url": "http://localhost:8765/sse"}}}` |
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
- **UI de la pestaña 🧩 Skills:** barra lateral izquierda (lista de skills, 📅 fechas, 📊 stats) + visor de contenido con descarga raw y delete
- **Capa 2 (pública/GitHub):** publica con `prometheus-skills publish <nombre>` cuando esté lista
- **Contribución externa:** vía Pull Request en el repo (tú apruebas el merge)

### Skill `ai-company` (16 analistas sêniors + pipeline de desarrollo)

Incluida en el registry y en `skills/ai-company/`: 16 analistas sêniors que guían al usuario por el pipeline **PRD (entrevista grill-me con checkpointing) → aprobación → Tech Spec (Frontend, Backend, Base de Datos) → Design Review → validación → Sprints → validación → entrega**, con gates de aprobación humana. Templates: `PRD.md`, `TECH_SPEC.md`, `SPRINT.md`, `VALIDATION.md`. Instalada globalmente en OpenCode — funciona en todos los proyectos y sesiones.

**Skills embebidas:**

| Archivo | Qué es | Crédito |
|---|---|---|
| `design/super-designer/` | **Autoridad única de diseño** — 20 mandamientos, 46 anti-patrones, 35 checks preflight, 3 dials (VARIANCE/MOTION/DENSITY). Toda UI pasa por un gate de Design Review obligatorio | basada en emilkowalski/skills, impeccable.style, tasteskill.dev |
| `GRILL.md` | Entrevista implacable del PRD (1 pregunta a la vez) + **checkpointing por respuesta** en `brainstorms/` | mattpocock/skills |
| `VIRAL.md` | 31 Principios de un Producto Viral — brújula de launch, **brand lane only** (landing/pricing/marketing) | Marc Lou |
| `REVENUE.md` | Revenue-Centric Design — 101 principios de conversión/pricing/churn. **Licencia: atribución, prohibido gambling** | @richardrx (heliocosta-dev) |
| `design/emil-design-eng.md` | Apéndice de referencia — animación, gestos, clip-path, toasts, performance, a11y. **En divergencia, super-designer gana** | emilkowalski |

**Jerarquía de decisión:** super-designer (visual/UX) > VIRAL (copy/estructura de landing) > REVENUE (estrategia de ingresos). **Lane rules:** product lane (dashboards/apps) = super-designer sola; brand lane (landing/pricing) = super-designer + VIRAL + REVENUE.

## Google Antigravity y VSCode

Ambos soportan MCP (SSE + Bearer) — ver la sección de integraciones del README principal para los bloques de configuración listos.

## 🕸️ Grafo de conocimiento — aristas reales

La pestaña Grafo (`/api/graph`) renderiza el **grafo de conocimiento real** extraído de tu store Mnemosyne — no una proyección artificial:

- **Tipos de arista reales**: `ctx` (contexto gist↔memoria), `references` (menciones de entidad compartidas), `mentions` (memoria↔entidad), `executou` (relaciones de tripla) — con leyenda de colores en vivo
- **Analytics**: **PageRank + degree centrality** en Python puro (sin dependencias nuevas), expuestos por nodo y usados para rankear hubs
- **Modo denso**: grafos pequeños usan layout circular con etiquetas permanentes; redes grandes colapsan al **subgrafo de hubs + entidades** para que la estructura siga siendo legible
- **Boost en recall**: el payload del recall incluye `graph_degree` — las memorias conectadas aparecen junto con las puntuaciones semánticas

![Grafo de conocimiento](../SCREENSHOTS/graph.png)
