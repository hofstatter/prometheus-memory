# Prometheus-Memory: 多租户 PostgreSQL + Atlas 图书管理员

**状态：** ✅ 已完成（F-1 → F8）· **日期：** 2026-08-24 · **仓库：** prometheus-memory

## 交付内容

Prometheus-Memory 已演进为**基于 PostgreSQL 的多租户记忆库**，由 **Atlas**（图书管理员智能体）管理：

| 阶段 | 交付 |
|---|---|
| F-1 | VM 101 完整备份 + 克隆（vzdump 5.7GB + 克隆 901 已停止 — 恢复点） |
| F0 | 存储审计（85 张表 → `docs/SCHEMA_INVENTORY.md`） |
| F1 | PostgreSQL 16.15 + pgvector 0.8.6 + pgBouncer（容器，每日备份） |
| F2 | 多租户 schema + `pg_backend.py`（D13：PG = Prometheus-Memory 存储） |
| F3 | Sidecar `prometheus_*` 迁入 PG（14 张表，733 条记录迁移） |
| F4 | `PGSQLiteCompat` 适配器 + 镜像验证（cron 03:30） |
| F5 | **Auth Gateway** — 每个智能体唯一 API 密钥（SHA-256，即时撤销）+ RLS 18/18 |
| F6 | Atlas 反射弧 — 反射 1.2ms + 异步深度分析 |
| F7 | Atlas DBA + 镜像神经元（13 个行为模式）+ 突触（18 条图边） |
| F8 | 每租户 L3 画像（DeepSeek）+ 可观测性（`pm_usage.py`） |

## 主要特性

- **多租户：** 所有表带 `tenant_id` + RLS（18/18，FORCE），角色 `prometheus_app`。
- **认证：** 每个智能体（Hermes、OpenClaw、OpenCode、Codex...）通过 `pm-key` 获得唯一 API 密钥。
- **Atlas：** 反射弧（快速召回 + 异步 LLM）、数据工程师（ANALYZE/VACUUM）、镜像神经元（行为建模）、突触（智能体↔项目图）、L3 画像。

## 未版本化（仅生产）

`.env`（VM）、`pg_config.json`、真实 systemd 单元、cron 脚本（`backup-pg.sh`、`pg-mirror.sh`）— 见 `docs/SCHEMA_INVENTORY.md` §6。
