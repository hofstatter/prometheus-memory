-- Prometheus-Memory PostgreSQL Schema (F2) — base multi-tenant
-- Aplicar: docker exec -i prometheus-pg psql -U prometheus -d prometheus_memory < 001_schema_pg.sql
CREATE EXTENSION IF NOT EXISTS vector;

-- ---------- Auth (multi-tenant) ----------
CREATE TABLE IF NOT EXISTS tenants (
    id              BIGSERIAL PRIMARY KEY,
    name            TEXT NOT NULL UNIQUE,
    master_key_hash TEXT,
    created_at      TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE IF NOT EXISTS agents (
    id           BIGSERIAL PRIMARY KEY,
    tenant_id    BIGINT NOT NULL REFERENCES tenants(id),
    agent_id     TEXT NOT NULL,
    api_key_hash TEXT UNIQUE,
    harness      TEXT,
    channel_id   TEXT,
    created_at   TIMESTAMPTZ DEFAULT now(),
    revoked_at   TIMESTAMPTZ,
    UNIQUE (tenant_id, agent_id)
);

-- ---------- Core (L1/L2) ----------
CREATE TABLE IF NOT EXISTS working_memory (
    id          TEXT NOT NULL,
    tenant_id   BIGINT NOT NULL REFERENCES tenants(id) DEFAULT 1,
    content     TEXT NOT NULL,
    source      TEXT,
    timestamp   TIMESTAMPTZ DEFAULT now(),
    session_id  TEXT,
    importance  REAL DEFAULT 0.5,
    metadata_json JSONB,
    veracity    TEXT,
    memory_type TEXT,
    consolidated_at TIMESTAMPTZ,
    recall_count INTEGER DEFAULT 0,
    scope       TEXT,
    author_id   TEXT,
    channel_id  TEXT,
    created_at  TIMESTAMPTZ DEFAULT now(),
    embedding   vector(384),
    PRIMARY KEY (tenant_id, id)
);

CREATE TABLE IF NOT EXISTS episodic_memory (
    id          TEXT NOT NULL,
    tenant_id   BIGINT NOT NULL REFERENCES tenants(id) DEFAULT 1,
    content     TEXT NOT NULL,
    summary_of  TEXT,
    tier        TEXT,
    timestamp   TIMESTAMPTZ DEFAULT now(),
    importance  REAL DEFAULT 0.5,
    channel_id  TEXT,
    created_at  TIMESTAMPTZ DEFAULT now(),
    embedding   vector(384),
    PRIMARY KEY (tenant_id, id)
);

-- ---------- Grafo ----------
CREATE TABLE IF NOT EXISTS triples (
    id          BIGSERIAL PRIMARY KEY,
    tenant_id   BIGINT NOT NULL REFERENCES tenants(id) DEFAULT 1,
    subject     TEXT NOT NULL,
    predicate   TEXT NOT NULL,
    object      TEXT NOT NULL,
    valid_until TIMESTAMPTZ,
    created_at  TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE IF NOT EXISTS graph_edges (
    id          BIGSERIAL PRIMARY KEY,
    tenant_id   BIGINT NOT NULL REFERENCES tenants(id) DEFAULT 1,
    source_id   TEXT,
    target_id   TEXT,
    relationship TEXT,
    weight      REAL DEFAULT 0.5,
    created_at  TIMESTAMPTZ DEFAULT now()
);

-- ---------- Sidecar prometheus_* (mínimo para F3+) ----------
CREATE TABLE IF NOT EXISTS prometheus_projects (
    id          BIGSERIAL PRIMARY KEY,
    tenant_id   BIGINT NOT NULL REFERENCES tenants(id) DEFAULT 1,
    slug        TEXT NOT NULL,
    name        TEXT,
    created_at  TIMESTAMPTZ DEFAULT now(),
    UNIQUE (tenant_id, slug)
);

CREATE TABLE IF NOT EXISTS prometheus_sessions (
    id           BIGSERIAL PRIMARY KEY,
    tenant_id    BIGINT NOT NULL REFERENCES tenants(id) DEFAULT 1,
    project_slug TEXT,
    agent_id     TEXT,
    session_id   TEXT,
    last_seen_at TIMESTAMPTZ DEFAULT now(),
    UNIQUE (tenant_id, session_id)
);

-- ---------- Índices ----------
CREATE INDEX IF NOT EXISTS idx_wm_tenant_created ON working_memory (tenant_id, created_at);
CREATE INDEX IF NOT EXISTS idx_wm_channel ON working_memory (tenant_id, channel_id);
CREATE INDEX IF NOT EXISTS idx_ep_tenant_created ON episodic_memory (tenant_id, created_at);
CREATE INDEX IF NOT EXISTS idx_triples_tenant_pred ON triples (tenant_id, predicate);
CREATE INDEX IF NOT EXISTS idx_ge_tenant ON graph_edges (tenant_id);
CREATE INDEX IF NOT EXISTS idx_wm_embedding ON working_memory USING hnsw (embedding vector_cosine_ops);
CREATE INDEX IF NOT EXISTS idx_ep_embedding ON episodic_memory USING hnsw (embedding vector_cosine_ops);

-- ---------- Full-text (tsvector) ----------
ALTER TABLE working_memory ADD COLUMN IF NOT EXISTS content_tsv tsvector;
ALTER TABLE episodic_memory ADD COLUMN IF NOT EXISTS content_tsv tsvector;
CREATE INDEX IF NOT EXISTS idx_wm_tsv ON working_memory USING gin (content_tsv);
CREATE INDEX IF NOT EXISTS idx_ep_tsv ON episodic_memory USING gin (content_tsv);

-- ---------- Seed: tenant default ----------
INSERT INTO tenants (id, name) VALUES (1, 'default')
    ON CONFLICT (id) DO NOTHING;
