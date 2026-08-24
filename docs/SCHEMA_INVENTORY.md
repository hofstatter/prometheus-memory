# SCHEMA INVENTORY — Mnemosyne + Prometheus sidecar (F0, 24/08/2026)

**Fonte:** `/var/lib/docker/volumes/prometheus-data/_data/data/mnemosyne.db` (SQLite, VM 101)
**Total:** 85 tabelas · **Objetivo:** base para a migração SQLite → PostgreSQL (pgvector + tsvector)

## 1. Core Mnemosyne (L0-L3)

| Tabela | Camada | Colunas principais | PG alvo |
|---|---|---|---|
| `working_memory` | L1 | id, content, source, timestamp, session_id, importance, metadata_json, veracity, created_at, memory_type, consolidated_at, recall_count, pinned, scope, author_id, channel_id, trust_tier, validated_at, temporal_tags, corrected_by (30 cols) | `tenant_id` + index (created_at, channel_id) |
| `episodic_memory` | L2 | id, content, summary_of, tier, degraded_at, binary_vector, recall_count, author_id, channel_id (31 cols) | `tenant_id` + pgvector |
| `memories` | L1 alt | — | `tenant_id` |
| `facts` / `consolidated_facts` / `canonical_facts` / `memoria_facts` | L3/fatos | — | `tenant_id` |
| `gists` | Lições | — | `tenant_id` |
| `triples` | Grafo (SPO) | subject, predicate, object | `tenant_id` + index (predicate) |
| `graph_edges` | Grafo | source_id, target_id, relationship, weight | `tenant_id` |
| `memory_embeddings` | Vetores | memory_id, embedding_json, model | → pgvector (vetor em `vec_*`) |
| `memoria_kg` / `memoria_persona` / `memoria_preferences` / `memoria_timelines` / `memoria_instructions` | Mem0-like | — | `tenant_id` |
| `scratchpad` / `skills` / `annotations` / `conflicts` / `consolidation_log` / `memory_events` / `memory_validations` / `audit_log` | Apoio | — | `tenant_id` |

## 2. Vetores (sqlite-vec → pgvector)

| Tabela vec0 atual | PG alvo |
|---|---|
| `vec_working*` (vec_working + _chunks/_info/_rowids/_vector_chunks00) | `vec_working(embedding vector(384))` com índice **HNSW** |
| `vec_episodes*` | `vec_episodes(embedding vector(384))` HNSW |
| `vec_facts*` | `vec_facts(embedding vector(384))` HNSW |
| `vec_chunks*` (RAG) | `vec_chunks(embedding vector(384))` HNSW |

> ⚠️ Confirmado: o sqlite-vec usa a extensão `vec0` (erro "no such module: vec0" ao consultar sem a extensão). Embeddings atuais: **384d** (fastembed MiniLM-L12 multilíngue).

## 3. Full-text (FTS5 → tsvector)

| FTS5 atual | PG alvo |
|---|---|
| `fts_working*`, `fts_episodes*`, `fts_facts*` | `tsvector` + índice **GIN** por tabela |
| `notes_fts*` | `tsvector` + GIN |

## 4. Sidecar prometheus_* (Web UI :8777) — hoje SQLite mesmo arquivo

| Tabela | Função | PG alvo |
|---|---|---|
| `prometheus_projects` | projetos | `tenant_id` |
| `prometheus_project_events` | eventos por projeto | `tenant_id` + index (project_slug, created_at) |
| `prometheus_project_tasks` | tarefas/kanban | `tenant_id` + index (project_slug, status) |
| `prometheus_sessions` | sessões/presença | `tenant_id` + index (last_seen_at) |
| `prometheus_events_ingest` | ingest idempotente | `tenant_id` + UNIQUE(client_event_id) |
| `prometheus_connections` | conexões/custos | `tenant_id` + index (fingerprint) |
| `prometheus_tech_profile` | stack/runtime | `tenant_id` |
| `prometheus_skills` | skills por projeto | `tenant_id` + index (status) |
| `prometheus_dedup_hashes` | dedup SHA-256 | `tenant_id` + UNIQUE(channel, hash) |
| `prometheus_entities` / `prometheus_memory_entities` | entidades/linking | `tenant_id` + index (name, canonical_id) |
| `prometheus_project_reports` / `prometheus_reports_daily` | relatórios | `tenant_id` |
| `prometheus_meta` | metadata | `tenant_id` |
| `rag_collections` / `rag_documents` / `rag_chunks` | RAG | `tenant_id` + pgvector em chunks |

## 5. Próximos passos da migração (F1+)

1. **F1** — PG:16 + `pgvector` + `pgBouncer` na VM 101 (container).
2. **F2** — backend PG do core (SQLAlchemy Core): rewrite de recall (pgvector KNN + tsvector), store, sleep (consolidação), graph, triples.
3. **F3** — sidecar `prometheus_*` em PG (o `prometheus_db.py` troca o driver sqlite3 → SQLAlchemy/PG).
4. **F4** — dump SQLite → transform → `psql` (com `tenant_id=default`); espelho 1 semana; SQLite desligado (arquivo mantido).
5. **F5** — multi-tenant + RLS + Auth Gateway (tenants/agents/api_keys).
