-- RLS multi-tenant (F5) — isolamento por tenant_id
-- Policy: tenant = current_setting('app.tenant_id'); default '1' se não setado.
-- O Auth Gateway seta app.tenant_id na conexão após validar a API key do agente.
-- REPRODUZÍVEL: inclui FORCE em todas + role prometheus_app + GRANT (idempotente).
-- Aplicar: docker exec -i prometheus-pg psql -U prometheus -d prometheus_memory < 003_rls.sql

-- ---------- role de aplicação (sem BYPASSRLS — o dono prometheus tem bypass) ----------
DO $$ BEGIN
  IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname='prometheus_app') THEN
    CREATE ROLE prometheus_app LOGIN PASSWORD 'MUDAR_EM_PRODUCAO';
  END IF;
END $$;

-- ---------- Core ----------
ALTER TABLE working_memory ENABLE ROW LEVEL SECURITY;
ALTER TABLE working_memory FORCE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS wm_tenant ON working_memory;
CREATE POLICY wm_tenant ON working_memory
    USING (tenant_id = COALESCE(NULLIF(current_setting('app.tenant_id', true), ''), '1')::bigint);

ALTER TABLE episodic_memory ENABLE ROW LEVEL SECURITY;
ALTER TABLE episodic_memory FORCE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS ep_tenant ON episodic_memory;
CREATE POLICY ep_tenant ON episodic_memory
    USING (tenant_id = COALESCE(NULLIF(current_setting('app.tenant_id', true), ''), '1')::bigint);

ALTER TABLE triples ENABLE ROW LEVEL SECURITY;
ALTER TABLE triples FORCE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS tr_tenant ON triples;
CREATE POLICY tr_tenant ON triples
    USING (tenant_id = COALESCE(NULLIF(current_setting('app.tenant_id', true), ''), '1')::bigint);

ALTER TABLE graph_edges ENABLE ROW LEVEL SECURITY;
ALTER TABLE graph_edges FORCE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS ge_tenant ON graph_edges;
CREATE POLICY ge_tenant ON graph_edges
    USING (tenant_id = COALESCE(NULLIF(current_setting('app.tenant_id', true), ''), '1')::bigint);

-- ---------- Sidecar ----------
ALTER TABLE prometheus_projects ENABLE ROW LEVEL SECURITY;
ALTER TABLE prometheus_projects FORCE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS pp_tenant ON prometheus_projects;
CREATE POLICY pp_tenant ON prometheus_projects
    USING (tenant_id = COALESCE(NULLIF(current_setting('app.tenant_id', true), ''), '1')::bigint);

ALTER TABLE prometheus_project_events ENABLE ROW LEVEL SECURITY;
ALTER TABLE prometheus_project_events FORCE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS ppe_tenant ON prometheus_project_events;
CREATE POLICY ppe_tenant ON prometheus_project_events
    USING (tenant_id = COALESCE(NULLIF(current_setting('app.tenant_id', true), ''), '1')::bigint);

ALTER TABLE prometheus_project_tasks ENABLE ROW LEVEL SECURITY;
ALTER TABLE prometheus_project_tasks FORCE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS ppt_tenant ON prometheus_project_tasks;
CREATE POLICY ppt_tenant ON prometheus_project_tasks
    USING (tenant_id = COALESCE(NULLIF(current_setting('app.tenant_id', true), ''), '1')::bigint);

ALTER TABLE prometheus_sessions ENABLE ROW LEVEL SECURITY;
ALTER TABLE prometheus_sessions FORCE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS ps_tenant ON prometheus_sessions;
CREATE POLICY ps_tenant ON prometheus_sessions
    USING (tenant_id = COALESCE(NULLIF(current_setting('app.tenant_id', true), ''), '1')::bigint);

ALTER TABLE prometheus_events_ingest ENABLE ROW LEVEL SECURITY;
ALTER TABLE prometheus_events_ingest FORCE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS pei_tenant ON prometheus_events_ingest;
CREATE POLICY pei_tenant ON prometheus_events_ingest
    USING (tenant_id = COALESCE(NULLIF(current_setting('app.tenant_id', true), ''), '1')::bigint);

ALTER TABLE prometheus_connections ENABLE ROW LEVEL SECURITY;
ALTER TABLE prometheus_connections FORCE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS pc_tenant ON prometheus_connections;
CREATE POLICY pc_tenant ON prometheus_connections
    USING (tenant_id = COALESCE(NULLIF(current_setting('app.tenant_id', true), ''), '1')::bigint);

ALTER TABLE prometheus_skills ENABLE ROW LEVEL SECURITY;
ALTER TABLE prometheus_skills FORCE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS psk_tenant ON prometheus_skills;
CREATE POLICY psk_tenant ON prometheus_skills
    USING (tenant_id = COALESCE(NULLIF(current_setting('app.tenant_id', true), ''), '1')::bigint);

ALTER TABLE prometheus_dedup_hashes ENABLE ROW LEVEL SECURITY;
ALTER TABLE prometheus_dedup_hashes FORCE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS pdh_tenant ON prometheus_dedup_hashes;
CREATE POLICY pdh_tenant ON prometheus_dedup_hashes
    USING (tenant_id = COALESCE(NULLIF(current_setting('app.tenant_id', true), ''), '1')::bigint);

ALTER TABLE prometheus_entities ENABLE ROW LEVEL SECURITY;
ALTER TABLE prometheus_entities FORCE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS pe_tenant ON prometheus_entities;
CREATE POLICY pe_tenant ON prometheus_entities
    USING (tenant_id = COALESCE(NULLIF(current_setting('app.tenant_id', true), ''), '1')::bigint);

ALTER TABLE prometheus_memory_entities ENABLE ROW LEVEL SECURITY;
ALTER TABLE prometheus_memory_entities FORCE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS pme_tenant ON prometheus_memory_entities;
CREATE POLICY pme_tenant ON prometheus_memory_entities
    USING (tenant_id = COALESCE(NULLIF(current_setting('app.tenant_id', true), ''), '1')::bigint);

ALTER TABLE prometheus_meta ENABLE ROW LEVEL SECURITY;
ALTER TABLE prometheus_meta FORCE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS pm_tenant ON prometheus_meta;
CREATE POLICY pm_tenant ON prometheus_meta
    USING (tenant_id = COALESCE(NULLIF(current_setting('app.tenant_id', true), ''), '1')::bigint);

-- ---------- tabelas que estavam sem RLS (correção Inspetor) ----------
ALTER TABLE prometheus_project_reports ENABLE ROW LEVEL SECURITY;
ALTER TABLE prometheus_project_reports FORCE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS ppr_tenant ON prometheus_project_reports;
CREATE POLICY ppr_tenant ON prometheus_project_reports
    USING (tenant_id = COALESCE(NULLIF(current_setting('app.tenant_id', true), ''), '1')::bigint);

ALTER TABLE prometheus_tech_profile ENABLE ROW LEVEL SECURITY;
ALTER TABLE prometheus_tech_profile FORCE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS ptp_tenant ON prometheus_tech_profile;
CREATE POLICY ptp_tenant ON prometheus_tech_profile
    USING (tenant_id = COALESCE(NULLIF(current_setting('app.tenant_id', true), ''), '1')::bigint);

ALTER TABLE prometheus_reports_daily ENABLE ROW LEVEL SECURITY;
ALTER TABLE prometheus_reports_daily FORCE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS prd_tenant ON prometheus_reports_daily;
CREATE POLICY prd_tenant ON prometheus_reports_daily
    USING (tenant_id = COALESCE(NULLIF(current_setting('app.tenant_id', true), ''), '1')::bigint);

-- tenant admin (id 1) vê tudo (bypass): conceder via role owner (já é o dono)

-- ---------- GRANT ao role de aplicação ----------
GRANT USAGE ON SCHEMA public TO prometheus_app;
GRANT ALL ON ALL TABLES IN SCHEMA public TO prometheus_app;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO prometheus_app;


-- ---------- índices únicos (F7 — evita duplicatas no espelho/sinapse) ----------
CREATE UNIQUE INDEX IF NOT EXISTS uq_triples ON triples (tenant_id, subject, predicate, object);
CREATE UNIQUE INDEX IF NOT EXISTS uq_edges ON graph_edges (tenant_id, source_id, target_id, relationship);
