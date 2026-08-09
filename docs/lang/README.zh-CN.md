# ⚡ Prometheus Memory

> 🌐 [English](../../README.md) · [Português](README.pt-BR.md) · [Español](README.es.md) · **中文**

> 面向 AI 智能体的 L0→L3 记忆流水线。
> 将原始对话转化为用户画像、技能与图表。
> 基于 [Mnemosyne](https://github.com/abdiasrj/mnemosyne)（BEAM 架构）构建，架构灵感来自 TencentDB-Agent-Memory（L0→L3 金字塔）。

[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](../../LICENSE)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/)
[![Mnemosyne 3.12+](https://img.shields.io/badge/mnemosyne-3.12+-blueviolet.svg)](https://github.com/abdiasrj/mnemosyne)

🌐 [English](../../README.md) | [Português](README.pt-BR.md) | **中文**

## 为什么叫 "Prometheus"（普罗米修斯）

在希腊神话中，普罗米修斯是记忆女神谟涅摩叙涅（Mnemosyne）之子——
是将**知识之火**带给人类的泰坦。Mnemosyne 负责存储（记忆），
Prometheus 则将原始数据转化为**可执行的知识**（用户画像、技能、图表）。

## 🧠 智能体的第二大脑

**一个大脑，多个智能体。** Prometheus Memory 充当所有 AI 智能体的
**共享第二大脑**。OpenCode、Claude Code、Cursor、Codex 以及自定义智能体
通过 MCP 读写**同一份记忆**。智能体 A 早上做出的决策，智能体 B 下午即可使用
—— 在会话、工具或机器之间，一切都不会丢失。

### 🔁 为循环智能体而生

专为**持续运行的循环智能体**（每日分诊、监控、24/7 自动化）设计：
每次循环迭代都会回忆之前学到的东西（`mnemosyne recall`），
并在结束时存储新的事实（`mnemosyne remember`）。
L0→L3 流水线会自动整合一切 —— 每 6 小时事实汇集成场景，
每周汇集成用户画像和技能。智能体切实地**在每个周期变得更聪明**，
无需任何人工干预。

## 使用场景

- 🔁 **24/7 循环智能体** — 每日分诊、X/Twitter 监控、从每次运行中学习的观察者
- 🤝 **多智能体团队** — 不同角色的智能体共享上下文
- 📅 **长期项目** — 数十次会话，零上下文丢失
- 🛠️ **多种 AI 工具** — 为整个技术栈提供统一记忆层

## 功能特性

- 🔍 **层级时间线** — L3→L2→L1 逐层钻取，侧边栏含项目/日期/统计
- 🕸️ **知识图谱** — G6.js d3-force 布局，Obsidian 风格：发光效果、悬停激活、点击查看详情；**真实边**（`ctx`、`references`、`mentions`、`executou`）基于**纯 Python 的 PageRank + 度中心性**，密集模式自动折叠为核心枢纽子图
- 📐 **Mermaid 画布** — 自动生成的智能体状态图，支持缩放、点击查看卸载内容；**v2：多项目**（每个项目一个子图，展示 Backlog→Doing→Done 事件流、项目芯片、图例和指向项目标签页的链接）
- 📄 **多模态本地 RAG** — 上传 PDF、TXT、MD、DOCX、PNG、JPG，自动 OCR（Tesseract），向量检索
- 📝 **智能笔记** — 通过 URL 导入（GitHub、X/Twitter、网站），自动清洗并自带 Markdown 渲染器
- ✏️ **内联编辑器** — 直接在界面中编辑和删除记忆（7 个标签页 + 编辑弹窗）
- 💾 **日志卸载** — 大型工具输出转为引用（最多减少 61% 的 token 消耗）
- 🧠 **技能生成** — 检测场景中反复出现的模式，自动生成可复用的技能
- 🗂️ **项目标签页（v0.2）** — 按项目展示运营面板：看板、时间线、进度条和**实时智能体在线状态**（heartbeat 驱动的 active/idle/stale），基于 `sess:*`/`proj:*`/`agent:*` 通道与 `/api/pm/*`（`client_event_id` 幂等、Project Resolver 带置信度）
- 🔑 **连接与成本（v0.2）** — 按项目的 API 密钥/MCP/订阅：`.env` 只读扫描（SHA-256 指纹，**绝不存储/暴露原始值**）、"已付费未使用"/"即将过期"告警、跨项目共享密钥检测、全局月度成本汇总
- 🧱 **技术栈与运行时（v0.2）** — GitHub 风格语言占比条（按字节统计，文档/配置单独列出）、框架（monorepo 感知）、数据库（compose/DATABASE_URL）、容器与 git（分支/提交/dirty 或"未版本化"）
- 🧩 **项目技能（v0.2）** — Skill Builder 从项目事件检测模式 → **草稿**（含证据）→ 人工批准 → `active` → 可提升为全局
- 🧬 **Mem0 V3 模式（v0.2）** — 单次 LLM 提取并做时间锚定（"今天/昨天"→绝对日期）、按通道 SHA-256 去重、实体链接与召回阈值
- 🎨 深色模式、响应式设计、零构建步骤（无 node_modules）

## 架构

```
┌─────────────────────────────────────────────────────┐
│              Prometheus Web UI (:8777)               │
│  时间线 │ 图谱 │ 画布 │ 文档 │ 笔记 │ 技能 │ 项目 │ ✏️      │
└─────────────────────────────────────────────────────┘
                          │
          ┌───────────────┼───────────────┐
          ▼               ▼               ▼
 ┌─────────────┐  ┌─────────────┐  ┌─────────────┐
 │ L3 用户画像  │  │ L2 场景     │  │ L0 会话     │
 │ （每周）     │  │ （每6小时） │  │（会话结束） │
 └─────────────┘  └─────────────┘  └─────────────┘
                          │
                     ┌────▼────┐
                     │ L1 事实 │
                     │(自动记忆)│
                     └────┬────┘
                          │
               ┌──────────▼──────────┐
               │    Mnemosyne 3.12+  │
               │  SQLite + sqlite-vec│
               │  FTS5 + BEAM        │
               └─────────────────────┘
```

完整细节见 [ARCHITECTURE.md](../../ARCHITECTURE.md)。

## 快速开始

### 前置要求

- Python 3.10+
- 带 systemd 的 Linux（用于 24/7 服务——可选）
- DeepSeek API 密钥（用于 L2/L3 整合）
- Tesseract OCR（可选，用于扫描版 PDF 和图片）

### 一键安装

```bash
git clone https://github.com/hofstatter/prometheus-memory.git
cd prometheus-memory
python setup.py          # 通用：Windows / macOS / Linux / 树莓派
# 或：bash setup.sh      （Unix 封装）
```

安装程序会自动检测操作系统/架构，询问您的**语言**（en/pt/es/zh），安装依赖，
并按平台注册 Web UI（Linux 使用 systemd，macOS 使用 launchd，Windows 提供任务计划程序说明）。

### Docker（一体化）

服务器推荐——单个容器即可运行 Web UI、MCP 服务器和 REST API（supervisord）：

```bash
git clone https://github.com/hofstatter/prometheus-memory.git
cd prometheus-memory
docker compose up -d          # http://localhost:8777 · MCP :8765 · REST :8766
```

数据存放在命名卷 `prometheus-data` 中（绝不离开主机）。已有 `~/.hermes/mnemosyne` 存储的一次性迁移：
`./scripts/migrate_to_docker.sh`。详见 [docs/PLAN_P6_DOCKER.md](../../docs/PLAN_P6_DOCKER.md)。

### 支持的平台

| 平台 | 状态 |
|---|---|
| Linux x86_64 | ✅ |
| Linux ARM64 / 树莓派 5 | ✅ |
| macOS（Intel + Apple Silicon） | ✅ |
| Windows 10/11（x64） | ✅ |

### 界面语言 🌐

Web 界面会自动检测浏览器语言——**English、Português、Español、中文**——并可通过顶部的
🌐 选择器随时切换（按浏览器保存）。在 `.env` 中设置 `PROMETHEUS_LANG` 可强制默认语言。（RAG 标签页在中文界面显示为「检索增强」。）

## 配置

所有选项均为环境变量——见 [.env.example](../../.env.example)：

| 变量 | 默认值 | 用途 |
|---|---|---|
| `DEEPSEEK_API_KEY` | — | L2/L3 **必填**（场景、画像、技能） |
| `PROMETHEUS_HOST` | `127.0.0.1` | Web UI 绑定地址（局域网用 `0.0.0.0`，风险自担） |
| `PROMETHEUS_PORT` | `8777` | Web UI 端口 |
| `MNEMOSYNE_HOME` | `~/.hermes/mnemosyne` | Mnemosyne 数据目录 |
| `PROMETHEUS_NOTES_DIR` | `~/notes` | 笔记目录 |
| `PROMETHEUS_USER` | `$USER` | 画像记忆中使用的名字 |
| `PROMETHEUS_PROJECT` | `geral` | 记忆的默认项目 |
| `PROMETHEUS_PASSWORD` | — | **UI 登录密码**（绑定非 localhost 时必填） |
| `PROMETHEUS_TOKEN` | — | 供智能体/脚本使用的 API Bearer 令牌 |
| `PROMETHEUS_PROTECT_READS` | `false` | `true` = 整个界面都需要登录 |
| `PROMETHEUS_PROJECTS` | — | 已知项目（逗号分隔） |
| `PROMETHEUS_EXCLUDE` | — | 在界面中隐藏的内容（逗号分隔） |
| `FIRECRAWL_API_KEY` | — | 抓取备用方案（可选） |
| `MNEMOSYNE_LEXICAL_GATE_MIN` | *历史值*（≥4 token 时为 0.3） | 召回质量旋钮（浮点 0.0–1.0）。覆盖最小词法重叠门槛：`0.0` 接受纯向量候选（召回优先——PT hit@5 43.8%→71.9%）；留空则保持上游历史阈值 |

## L0→L3 流水线

| 层级 | 脚本 | 频率 | 输出 |
|---|---|---|---|
| **L0** 会话 | `scripts/session_logger.py` | 每次会话结束 | 每会话一个 Markdown |
| **L1** 事实 | `auto-memory` 技能 | 会话进行中 | `mnemosyne remember` |
| **L2** 场景 | `scripts/memory_aggregator.py` | cron 每 6 小时 | 主题场景 + 画布 |
| **L3** 画像 | `scripts/persona_synthesizer.py` | cron 每周 | `persona.md` + L3 事实 |
| **技能** | `scripts/skill_generator.py` | 每周（随 L3） | `~/.opencode/skills/generated/` 中的技能 |
| **卸载** | `scripts/ref_manager.py` | 按需 | 带 node_id 的 `refs/*.md` |

## 安全

- 默认绑定 `127.0.0.1`（无网络暴露）
- **登录系统**：当 `PROMETHEUS_HOST != 127.0.0.1` 时，界面会在每个浏览器中要求输入一次 `PROMETHEUS_PASSWORD`（模态框），并签发 30 天 HMAC 会话。登录接口限流（每 IP 每分钟 5 次——窗口期内即使密码正确也需等待）
- **API 令牌**：智能体/脚本使用 `Authorization: Bearer $PROMETHEUS_TOKEN` 代替密码登录
- **作用域**：默认仅保护写操作（读取开放）；`PROMETHEUS_PROTECT_READS=true` 保护整个 API（HTML 外壳保持公开以便渲染登录框）
- **单用户单存储**：无智能体隔离（信任边界 = 本机）。多租户作用域将在 v0.2 提供
- 笔记端点的路径穿越防护
- URL 导入的 SSRF 防护，每次重定向都会重新验证
- XSS 加固：集合 ID 消毒、代码块转义、严格 CSP 头
- 源码中无任何密钥——仅使用环境变量
- 渲染时的 HTML/JS 清洗（XSS 防护）

## 实时资源监控

- ⚡ **实时资源监控** — 时间线侧边栏实时显示 GPU/内存/磁盘使用率条 + 进程占用（每 3 秒更新）

## 集成

兼容任何支持 MCP 的智能体——**所有开发工具共享同一份记忆**：

```
OpenCode ─┐
Claude Code ─┼──► Mnemosyne MCP (:8765) ──► Prometheus Memory（同一存储）
Cursor ─────┤        ▲
Codex CLI ──┘   REST API (:8777) — /api/context/briefing, /api/memory/*
```

### 各工具配置

| 工具 | 配置 |
|---|---|
| **OpenCode** | 全局（推荐）：`~/.config/opencode/opencode.jsonc`（`mcp` 块：url :8765/sse + Bearer header）+ `cp -r skills/auto-memory ~/.config/opencode/skills/auto-memory/`。⚠️ `~/.opencode/skills/` 是**旧路径**（OpenCode ≤2025），当前为 `~/.config/opencode/skills/`。按项目：`<项目>/.opencode/skills/` + 相同 `mcp` 块。MCP（:8765）需要 Bearer 令牌（`MNEMOSYNE_MCP_TOKEN`）。 |
| **Claude Code** | `claude mcp add mnemosyne --transport sse http://localhost:8765/sse` |
| **Cursor** | `.cursor/mcp.json` → `{"mcpServers": {"prometheus": {"url": "http://localhost:8765/sse"}}}` |
| **Codex CLI** | `~/.codex/config.toml` → `[mcp_servers.mnemosyne]` `url = "http://localhost:8765/sse"` |
| **任意智能体** | REST：`GET /api/context/briefing`（会话开始，约 500 token）+ Mnemosyne CLI/MCP 写入 |

智能体 A 早上做出的决策，智能体 B 下午即可使用——工具不同，记忆相同。

## Token 节省

Prometheus 旨在**降低 token 开销**，而不仅仅是存储记忆：

| 机制 | 如何节省 |
|---|---|
| **日志卸载**（`scripts/ref_manager.py`） | 大型工具输出（>500 字符）转为 `[ref:id]` 引用——上下文中最多减少 **61%** 的 token |
| **L0→L3 压缩** | 原始事实聚合为场景和画像——每个被聚合的事实，recall 注入约减少 40 token |
| **上下文简报** | `GET /api/context/briefing` 返回约 500 token 的压缩摘要（画像 + 场景 + 近期事实）——以最低成本开启每次会话 |
| **节省计量器** | `GET /api/stats/savings` 估算累计节省的 token（卸载字节 ÷ 4 + 压缩），并在 UI 侧边栏显示 💰 卡片 |

## 对比

见 [COMPARISON.md](../../COMPARISON.md) — Mnemosyne vs MemPalace vs TencentDB vs Prometheus。

## 作者

**Herbert Hofstatter** — [@hofstatter](https://github.com/hofstatter) · [X @hofstatter](https://x.com/hofstatter)

## 许可证

MIT — 见 [LICENSE](../../LICENSE) 和 [NOTICE](../../NOTICE)。


## 多智能体记忆（隔离）

每个智能体拥有独立的记忆通道（`agent-<id>`）——记忆不会在智能体之间泄露：

```bash
curl -X POST localhost:8777/api/memory/remember -H "Authorization: Bearer $TOKEN" \
  -d '{"agent_id": "atlas", "content": "atlas 偏好异步 Python"}'
curl -X POST localhost:8777/api/memory/recall -H "Authorization: Bearer $TOKEN" \
  -d '{"agent_id": "atlas", "query": "python"}'
```

共享上下文？使用 `agent_id: ""`（默认通道）。

## 技能注册中心（第 1 层 — 私有）

Prometheus 也是一个**私有技能注册中心**——你的"工作室"，可通过 UI 创建、编辑和迭代技能，任何 IDE（OpenCode、Cursor、VSCode）都可从中同步：

```bash
curl -X POST localhost:8777/api/skills -H "Authorization: Bearer $TOKEN" \
  -d '{"name":"my-skill","content":"# My Skill\ncontent"}'
prometheus-skills sync            # OpenCode（~/.config/opencode/skills/）
prometheus-skills sync --ide cursor
prometheus-skills list
```

- **第 1 层（私有）：** 你的技能，可通过 UI（🧩 Skills 标签页）编辑，只有你能写入
- **🧩 Skills 标签页 UI：** 左侧边栏（技能列表、📅 日期、📊 统计）+ 内容查看器，支持原始下载和删除
- **第 2 层（公开/GitHub）：** 准备好后用 `prometheus-skills publish <名称>` 发布
- **外部贡献：** 通过仓库的 Pull Request（你审核合并）

### 技能 `ai-company`（16 位高级分析师 + 开发流水线）

注册中心及 `skills/ai-company/` 内置：16 位高级分析师引导用户完成流水线 **PRD（grill-me 访谈 + 检查点）→ 批准 → 技术规格（前端、后端、数据库）→ 设计评审 → 验证 → 迭代冲刺 → 验证 → 交付**，含人工批准门。模板：`PRD.md`、`TECH_SPEC.md`、`SPRINT.md`、`VALIDATION.md`。已在 OpenCode 全局安装——适用于所有项目和会话。

**内嵌技能：**

| 文件 | 内容 | 致谢 |
|---|---|---|
| `design/super-designer/` | **唯一设计权威** — 20 条戒律、46 个反模式、35 项交付前检查、3 个调节旋钮（VARIANCE/MOTION/DENSITY）。所有 UI 必须通过强制设计评审门 | 基于 emilkowalski/skills、impeccable.style、tasteskill.dev |
| `GRILL.md` | 毫不留情的 PRD 访谈（一次一个问题）+ 每个回答在 `brainstorms/` 中**保存检查点** | mattpocock/skills |
| `VIRAL.md` | 病毒式产品的 31 条原则 — 发布指南，**仅限品牌层**（落地页/定价/营销） | Marc Lou |
| `REVENUE.md` | 以收入为中心的设计 — 101 条转化/定价/流失原则。**许可证：需署名，禁止用于赌博** | @richardrx (heliocosta-dev) |
| `design/emil-design-eng.md` | 参考附录 — 动画、手势、clip-path、toast、性能、无障碍。**如有分歧，以 super-designer 为准** | emilkowalski |

**决策层级：** super-designer（视觉/UX）> VIRAL（落地页文案/结构）> REVENUE（收入策略）。**分层规则：** 产品层（仪表盘/应用）= 仅 super-designer；品牌层（落地页/定价）= super-designer + VIRAL + REVENUE。

## Google Antigravity 与 VSCode

两者均支持 MCP（SSE + Bearer）——配置块见主 README 的集成部分。

## 🕸️ 知识图谱 — 真实边

图谱标签页（`/api/graph`）渲染从 Mnemosyne 存储中提取的**真实知识图谱**——而非人工投影：

- **真实边类型**：`ctx`（gist↔记忆上下文）、`references`（共享实体提及）、`mentions`（记忆↔实体）、`executou`（三元组关系）——带实时彩色图例
- **分析指标**：**纯 Python 实现的 PageRank + 度中心性**（零新增依赖），按节点暴露并用于枢纽排名
- **密集模式**：小图使用圆形布局并常显标签；大网络自动折叠为**枢纽 + 实体子图**，保证结构可读
- **召回增强**：召回负载包含 `graph_degree`——关联记忆与语义得分一起呈现

![知识图谱](../SCREENSHOTS/graph.png)
