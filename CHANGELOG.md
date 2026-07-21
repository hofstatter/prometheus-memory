# Changelog

## [0.1.0] — 2026-07-21

### Adicionado
- Pipeline L0→L3 completo (session logger, aggregator, persona synthesizer, skill generator, ref manager)
- Web UI unificada na porta 8777 com 6 abas: Timeline, Grafo (G6.js), Canvas (Mermaid), Documents (RAG), Notes, Editor
- RAG local multimodal: PDF/TXT/MD/DOCX/PNG/JPG com OCR (PyMuPDF + Tesseract)
- Notes: importação por URL com detecção de fonte (GitHub, X, web) e sanitização de Markdown
- Offloading de logs com `ref_manager.py` (refs/*.md + node_id)
- Skill auto-memory para agentes (gravação automática de sessões)
- Instalação em 1 comando via `setup.sh` (deps, cron, systemd)
- Configuração 100% por variáveis de ambiente

### Segurança
- Proteção contra path traversal nos endpoints de Notes
- Proteção SSRF na importação de URLs (apenas http/https públicos)
- Bind padrão em 127.0.0.1
- Nenhuma chave de API no código-fonte
- Escape de HTML na renderização (XSS) e Mermaid `securityLevel: 'strict'`
- Allowlist de extensões e limite de 50MB no upload RAG
