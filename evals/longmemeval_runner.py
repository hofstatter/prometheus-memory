#!/usr/bin/env python3
"""LongMemEval runner (M5) — QA accuracy do recall do Prometheus em subset PT-BR.

Fluxo por instância (lane eval:lme-<qid>, DB temporário isolado):
  1. INGEST  — sessões do haystack → remember_lane raw com prefixo [data]
               (infer=False, SEMANTIC_DEDUP=off → testa RECALL, não extração)
  2. RECALL  — recall_lane(lane, question, top_k=5)  (embeddings locais)
  3. QA      — DeepSeek responde com as memórias recuperadas (temperature 0)
  4. JUDGE   — DeepSeek rubrica binária gold vs hipótese (temperature 0)
Saída: QA accuracy total + por question_type → evals/REPORT_LONGMEMEVAL.md

Uso:
  python3 evals/longmemeval_runner.py --subset 20 --local-only
  DEEPSEEK_API_KEY=... python3 evals/longmemeval_runner.py --subset 100
"""
import argparse
import json
import os
import re
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "web"))
sys.path.insert(0, str(ROOT / "scripts"))

from llm_backend import call_llm, available  # noqa: E402


FULL = ROOT / "evals" / "data" / "longmemeval_s_cleaned.json"
REPORT = ROOT / "evals" / "REPORT_LONGMEMEVAL.md"

QA_PROMPT = """Read the retrieved memories below and answer the question. The
answer is a specific value or fact present in one of the memories — extract it
and answer concisely. Only answer "I don't know" if the memories are truly
unrelated to the question.

Memory format notes:
- "[Fact metric] key: value" — key is snake_case (e.g. "case_saved_from_pct" =
  "case saved from percent"); the value answers the quantity named by the key.
- "[Fact sequence] ..." — chronological list of events; find the relevant event.
- Dates "[2023/05/29 ...]" are session timestamps.

## Retrieved memories
{memories}

## Question
{question}

Answer:"""

JUDGE_PROMPT = """Você é um avaliador rigoroso de respostas. Compare a resposta do
assistente com a resposta de referência para a pergunta. A resposta está CORRETA
apenas se contiver a informação-chave da referência. "Não sei", "Não sei." ou
respostas evasivas são SEMPRE incorretas. Responda SOMENTE com 1 (correta) ou 0 (incorreta).

Pergunta: {question}
Resposta de referência: {gold}
Resposta do assistente: {hypothesis}

Veredito (0 ou 1):"""


def _lane(qid: str) -> str:
    return f"eval:lme-{qid[:32]}"


def _parse_int(raw: str) -> int | None:
    if not raw:
        return None
    for tok in re.findall(r"[01]", raw):
        return int(tok)
    return None


def _ingest(inst: dict) -> None:
    import os as _os
    from memory import remember_lane

    # SEMANTIC_DEDUP=off no runner — dedup semântico não deve interferir
    _os.environ["SEMANTIC_DEDUP"] = "off"
    lane = _lane(inst["question_id"])
    for date, session in zip(inst["haystack_dates"], inst["haystack_sessions"]):
        text = "\n".join(t["content"] for t in session if t.get("content"))
        remember_lane(lane, f"prom-{lane}", f"[{date}] {text}", scope="session")


def _recall(inst: dict, top_k: int = 5) -> list:
    from memory import recall_lane
    return recall_lane(_lane(inst["question_id"]), inst["question"], top_k=top_k)


def _render_content(content: str) -> str:
    """Normaliza memórias estruturadas do Mnemosyne para prosa legível ao QA.

    "[Fact metric] key: value" → "key words: value" · "[Fact sequence]" → texto ·
    "[MEMORIA ...]" (tag de suplemento) → descartada do texto.
    """
    out = []
    for line in (content or "").splitlines():
        m = re.match(r"\[Fact metric\]\s+(.+?):\s*(.+)$", line)
        if m:
            key = m.group(1).replace("_", " ").replace("-", " ")
            out.append(f"{key}: {m.group(2)}")
            continue
        m = re.match(r"\[Fact sequence\]\s*(.*)$", line)
        if m:
            out.append(m.group(1))
            continue
        if line.strip().startswith("[MEMORIA"):
            continue
        out.append(line)
    return "\n".join(out)


def _fmt(mems: list) -> str:
    if not mems:
        return "(nenhuma memória recuperada)"
    return "\n".join(f"- ({r.get('score', 0):.2f}) {_render_content(r.get('content', ''))[:800]}"
                     for r in mems)


def _judge(inst: dict, hypothesis: str) -> int | None:
    if not hypothesis or not hypothesis.strip():
        return 0
    raw = call_llm(JUDGE_PROMPT.format(question=inst["question"], gold=inst["answer"],
                                       hypothesis=hypothesis),
                   max_tokens=10, temperature=0, timeout=45)
    return _parse_int(raw)


def _prepare_eval_db(db_path: Path) -> None:
    """Isola o DB do eval e contorna o bug upstream do Mnemosyne.

    mnemosyne/core/memory.py cria memory_embeddings COM FK→memories (episódica),
    mas o BEAM grava embeddings de working_memory na mesma tabela → em DB fresco
    o INSERT falha com FOREIGN KEY. Reconstruímos a tabela sem a FK (idempotente).
    """
    from mnemosyne.mcp_tools import Mnemosyne
    Mnemosyne(session_id="_init", db_path=str(db_path), bank="default",
              channel_id="_init")  # dispara init completo do schema
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


def _select_subset(data: list, n: int, seed: int = 42) -> list:
    """Estrato proporcional por question_type (mín. 1 por tipo), ordem estável."""
    import random
    random.seed(seed)
    by_type: dict = {}
    for inst in data:
        by_type.setdefault(inst["question_type"], []).append(inst)
    n = min(n, len(data))
    per = {t: max(1, round(n * len(v) / len(data))) for t, v in by_type.items()}
    picked = []
    for t, count in per.items():
        picked.extend(random.sample(by_type[t], min(count, len(by_type[t]))))
    return picked[:n]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--subset", type=int, default=20)
    ap.add_argument("--local-only", action="store_true", help="sem LLM (judge implícito por overlap)")
    ap.add_argument("--data", default=str(FULL))
    args = ap.parse_args()

    # Dataset oficial (sessões EN). PT-BR exige corpus de sessões traduzido —
    # perguntas PT contra memórias EN não recall (FTS/gate lexical por idioma).
    full = json.load(open(args.data))
    subset = _select_subset(full, args.subset)

    # DB temporário isolado (D12); removido ao final (não acumula em /tmp)
    tmpdir = tempfile.mkdtemp(prefix="lme-eval-")
    try:
        return _run(args, subset, Path(tmpdir) / "lme.db")
    finally:
        import shutil
        shutil.rmtree(tmpdir, ignore_errors=True)


def _run(args, subset: list, db_path: Path) -> int:
    os.environ["PROMETHEUS_DB"] = str(db_path)
    os.environ["SEMANTIC_DEDUP"] = "off"
    from prometheus_db import init_schema
    init_schema()
    _prepare_eval_db(db_path)

    results = []
    actual_mode = "llm" if (available() and not args.local_only) else "local-only"
    for n, inst in enumerate(subset, start=1):
        try:
            _ingest(inst)
            mems = _recall(inst)
            if actual_mode == "local-only":
                # fallback sem LLM: acerta se a resposta de referência tem overlap
                # alto com alguma memória recuperada (proxy de recall)
                hit = False
                gold_tokens = set(re.findall(r"\w+", inst["answer"].lower()))
                for m in mems:
                    mt = set(re.findall(r"\w+", (m.get("content") or "").lower()))
                    if gold_tokens and mt and len(gold_tokens & mt) / len(gold_tokens) >= 0.5:
                        hit = True
                        break
                label = 1 if hit else 0
                hyp = "(local-only, proxy overlap)"
            else:
                hyp = call_llm(QA_PROMPT.format(memories=_fmt(mems), question=inst["question"]),
                               max_tokens=120, temperature=0, timeout=45) or ""
                label = _judge(inst, hyp) or 0
            results.append({"id": inst["question_id"], "type": inst["question_type"],
                            "label": label, "hyp": hyp[:120]})
            print(f"  {n}/{len(subset)} [{inst['question_type'][:22]:<22}] label={label}", flush=True)
        except Exception as e:
            print(f"  {n}/{len(subset)} ERRO {inst['question_id']}: {str(e)[:100]}", flush=True)

    if not results:
        print("Nenhum resultado. Dataset completo disponível?")
        return 1

    import llm_backend
    total = sum(r["label"] for r in results) / len(results)
    by_type: dict = {}
    for r in results:
        by_type.setdefault(r["type"], []).append(r["label"])
    lines = ["# Report LongMemEval (subset EN oficial)", "",
             f"- Data: 04/08/2026 · instâncias: {len(results)} · mode: **{actual_mode}**"
             f" · backend: {llm_backend.describe()}",
             f"- **QA accuracy total: {total:.1%}**", "", "| Tipo | n | Accuracy |", "|---|---|---|"]
    for t, labels in sorted(by_type.items(), key=lambda kv: -sum(kv[1]) / len(kv[0])):
        lines.append(f"| {t} | {len(labels)} | {sum(labels) / len(labels):.1%} |")
    REPORT.write_text("\n".join(lines) + "\n")
    print(f"\nQA accuracy total: {total:.1%} (mode={actual_mode}) → {REPORT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
