#!/usr/bin/env python3
"""P5 — Régua PT: hit@5 do recall em memórias reais do ecossistema (PT-BR).

Compara o embedding ATUAL (bge-small-en-v1.5, só EN) com um candidato
multilíngue (ex.: intfloat/multilingual-e5-large) na MESMA sessão —
retrieval puro, sem LLM: acerta se a memória-gold aparece no top-5.

Uso:
  # baseline (modelo atual)
  python3 scripts/eval_pt_recall.py
  # candidato e5-large
  MNEMOSYNE_EMBEDDING_MODEL=intfloat/multilingual-e5-large \
  MNEMOSYNE_EMBEDDING_DIM=1024 python3 scripts/eval_pt_recall.py
  # isolar o efeito do embedding (abaixa o gate lexical upstream):
  P5_BYPASS_LEXICAL=1 python3 scripts/eval_pt_recall.py

Saída: tabela comparativa + append em evals/reports/p5-multilingue-pt.md
"""
import json
import os
import shutil
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "web"))
sys.path.insert(0, str(ROOT / "scripts"))

REPORT = ROOT / "evals" / "reports" / "p5-multilingue-pt.md"

# (pergunta, memória-gold) — fatos reais do ecossistema NB02
CASOS = [
    ("Qual modelo o Visionário usa para analisar imagens?",
     "O Visionário usa o MiniMax M3 com visão nativa para validar screenshots de UI."),
    ("Qual a stack do projeto Evscar?",
     "Evscar roda Next.js com Python IA e Postgres."),
    ("Qual o projeto que roda na porta 8777?",
     "Prometheus Memory roda na porta 8777, cópia de produção com .env de secrets."),
    ("Qual o modelo do Arquiteto na stack v5?",
     "O Arquiteto usa o GLM-5.2 da Zhipu, plano flat de 18 dólares por mês."),
    ("Qual o endereço do repositório do prometheus-memory?",
     "O repositório público é github.com/hofstatter/prometheus-memory."),
    ("Qual o backend de LLM usado pela produção do Prometheus?",
     "A produção usa LLM_BACKEND deepseek com extração de fatos ativa."),
    ("Onde ficam os documentos do ecossistema?",
     "CONTEXT.md e STATE.md ficam em Bytex_AgentOS na pasta Projetos."),
    ("Qual o ID do modelo do Pedreiro?",
     "O Pedreiro usa o deepseek-v4-flash para build de volume."),
    ("Qual a porta do MCP do Mnemosyne?",
     "O MCP do Mnemosyne roda na porta 8765 com bearer bytex-memory-local-2026."),
    ("Qual a versão do kernel da NB02?",
     "O kernel é o 7.0.0-28, rebootado recentemente."),
    ("Qual o nome do MCP de screenshots?",
     "O MCP ScreenshotAPI captura screenshots de URLs via token no .env."),
    ("Qual é a pendência crônica do sistema?",
     "Falta rodar sudo loginctl enable-linger herbert para serviços de usuário no boot."),
    ("Qual o custo mensal do plano do Arquiteto?",
     "O GLM Coding Plan custa 18 dólares por mês flat."),
    ("Qual a chave do sentinela?",
     "A sentinela usa o DeepSeek V4 Flash com DEEPSEEK_API_KEY e log em ~/logs/sentinela.log."),
    ("Qual a stack do Provador?",
     "O Provador roda FastAPI com Caddy nas portas 8000, 8080 e 8081."),
    ("Qual o nome do modelo do Inspetor?",
     "O Inspetor usa o DeepSeek V4 Pro para revisão de código crítico."),
    ("Qual o endereço do MCP da memória local?",
     "O Mnemosyne local responde em localhost 8766 via API."),
    ("Qual o projeto que roda na porta 8085?",
     "O bytex-agentos local roda na porta 8085 com FastAPI e Next.js."),
    ("Qual a porta da interface web do Prometheus?",
     "A interface web do Prometheus Memory está na porta 8777."),
    ("Qual o modelo do Ollama que ficou desativado?",
     "O qwen3 4b instruct foi mantido no disco quando o Ollama foi desativado."),
    ("Qual o banco de dados usado pelo RAG do Prometheus?",
     "O RAG local usa sqlite-vec com fastembed, sem Postgres."),
    ("Qual a porta do canvas do Mnemosyne?",
     "O canvas em Mermaid é servido pelo MCP do Mnemosyne."),
    # ── Casos SEMANTIC-ONLY (sem overlap de tokens pergunta↔gold) ──
    # Exercitam de verdade o embedding: o FTS5 lexical não acha por keywords.
    ("Quem valida as telas dos projetos?",
     "O MiniMax M3 analisa screenshots com visão nativa para revisão de interface."),
    ("Qual serviço deixa o sistema responder perguntas de forma estruturada?",
     "O MCP do Mnemosyne em localhost 8765 resolve dúvidas via busca na memória."),
    ("Em qual número a gente conversa com a máquina de lembranças?",
     "O endpoint de API da memória responde na porta 8766."),
    ("Que ferramenta transforma documentos em vetores para busca por significado?",
     "O fastembed gera embeddings ONNX localmente, sem enviar dados para fora."),
    ("Qual programa acorda o sistema a cada meia hora?",
     "A sentinela em python roda por timer e escreve em ~/logs/sentinela.log."),
    ("Quem constrói a maior parte do código nas tarefas?",
     "O Pedreiro usa o deepseek-v4-flash para implementação de volume."),
    ("Onde o projeto guarda o registro do estado das sessões?",
     "O arquivo STATE.md em Bytex_AgentOS documenta onde cada sessão parou."),
    ("Qual deles cria os planos antes de qualquer código?",
     "O Arquiteto com GLM-5.2 planeja fases antes do Pedreiro executar."),
    ("Que número usamos para abrir o painel da memória no navegador?",
     "A interface web do Prometheus Memory está na porta 8777."),
    ("Qual mecanismo impede guardar duas vezes o mesmo fato?",
     "A deduplicação semântica rejeita memórias duplicadas com score acima do limiar."),
]


def _prepare_db(db_path: Path) -> None:
    """Mesmo contorno de FK do runner LongMemEval (bug upstream)."""
    from mnemosyne.mcp_tools import Mnemosyne
    Mnemosyne(session_id="_init", db_path=str(db_path), bank="default", channel_id="_init")
    import sqlite3
    con = sqlite3.connect(str(db_path))
    con.execute("PRAGMA foreign_keys=OFF")
    con.execute("DROP TABLE IF EXISTS memory_embeddings")
    con.execute("""CREATE TABLE memory_embeddings (
        memory_id TEXT PRIMARY KEY,
        embedding_json TEXT NOT NULL,
        model TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)""")
    con.commit()
    con.close()


def _run() -> dict:
    import tempfile as _tf

    tmpdir = _tf.mkdtemp(prefix="p5-pt-eval-")
    try:
        db_path = Path(tmpdir) / "p5.db"
        # IMPORTANTE: setar env ANTES de importar web/memory.py — DB_PATH é
        # congelado no import (módulo nível). Sem isso o eval escreve no DB real.
        os.environ["PROMETHEUS_DB"] = str(db_path)
        os.environ["SEMANTIC_DEDUP"] = "off"
        if os.environ.get("P5_BYPASS_LEXICAL", "").lower() in ("1", "true", "on"):
            # Isola o efeito do EMBEDDING: o gate lexical upstream (beam.py
            # _lexical_relevance, hardcoded, sem knob) zera candidatos sem
            # overlap de tokens — o vetor nunca é exercitado. Monkeypatch em
            # runtime (não toca site-packages) devolve 0.25 de piso quando
            # existe overlap parcial, deixando o dense score decidir o ranking.
            import mnemosyne.core.beam as _beam
            _orig = _beam._lexical_relevance
            def _relaxed(qtokens, content, query_lower=""):
                base = _orig(qtokens, content, query_lower)
                if base > 0:
                    return base
                return 0.25  # piso: candidato sobrevive ao gate, vetor decide
            _beam._lexical_relevance = _relaxed
        from prometheus_db import init_schema
        from memory import remember_lane, recall_lane
        init_schema()
        _prepare_db(db_path)

        # ingest raw (infer=False) de todas as memórias-gold numa lane só
        lane = "eval:p5-pt"
        for i, (_q, gold) in enumerate(CASOS):
            remember_lane(lane, f"prom-p5-{i}", gold, scope="session")

        # hot: model carregado antes da cronometragem (embed de recall)
        recall_lane(lane, CASOS[0][0], top_k=5)

        hits = 0
        latencies = []
        per = []
        for i, (q, gold) in enumerate(CASOS):
            t0 = time.perf_counter()
            mems = recall_lane(lane, q, top_k=5)
            lat = (time.perf_counter() - t0) * 1000
            latencies.append(lat)
            found = any((m.get("content") or "") == gold or gold in (m.get("content") or "")
                        for m in mems)
            hits += int(found)
            per.append({"q": q, "hit": found, "lat_ms": round(lat, 1),
                        "top": [ (m.get("content") or "")[:60] for m in mems]})
            print(f"  {i+1}/{len(CASOS)} hit={int(found)} lat={lat:.0f}ms", flush=True)

        total = len(CASOS)
        return {
            "hits": hits, "total": total, "acc": hits / total,
            "lat_p50": sorted(latencies)[len(latencies)//2],
            "lat_max": max(latencies),
            "model": os.environ.get("MNEMOSYNE_EMBEDDING_MODEL", "BAAI/bge-small-en-v1.5 (default)"),
            "per": per,
        }
    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)


def _render(res: dict) -> str:
    return (f"- model: `{res['model']}` · **hit@{len(res['per'])} = {res['hits']}/{res['total']}"
            f" ({res['acc']:.1%})** · latência p50 {res['lat_p50']:.0f}ms · máx {res['lat_max']:.0f}ms")


def main() -> int:
    res = _run()
    print("\n" + _render(res))

    existing = []
    if REPORT.exists():
        existing = REPORT.read_text().splitlines()
    header = "# P5 — Régua PT: recall hit@5 (mesma sessão, retrieval puro)\n\n"
    body = "\n".join(existing)
    if not body.strip():
        body = header
    entry = (f"\n- {time.strftime('%Y-%m-%d %H:%M')} — {_render(res)}"
             f"\n  - acertos: {res['hits']}/{res['total']}\n")
    with open(REPORT, "w") as fh:
        fh.write(body if body != header else header)
        if body != header:
            fh.write("\n")
        fh.write(entry)
    return 0


if __name__ == "__main__":
    sys.exit(main())
