#!/usr/bin/env python3
"""Eval próprio do pipeline L1→L2 (cenas) — mede o claim central do Prometheus Memory.

Roda a síntese de cena para 20 cenários (evals/scenarios.json) e avalia cada cena
com judge LLM (rubrica objetiva 0-100):
  - relevância: a cena cobre os fatos?
  - fidelidade: tudo na cena vem dos fatos (sem alucinação)?
  - formato: segue "[projeto] cena [tema]: [descricao]"?

Saída: score composto 0-100 + evals/REPORT.md detalhado.
Uso: python3 scripts/eval_pipeline.py [--backend ollama|deepseek]
"""
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from llm_backend import call_llm, available, describe

SCENARIOS = Path(__file__).resolve().parent.parent / "evals" / "scenarios.json"
REPORT = Path(__file__).resolve().parent.parent / "evals" / "REPORT.md"

JUDGE_RUBRIC = """Voce e um avaliador objetivo de qualidade de consolidacao de memoria.
Avalie a CENA gerada a partir dos FATOS abaixo com 3 criterios (0-100 cada):
1. RELEVANCIA: a cena cobre os pontos principais dos fatos?
2. FIDELIDADE: tudo na cena vem dos fatos (zero alucinacao/conteudo inventado)?
3. FORMATO: segue "[projeto] cena [tema]: [descricao]" e e concisa?

Responda APENAS JSON: {"relevancia": N, "fidelidade": N, "formato": N, "justificativa": "1 linha"}

FATOS:
{facts}

CENA:
{scene}"""


def synthesize_scene(project: str, facts: list) -> str:
    facts_text = "\n".join(f"- {f[:300]}" for f in facts)
    prompt = f"""Resuma estes fatos em uma cena tematica concisa (max 100 palavras).
Use portugues brasileiro. Formato: "[{project}] cena [tema-resumido]: [descricao]"

Fatos:
{facts_text}
"""
    return call_llm(prompt, max_tokens=200, temperature=0.3, timeout=30)


def judge(facts: list, scene: str) -> dict:
    prompt = JUDGE_RUBRIC.replace("{facts}", "\n".join(f"- {f}" for f in facts)).replace("{scene}", scene)
    raw = call_llm(prompt, max_tokens=200, temperature=0.1, timeout=30)
    try:
        start = raw.find("{")
        end = raw.rfind("}") + 1
        return json.loads(raw[start:end])
    except Exception:
        return {"relevancia": 0, "fidelidade": 0, "formato": 0, "justificativa": f"judge falhou: {raw[:80]}"}


def main():
    scenarios = json.loads(SCENARIOS.read_text())
    backend = describe()
    if not available():
        print(f"❌ backend LLM indisponivel: {backend}")
        sys.exit(1)

    print(f"🔥 Eval pipeline L1→L2 — backend: {backend}")
    print(f"   {len(scenarios)} cenários\n")

    results = []
    total_rel = total_fid = total_fmt = 0

    for sc in scenarios:
        facts = sc["facts"]
        scene = synthesize_scene(sc["project"], facts)
        if not scene:
            results.append({**sc, "scene": "(falha síntese)", "relevancia": 0, "fidelidade": 0, "formato": 0, "score": 0, "justificativa": "síntese falhou"})
            continue
        j = judge(facts, scene)
        score = round((j["relevancia"] + j["fidelidade"] + j["formato"]) / 3)
        total_rel += j["relevancia"]
        total_fid += j["fidelidade"]
        total_fmt += j["formato"]
        results.append({**sc, "scene": scene, "relevancia": j["relevancia"], "fidelidade": j["fidelidade"], "formato": j["formato"], "score": score, "justificativa": j.get("justificativa", "")})
        print(f"  [{sc['id']:2d}] score {score:3d} | {scene[:70]}")

    n = len(results)
    composite = round((total_rel + total_fid + total_fmt) / (n * 3)) if n else 0
    print(f"\n{'='*50}")
    print(f"📊 SCORE COMPOSTO: {composite}/100")
    print(f"   relevância: {round(total_rel/n)} | fidelidade: {round(total_fid/n)} | formato: {round(total_fmt/n)}")

    REPORT.write_text(f"""# Eval Report — Prometheus Memory L1→L2

**Backend:** {backend} · **Cenários:** {n}

## Score composto: **{composite}/100**

| Critério | Média |
|---|---|
| Relevância | {round(total_rel/n)}/100 |
| Fidelidade | {round(total_fid/n)}/100 |
| Formato | {round(total_fmt/n)}/100 |

## Por cenário

| # | Score | Cena | Justificativa |
|---|---|---|---|
""" + "\n".join(
        f"| {r['id']} | {r['score']} | {r['scene'][:80]} | {r['justificativa'][:60]} |"
        for r in results
    ) + "\n")
    print(f"📄 relatório: {REPORT}")
    return composite


if __name__ == "__main__":
    main()
