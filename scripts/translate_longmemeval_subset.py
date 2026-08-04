#!/usr/bin/env python3
"""Gera subset PT-BR de perguntas do LongMemEval (trabalho FUTURO — ver nota).

⚠️ NOTA (04/08/2026): o runner M5 usa o subset EN original. Perguntas PT contra
sessões EN não recall (FTS/gate lexical por idioma); PT-BR só faz sentido quando
houver um CORPUS DE SESSÕES traduzido (≈50k turnos — esforço grande, fora do v1).
Este script fica como ferramenta para esse trabalho futuro.

Lê evals/data/longmemeval_s_cleaned.json (gitignored), seleciona N perguntas por
tipo (estrato), traduz pergunta+resposta para PT-BR via DeepSeek
(scripts/llm_backend) e salva evals/longmemeval_ptbr.json com os IDs originais.

Uso:  DEEPSEEK_API_KEY=... python3 scripts/translate_longmemeval_subset.py --n 100 [--resume]
"""
import argparse
import json
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "web"))

from llm_backend import call_llm, available  # noqa: E402

DATA = Path(__file__).resolve().parent.parent / "evals" / "data" / "longmemeval_s_cleaned.json"
OUT = Path(__file__).resolve().parent.parent / "evals" / "longmemeval_ptbr.json"

TRANSLATE_PROMPT = """Traduza para português brasileiro (natural, não literal).
Responda SOMENTE com JSON: {{"question": "...", "answer": "..."}}

EN question: {question}
EN answer: {answer}
"""


def _parse(raw: str) -> dict:
    if not raw:
        return {}
    start, end = raw.find("{"), raw.rfind("}") + 1
    if start < 0 or end <= start:
        return {}
    try:
        data = json.loads(raw[start:end])
    except (json.JSONDecodeError, ValueError):
        return {}
    return data if isinstance(data, dict) else {}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=100)
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--dry-local", action="store_true", help="não chama LLM; salva original")
    ap.add_argument("--resume", action="store_true", help="retoma de OUT existente (por id)")
    args = ap.parse_args()

    if not available():
        print("LLM backend indisponível (DEEPSEEK_API_KEY?) — use --dry-local p/ testar pipeline.")
        if not args.dry_local:
            return 1

    done_ids = set()
    if args.resume and OUT.exists():
        done_ids = {i["question_id"] for i in json.load(open(OUT))}
        print(f"Resume: {len(done_ids)} já traduzidas em {OUT}")

    data = json.load(open(DATA))
    random.seed(args.seed)
    by_type: dict = {}
    for inst in data:
        by_type.setdefault(inst["question_type"], []).append(inst)

    total = min(args.n, len(data))
    per = {t: max(1, round(total * len(v) / len(data))) for t, v in by_type.items()}
    picked = []
    for t, count in per.items():
        picked.extend(random.sample(by_type[t], min(count, len(by_type[t]))))
    picked = [p for p in picked if p["question_id"] not in done_ids][: max(total - len(done_ids), 0)]

    out = []
    if args.resume and OUT.exists():
        out = [i for i in json.load(open(OUT)) if i["question_id"] in done_ids]

    for n, inst in enumerate(picked, start=1):
        if args.dry_local:
            out.append({
                "question_id": inst["question_id"],
                "question_type": inst["question_type"],
                "question": inst["question"],
                "answer": inst["answer"],
            })
            continue
        raw = call_llm(TRANSLATE_PROMPT.format(question=inst["question"], answer=inst["answer"]),
                       max_tokens=400, temperature=0, timeout=60)
        t = _parse(raw)
        if not t.get("question") or not t.get("answer"):
            print(f"  [skip tradução] {inst['question_id']}")
            t = {"question": inst["question"], "answer": inst["answer"]}
        out.append({
            "question_id": inst["question_id"],
            "question_type": inst["question_type"],
            "question": t["question"],
            "answer": t["answer"],
        })
        if n % 5 == 0:
            print(f"  {n}/{len(picked)} traduzidas...", flush=True)
            OUT.write_text(json.dumps(out, ensure_ascii=False, indent=2))
    OUT.write_text(json.dumps(out, ensure_ascii=False, indent=2))
    print(f"Salvo {len(out)} instâncias em {OUT} "
          f"({'traduzidas' if not args.dry_local else 'originais (dry)'})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
