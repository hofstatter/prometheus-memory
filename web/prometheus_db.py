#!/usr/bin/env python3
"""Prometheus sidecar DB — tabelas prometheus_* (nunca ALTER no upstream Mnemosyne).

Mesmo padrão de skills_registry/storage: WAL + busy_timeout + synchronous=NORMAL.
Schema idempotente (CREATE TABLE IF NOT EXISTS), inicializado via init_schema().
"""
import os
import sqlite3
from pathlib import Path

MNEMOSYNE_HOME = Path(os.environ.get("MNEMOSYNE_HOME", Path.home() / ".hermes" / "mnemosyne"))
DB_PATH = Path(os.environ.get("PROMETHEUS_DB", MNEMOSYNE_HOME / "data" / "mnemosyne.db"))

SCHEMA = """
CREATE TABLE IF NOT EXISTS prometheus_projects (
  slug TEXT PRIMARY KEY,
  name TEXT NOT NULL,
  repo_path TEXT,
  git_remote TEXT,
  color TEXT,
  status TEXT DEFAULT 'active',
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  last_event_at TIMESTAMP
);

CREATE TABLE IF NOT EXISTS prometheus_project_events (
  id TEXT PRIMARY KEY,
  project_slug TEXT NOT NULL,
  session_key TEXT,
  harness TEXT,
  agent_id TEXT,
  event_type TEXT,
  title TEXT,
  summary TEXT,
  memory_id TEXT,
  status_hint TEXT,
  progress_delta REAL DEFAULT 0,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_pme_pslug_ts ON prometheus_project_events(project_slug, created_at);

CREATE TABLE IF NOT EXISTS prometheus_project_tasks (
  id TEXT PRIMARY KEY,
  project_slug TEXT NOT NULL,
  title TEXT NOT NULL,
  status TEXT DEFAULT 'todo',
  source_event_id TEXT,
  confidence REAL DEFAULT 0.5,
  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_pmt_pslug_status ON prometheus_project_tasks(project_slug, status);

CREATE TABLE IF NOT EXISTS prometheus_sessions (
  session_key TEXT PRIMARY KEY,
  harness TEXT NOT NULL,
  harness_session_id TEXT NOT NULL,
  project_slug TEXT,
  agent_id TEXT,
  author_id TEXT,
  cwd TEXT,
  git_remote TEXT,
  current_action TEXT,
  started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  last_seen_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  status TEXT DEFAULT 'active'
);
CREATE INDEX IF NOT EXISTS idx_pms_pslug_seen ON prometheus_sessions(project_slug, last_seen_at);

CREATE TABLE IF NOT EXISTS prometheus_events_ingest (
  client_event_id TEXT PRIMARY KEY,
  session_key TEXT,
  project_slug TEXT,
  memory_id TEXT,
  processed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS prometheus_connections (
  id TEXT PRIMARY KEY,
  project_slug TEXT NOT NULL,
  kind TEXT NOT NULL,          -- api_key | mcp | service | saas
  name TEXT NOT NULL,
  provider TEXT,
  env_var TEXT,
  fingerprint TEXT,            -- SHA-256 do valor (nunca o valor) — detecta chave compartilhada
  billing_type TEXT,           -- subscription | paygo | free | unknown
  cost_usd_month REAL,
  expires_at TEXT,
  last_used_at TEXT,
  status TEXT DEFAULT 'active',-- active | unused | expired | revoked
  source TEXT DEFAULT 'manual',-- auto-env | auto-mcp | manual
  notes TEXT,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_pmc_pslug_kind ON prometheus_connections(project_slug, kind);
CREATE INDEX IF NOT EXISTS idx_pmc_fingerprint ON prometheus_connections(fingerprint);

CREATE TABLE IF NOT EXISTS prometheus_tech_profile (
  project_slug TEXT PRIMARY KEY,
  repo_path TEXT,
  languages_json TEXT,
  frameworks_json TEXT,
  databases_json TEXT,
  containers_json TEXT,
  git_json TEXT,
  analyzed_at TIMESTAMP,
  scan_duration_ms INTEGER
);

CREATE TABLE IF NOT EXISTS prometheus_project_reports (
  project_slug TEXT PRIMARY KEY,
  summary TEXT,
  progress REAL,
  open_issues INTEGER,
  last_decision TEXT,
  last_implementation TEXT,
  active_sessions INTEGER,
  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
"""

_init_done = False


def get_conn() -> sqlite3.Connection:
    con = sqlite3.connect(str(DB_PATH), timeout=10)
    con.execute("PRAGMA journal_mode=WAL")
    con.execute("PRAGMA busy_timeout=5000")
    con.execute("PRAGMA synchronous=NORMAL")
    con.row_factory = sqlite3.Row
    return con


def init_schema() -> None:
    global _init_done
    if _init_done:
        return
    con = get_conn()
    con.executescript(SCHEMA)
    con.commit()
    con.close()
    _init_done = True
