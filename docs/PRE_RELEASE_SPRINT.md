# Sprint Pré-Release — prometheus-memory v0.1.0

**Aprovado por Herbert em 25/07/2026** · Base: auditoria profunda 3 frentes (segurança, escala, completude)

## E1 — P0 Bloqueadores
1. PyMuPDF (AGPL) → **pypdfium2** (BSD) — resolve conflito com LICENSE MIT
2. A1: sanitizar `cid` de coleção RAG (XSS armazenado)
3. A2: escapar `b.code` no md2html (XSS em code blocks)
4. A3: SSRF via redirect — `allow_redirects=False` + revalidar Location
5. C1: token Bearer obrigatório quando `PROMETHEUS_HOST != 127.0.0.1` + disclaimer single-user

## E2 — Quick wins
6. `get_engine()` singleton nas rotas RAG (modelo 100-400MB recarregava por request)
7. `db()` helper: WAL + busy_timeout=5000 + synchronous=NORMAL
8. Índice `rag_chunks(document_id)` + paginação limit/offset
9. systemd: gunicorn + hardening (NoNewPrivileges, ProtectSystem=strict)
10. Erro de LLM NÃO persiste como persona (importance 0.95)
11. Watermark incremental no aggregator (pipeline_state)
12. TimeoutExpired → 503; /health real (DB + fastembed + CLI)
13. scripts/retention.py + cron: refs>90d, sessões>180d→tar.gz, backup diário rotação 7

## E3 — Storage layer
14. `web/storage.py`: interface MemoryStore, backend SQLite (default), Postgres stub (DATABASE_URL) — v0.2 plug-and-play

## E4 — Docs/testes/apresentação
15. Badge Python 3.10+ · "5 abas + editor modal" · nota honesta sqlite-vec · declaração single-store · tabela API REST no README · fix manifest.json 404
16. 6 testes pytest + CI (pytest + pip-audit)
17. Screenshots da UI no README (desbloquear .gitignore)
18. requirements pinados + SECURITY.md

## E5 — Release
19. Verificação completa → commit `chore: pre-release hardening`
20. Push GitHub público + topics + tag v0.1.0 + release
21. docs/ROADMAP.md (v0.2: multi-tenant agent_id, MCP server, vec0 KNN, Postgres backend; v0.3: dedup mem0-style, decay, sharding)
