# ⚡ Prometheus Memory

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
bash setup.sh
```

`setup.sh` 会安装依赖、复制流水线脚本、安装 auto-memory 技能、
创建 cron 任务并启用 Web UI 的 systemd 服务。

然后配置你的密钥：

```bash
nano ~/prometheus-memory/.env   # DEEPSEEK_API_KEY 必填
systemctl --user restart prometheus-web
```

访问：**http://localhost:8777**

### 手动安装

```bash
pip install "mnemosyne-memory[all]>=3.12"
pip install -r requirements.txt
cp .env.example .env   # 编辑填入你的密钥
set -a; . ./.env; set +a
python3 web/app.py     # http://localhost:8777
```

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
- 笔记端点的路径穿越防护
- URL 导入的 SSRF 防护（仅允许公网 http/https）
- 源码中无任何密钥——仅使用环境变量
- 渲染时的 HTML/JS 清洗（XSS 防护）

## 集成

兼容任何支持 MCP 的智能体：

- **OpenCode**（原生支持——包含 `auto-memory` 技能）
- **Claude Code**、**Cursor**、**Codex CLI**（通过 Mnemosyne MCP）

## 对比

见 [COMPARISON.md](../../COMPARISON.md) — Mnemosyne vs MemPalace vs TencentDB vs Prometheus。

## 作者

**Herbert Hofstatter** — [@hofstatter](https://github.com/hofstatter) · [X @hofstatter](https://x.com/hofstatter)

## 许可证

MIT — 见 [LICENSE](../../LICENSE) 和 [NOTICE](../../NOTICE)。
