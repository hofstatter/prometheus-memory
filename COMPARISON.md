# COMPARISON — Memória para Agentes IA

## Mnemosyne vs MemPalace vs TencentDB vs Prometheus

| | Mnemosyne | MemPalace | TencentDB-Agent-Memory | **Prometheus Memory** |
|---|---|---|---|---|
| Arquitetura | BEAM (3-tier) | Verbatim flat | Pirâmide L0→L3 | **L0→L3 sobre BEAM** |
| LongMemEval | 98.9% | 96.6% | Não publicado | Herda Mnemosyne |
| BEAM 100K | 65.2% | Não publicado | Não publicado | Herda Mnemosyne |
| Compressão | Consolidação (9.4x) | Nenhuma | Canvas (61% tokens) | **Consolidação + Canvas** |
| Hierarquia | Working + Episodic | Flat (Wing→Room→Drawer) | L0→L3 + Canvas | **L0→L3 + Canvas + Persona** |
| Persona/Skills | Persona facts | Não tem | Persona + Skill gen | **Persona + Skill gen + auto-memory** |
| RAG | — | ChromaDB | — | **sqlite-vec + OCR multimodal** |
| Web UI | — | — | — | **7 abas interativas** |
| Stack | Python, SQLite | Python, ChromaDB | Node.js, TypeScript | **Python, SQLite, Flask** |
| Licença | MIT | MIT | MIT | **MIT** |

## O que o Prometheus adiciona ao Mnemosyne

1. **Pirâmide L0→L3 completa** — sessões → fatos → cenas → persona, com
   consolidação automática via cron (6h / semanal)
2. **Mermaid Canvas** — diagrama de estado do agente gerado a cada
   consolidação; substitui outputs verbosos de tools por referências visuais
3. **Offloading de logs** — `ref_manager.py` salva outputs >500 chars em
   disco e troca por `[ref:node_id]` no contexto (até 61% menos tokens)
4. **Skill generation** — detecta padrões recorrentes nas cenas e gera
   skills reutilizáveis em `~/.opencode/skills/generated/`
5. **RAG local multimodal** — PDF/TXT/MD/DOCX/imagens com OCR (Tesseract),
   embeddings multilíngues locais, coleções por projeto
6. **Web UI unificada** — Timeline, Grafo (G6.js), Canvas, Documents, Notes,
   Editor — tudo em uma SPA sem build step
7. **Notes inteligente** — captura de URLs (GitHub, X, sites) com
   sanitização de Markdown e detecção automática de fonte

## Quando usar cada um

- **Mnemosyne puro** — você só precisa de memória persistente via MCP/CLI
- **MemPalace** — você quer recall verbatím (sem compressão)
- **TencentDB** — você está no ecossistema Node.js/TypeScript
- **Prometheus Memory** — você quer o pipeline completo: memória que se
  consolida sozinha, gera persona e skills, com RAG local e interface visual
