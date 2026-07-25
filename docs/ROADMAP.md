# ROADMAP — Prometheus Memory

## v0.1.0 (atual) ✅
Pipeline L0→L3 · Web UI 5 abas + editor · RAG multimodal + OCR · Notes · Offloading · Skills · Hardening pré-release

## v0.2 — Multi-agente & API
- [ ] **`agent_id`/`session_id`** em todo recall/write (isolamento entre agentes, padrão mem0)
- [ ] **MCP server** (padrão dominante 2026) + `POST /api/memory` (remember/recall via REST, matar subprocess+regex)
- [ ] **Backend PostgreSQL** completo via `web/storage.py` (`DATABASE_URL`) + pgvector (HNSW) para tabelas do Prometheus
- [ ] **sqlite-vec `vec0` KNN** (busca vetorial real até ~1M vetores; hoje: cosine brute-force)
- [ ] Fila assíncrona de indexing (upload → 202, worker processa)
- [ ] Retries + circuit breaker nas chamadas LLM; métricas `/metrics`
- [ ] FTS5 para busca de notas

## v0.3 — Escala & Inteligência
- [ ] Dedup semântico estilo mem0 (ADD/UPDATE/DELETE/NOOP via LLM)
- [ ] Decay/eviction de memórias (políticas estilo Letta core/archival)
- [ ] Consolidação orientada a eventos (fila) em vez de cron
- [ ] Sharding por agente; particionamento de rag_chunks
- [ ] Harness de eval (LongMemEval) no CI
- [ ] Decisão sobre Mnemosyne core: propor Postgres upstream ou engine própria

## Contexto da auditoria (25/07/2026)
Para o propósito declarado (single-user local-first), a arquitetura SQLite atual é coerente.
Cenário de 100k agentes exige os itens v0.2/v0.3 — não é tuning, é re-arquitetura planejada.
