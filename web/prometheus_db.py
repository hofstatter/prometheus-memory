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

CREATE TABLE IF NOT EXISTS prometheus_skills (
  id TEXT PRIMARY KEY,
  project_slug TEXT NOT NULL,
  name TEXT NOT NULL,
  description TEXT DEFAULT '',
  content TEXT NOT NULL,
  scope TEXT DEFAULT 'project',   -- project | global
  status TEXT DEFAULT 'draft',    -- draft | active | archived
  confidence REAL DEFAULT 0.5,
  evidence_json TEXT DEFAULT '[]',
  source TEXT DEFAULT 'builder',  -- builder | manual
  version INTEGER DEFAULT 1,
  checksum TEXT DEFAULT '',
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  last_used_at TEXT,
  use_count INTEGER DEFAULT 0
);
CREATE INDEX IF NOT EXISTS idx_psk_slug ON prometheus_skills(project_slug, status);
CREATE UNIQUE INDEX IF NOT EXISTS idx_psk_uniq ON prometheus_skills(project_slug, name);

CREATE TABLE IF NOT EXISTS prometheus_dedup_hashes (
  channel TEXT NOT NULL,
  content_hash TEXT NOT NULL,
  memory_id TEXT NOT NULL,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (channel, content_hash)
);

CREATE TABLE IF NOT EXISTS prometheus_entities (
  id TEXT PRIMARY KEY,
  name TEXT NOT NULL,
  type TEXT DEFAULT 'auto',
  canonical_id TEXT,
  first_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  last_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  mention_count INTEGER DEFAULT 1,
  UNIQUE(name, type)
);
CREATE INDEX IF NOT EXISTS idx_pme_name ON prometheus_entities(name);

CREATE TABLE IF NOT EXISTS prometheus_memory_entities (
  memory_id TEXT NOT NULL,
  entity_id TEXT NOT NULL,
  PRIMARY KEY (memory_id, entity_id)
);
CREATE INDEX IF NOT EXISTS idx_pmme_entity ON prometheus_memory_entities(entity_id);

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
    _migrate_entities_canonical(con)
    con.commit()
    con.close()
    _init_done = True


def _migrate_entities_canonical(con: sqlite3.Connection) -> None:
    """v1.2 — adiciona canonical_id a bancos criados antes da coluna existir."""
    cols = [r[1] for r in con.execute("PRAGMA table_info(prometheus_entities)").fetchall()]
    if cols and "canonical_id" not in cols:
        con.execute("ALTER TABLE prometheus_entities ADD COLUMN canonical_id TEXT")
    # idempotente nos dois caminhos (novo DB já tem a coluna no CREATE TABLE)
    con.execute("CREATE INDEX IF NOT EXISTS idx_pme_canonical ON prometheus_entities(canonical_id)")
