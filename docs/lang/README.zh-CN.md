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
- 🕸️ **知识图谱** — G6.js d3-force 布局，Obsidian 风格：发光效果、悬停激活、点击查看详情
- 📐 **Mermaid 画布** — 自动生成的智能体状态图，支持缩放、点击查看卸载内容
- 📄 **多模态本地 RAG** — 上传 PDF、TXT、MD、DOCX、PNG、JPG，自动 OCR（Tesseract），向量检索
- 📝 **智能笔记** — 通过 URL 导入（GitHub、X/Twitter、网站），自动清洗并自带 Markdown 渲染器
- ✏️ **内联编辑器** — 直接在界面中编辑和删除记忆
- 💾 **日志卸载** — 大型工具输出转为引用（最多减少 61% 的 token 消耗）
- 🧠 **技能生成** — 检测场景中反复出现的模式，自动生成可复用的技能
- 🎨 深色模式、响应式设计、零构建步骤（无 node_modules）

## 架构

```
┌─────────────────────────────────────────────────────┐
│              Prometheus Web UI (:8777)               │
│  时间线 │ 图谱 │ 画布 │ 文档 │ 笔记 │ ✏️              │
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
| **Cursor** | `.cursor/mcp.json` → `{"mcpServers": {"mnemosyne": {"url": "http://localhost:8765/sse"}}}` |
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

## Google Antigravity 与 VSCode

两者均支持 MCP（SSE + Bearer）——配置块见主 README 的集成部分。
