-- Prometheus-Memory sidecar schema no PG (F3) — tabelas prometheus_* + tenant_id
-- Aplicar: docker exec -i prometheus-pg psql -U prometheus -d prometheus_memory < 002_sidecar_pg.sql
CREATE EXTENSION IF NOT EXISTS vector;

-- ---------- projetos ----------
CREATE TABLE IF NOT EXISTS prometheus_projects (
    id          BIGSERIAL PRIMARY KEY,
    tenant_id   BIGINT NOT NULL REFERENCES tenants(id) DEFAULT 1,
    slug        TEXT NOT NULL,
    name        TEXT,
    repo_path   TEXT,
    created_at  TIMESTAMPTZ DEFAULT now(),
    updated_at  TIMESTAMPTZ DEFAULT now(),
    UNIQUE (tenant_id, slug)
);

CREATE TABLE IF NOT EXISTS prometheus_project_events (
    id           TEXT PRIMARY KEY,
    tenant_id    BIGINT NOT NULL REFERENCES tenants(id) DEFAULT 1,
    project_slug TEXT NOT NULL,
    session_key  TEXT,
    harness      TEXT,
    agent_id     TEXT,
    event_type   TEXT,
    title        TEXT,
    summary      TEXT,
    memory_id    TEXT,
    status_hint  TEXT,
    progress_delta REAL DEFAULT 0,
    created_at   TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE IF NOT EXISTS prometheus_project_tasks (
    id            TEXT PRIMARY KEY,
    tenant_id     BIGINT NOT NULL REFERENCES tenants(id) DEFAULT 1,
    project_slug  TEXT NOT NULL,
    title         TEXT NOT NULL,
    status        TEXT DEFAULT 'todo',
    source_event_id TEXT,
    confidence    REAL DEFAULT 0.5,
    updated_at    TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE IF NOT EXISTS prometheus_project_reports (
    project_slug  TEXT NOT NULL,
    tenant_id     BIGINT NOT NULL REFERENCES tenants(id) DEFAULT 1,
    summary       TEXT,
    progress      REAL,
    open_issues   INTEGER,
    last_decision TEXT,
    last_implementation TEXT,
    active_sessions INTEGER,
    updated_at    TIMESTAMPTZ DEFAULT now(),
    PRIMARY KEY (tenant_id, project_slug)
);

-- ---------- sessões / ingest ----------
CREATE TABLE IF NOT EXISTS prometheus_sessions (
    id           BIGSERIAL PRIMARY KEY,
    tenant_id    BIGINT NOT NULL REFERENCES tenants(id) DEFAULT 1,
    project_slug TEXT,
    agent_id     TEXT,
    session_id   TEXT,
    harness      TEXT,
    started_at   TIMESTAMPTZ DEFAULT now(),
    last_seen_at TIMESTAMPTZ DEFAULT now(),
    status       TEXT DEFAULT 'active',
    UNIQUE (tenant_id, session_id)
);

CREATE TABLE IF NOT EXISTS prometheus_events_ingest (
    client_event_id TEXT PRIMARY KEY,
    tenant_id    BIGINT NOT NULL REFERENCES tenants(id) DEFAULT 1,
    session_key  TEXT,
    project_slug TEXT,
    memory_id    TEXT,
    processed_at TIMESTAMPTZ DEFAULT now()
);

-- ---------- conexões / custos ----------
CREATE TABLE IF NOT EXISTS prometheus_connections (
    id           TEXT PRIMARY KEY,
    tenant_id    BIGINT NOT NULL REFERENCES tenants(id) DEFAULT 1,
    project_slug TEXT NOT NULL,
    kind         TEXT NOT NULL,
    name         TEXT NOT NULL,
    provider     TEXT,
    env_var      TEXT,
    fingerprint  TEXT,
    billing_type TEXT,
    cost_usd_month REAL,
    expires_at   TEXT,
    last_used_at TEXT,
    status       TEXT DEFAULT 'active',
    source       TEXT DEFAULT 'manual',
    notes        TEXT,
    created_at   TIMESTAMPTZ DEFAULT now(),
    updated_at   TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE IF NOT EXISTS prometheus_tech_profile (
    project_slug  TEXT NOT NULL,
    tenant_id     BIGINT NOT NULL REFERENCES tenants(id) DEFAULT 1,
    lang_pct      JSONB,
    frameworks    JSONB,
    dbs           JSONB,
    containers    JSONB,
    git_status    TEXT,
    updated_at    TIMESTAMPTZ DEFAULT now(),
    PRIMARY KEY (tenant_id, project_slug)
);

CREATE TABLE IF NOT EXISTS prometheus_skills (
    id          TEXT PRIMARY KEY,
    tenant_id   BIGINT NOT NULL REFERENCES tenants(id) DEFAULT 1,
    project_slug TEXT,
    name        TEXT NOT NULL,
    status      TEXT DEFAULT 'draft',
    content     TEXT,
    version     TEXT,
    updated_at  TIMESTAMPTZ DEFAULT now()
);

-- ---------- dedup / entidades ----------
CREATE TABLE IF NOT EXISTS prometheus_dedup_hashes (
    tenant_id    BIGINT NOT NULL REFERENCES tenants(id) DEFAULT 1,
    channel      TEXT NOT NULL,
    content_hash TEXT NOT NULL,
    memory_id    TEXT NOT NULL,
    created_at   TIMESTAMPTZ DEFAULT now(),
    PRIMARY KEY (tenant_id, channel, content_hash)
);

CREATE TABLE IF NOT EXISTS prometheus_entities (
    id           TEXT PRIMARY KEY,
    tenant_id    BIGINT NOT NULL REFERENCES tenants(id) DEFAULT 1,
    name         TEXT NOT NULL,
    type         TEXT DEFAULT 'auto',
    first_seen   TIMESTAMPTZ DEFAULT now(),
    last_seen    TIMESTAMPTZ DEFAULT now(),
    mention_count INTEGER DEFAULT 1,
    canonical_id TEXT,
    UNIQUE (tenant_id, name, type)
);

CREATE TABLE IF NOT EXISTS prometheus_memory_entities (
    tenant_id  BIGINT NOT NULL REFERENCES tenants(id) DEFAULT 1,
    memory_id  TEXT NOT NULL,
    entity_id  TEXT NOT NULL,
    PRIMARY KEY (tenant_id, memory_id, entity_id)
);

CREATE TABLE IF NOT EXISTS prometheus_meta (
    tenant_id BIGINT NOT NULL REFERENCES tenants(id) DEFAULT 1,
    key       TEXT NOT NULL,
    value     TEXT,
    PRIMARY KEY (tenant_id, key)
);

CREATE TABLE IF NOT EXISTS prometheus_reports_daily (
    id          BIGSERIAL PRIMARY KEY,
    tenant_id   BIGINT NOT NULL REFERENCES tenants(id) DEFAULT 1,
    report_date DATE DEFAULT CURRENT_DATE,
    project_slug TEXT,
    summary     JSONB,
    created_at  TIMESTAMPTZ DEFAULT now()
);

-- ---------- índices ----------
CREATE INDEX IF NOT EXISTS idx_ppe_tenant_ts ON prometheus_project_events (tenant_id, created_at);
CREATE INDEX IF NOT EXISTS idx_ppe_tenant_slug ON prometheus_project_events (tenant_id, project_slug);
CREATE INDEX IF NOT EXISTS idx_ppt_tenant_status ON prometheus_project_tasks (tenant_id, status);
CREATE INDEX IF NOT EXISTS idx_ps_tenant_seen ON prometheus_sessions (tenant_id, last_seen_at);
CREATE INDEX IF NOT EXISTS idx_pc_tenant_fp ON prometheus_connections (tenant_id, fingerprint);
CREATE INDEX IF NOT EXISTS idx_psk_tenant_status ON prometheus_skills (tenant_id, status);
