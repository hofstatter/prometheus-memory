#!/usr/bin/env python3
"""Extractor (Fase C — Mem0 parity) — extração LLM single-pass, estilo Mem0 V3.

Correção C4: usa `scripts.llm_backend.call_llm` (função real) e respeita o backend
configurado (LLM_BACKEND=deepseek p/ produção; degrada para vazio se indisponível).
"""
import json
import re
import sys
from datetime import date, timedelta
from pathlib import Path

_SCRIPTS = Path(__file__).resolve().parent.parent / "scripts"
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))

from llm_backend import call_llm  # noqa: E402

EXTRACTION_PROMPT = """Você é um Extrator de Memórias. Sua única operação é ADD.
Produza afirmações factuais auto-contidas, em português, com contexto rico (não
atômicas demais) e datas ABSOLUTAS (AAAA-MM-DD) — nunca "hoje/ontem/amanhã".

## Mensagens Novas
{new_messages}

## Memórias Recentes (não re-extrair)
{recently_extracted}

## Memórias Existentes (apenas p/ dedup/linking — não extrair daqui)
{existing_memories}

## Regras
1. Cada fato = 1 linha, auto-contido, sem "ele/ela/isso".
2. Não re-extraia informação já presente acima.
3. Capture transições old -> new quando houver (ex: "X substituiu Y").
4. Em dúvida, extraia (dedup downstream resolve).
5. Formato: JSON array de strings.

Output:"""

_RELATIVE = {
    "semana que vem": 7, "semana passada": -7,
    "amanhã": 1, "amanha": 1, "ontem": -1, "hoje": 0, "agora": 0,
}
_UNIT_DAYS = {"dia": 1, "dias": 1, "semana": 7, "semanas": 7, "mes": 30, "mês": 30, "meses": 30}


def ground_temporal(text: str, today: str = None) -> str:
    """Substitui datas relativas por datas absolutas (ex: "ontem" → YYYY-MM-DD)."""
    d = date.fromisoformat(today) if today else date.today()
    for phrase, days in sorted(_RELATIVE.items(), key=lambda kv: -len(kv[0])):
        target = (d + timedelta(days=days)).isoformat()
        text = re.sub(rf"\b{re.escape(phrase)}\b", target, text, flags=re.IGNORECASE)

    def _ago(m):
        n = int(m.group(1))
        unit = m.group(2).lower()
        return (d - timedelta(days=_UNIT_DAYS.get(unit, 1) * n)).isoformat()

    text = re.sub(r"há\s+(\d+)\s+(dias?|semanas?|meses?|mês)", _ago, text, flags=re.IGNORECASE)
    return text


def _parse(raw: str) -> list:
    if not raw:
        return []
    try:
        start = raw.find("[")
        end = raw.rfind("]") + 1
        if start >= 0 and end > start:
            data = json.loads(raw[start:end])
            if isinstance(data, list):
                return [str(f).strip() for f in data if str(f).strip()]
    except (json.JSONDecodeError, ValueError):
        pass
    lines = []
    for line in raw.splitlines():
        line = re.sub(r"^[\s\d.\-*\[\]\"']+", "", line).strip()
        if len(line) > 10 and not line.startswith(("{", "}", "[")):
            lines.append(line)
    return lines[:10]


def extract_facts(new_messages: str, recently_extracted: list = None,
                  existing_memories: list = None, today: str = None) -> list:
    """Single LLM call → lista de fatos. Retry 2x; vazio se LLM indisponível."""
    prompt = EXTRACTION_PROMPT.format(
        new_messages=new_messages or "(vazio)",
        recently_extracted="\n".join(f"- {m}" for m in (recently_extracted or [])) or "(vazio)",
        existing_memories="\n".join(f"- {m}" for m in (existing_memories or [])) or "(vazio)",
    )
    facts = []
    for _ in range(2):
        raw = call_llm(prompt, max_tokens=1500, temperature=0.2, timeout=45)
        facts = _parse(raw)
        if facts:
            break
    return facts
