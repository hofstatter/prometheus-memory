#!/usr/bin/env python3
"""Entity Store (v1.2 — aliases/canonização) — extração LLM + tipos + resolução canônica.

v1.1: extração LLM em lote (person|org|project|tech|other), acrônimos, fallback
heurística v1 (ENTITY_LLM=off ou LLM indisponível).
v1.2: canonical_id — fragmentos ("MiniMax" vs "MiniMax M3") resolvem para um
canônico no write; merge one-shot de duplicatas/lixo legado via merge_entities.py.
"""
import json
import os
import re
import sys
import unicodedata
import uuid
from pathlib import Path

from prometheus_db import get_conn, init_schema

_SCRIPTS_CANDIDATES = [
    Path(__file__).resolve().parent / "scripts",        # deploy produção (~/Projetos/web/scripts)
    Path(__file__).resolve().parent.parent / "scripts", # repo (prometheus-memory/scripts)
]
for _c in _SCRIPTS_CANDIDATES:
    if _c.exists():
        sys.path.insert(0, str(_c))
        break

from llm_backend import call_llm  # noqa: E402

ENTITY_LLM = os.getenv("ENTITY_LLM", "on").lower() in ("1", "on", "true")
VALID_TYPES = {"person", "org", "project", "tech", "other"}

_STOP = {"Para", "Uma", "Um", "O", "A", "Os", "As", "Com", "De", "Da", "Do", "Em",
         "E", "Que", "Na", "No", "Por", "Ao", "Se", "Não", "Nao", "Como", "Mais",
         "Muito", "Tem", "Foi", "Ser", "Hoje", "Ontem", "Agora", "Amanhã"}

ENTITY_PROMPT = """Extraia entidades nomeadas presentes NOS FATOS abaixo.
Use APENAS os tipos: person, org, project, tech, other.
INCLUA acrônimos (ex: FASHN, EVSCAR, MCP, API).
EXCLUA termos genéricos (ex: modelo, projeto, decisão, sistema, memória).
Uma entidade por objeto. Se não houver nenhuma, retorne [].

Formato: JSON array, um objeto por entidade:
[{{"fact": <índice do fato>, "name": "<nome>", "type": "<tipo>"}}]

Fatos:
{numbered_facts}

Output:"""


def extract_entities(text: str) -> set:
    """Heurística v1 (fallback): nomes próprios capitalizados (1-2 tokens)."""
    cands = re.findall(r"\b[A-ZÀ-Ý][a-zà-ÿ0-9.-]{2,}(?: [A-ZÀ-Ý][a-zà-ÿ0-9.-]{2,})?", text or "")
    out = set()
    for c in cands:
        if c.split()[0] in _STOP:
            continue
        out.add(c.strip())
    return out


def normalize_name(name: str) -> str:
    """Normaliza para comparação de aliases: lowercase + sem acentos + pontuação colapsada."""
    n = unicodedata.normalize("NFKD", name or "")
    n = "".join(c for c in n if not unicodedata.combining(c))
    return re.sub(r"[\s\-_.]+", " ", n.lower()).strip()


def resolve_canonical(con, name: str, type_: str):
    """Resolve `name` para uma entidade canônica existente do mesmo type.

    Match exato vence sempre; senão containment (prefixo/sufixo) com canônico =
    nome mais longo. Retorna id ou None (cria nova entidade).
    """
    n = normalize_name(name)
    if not n:
        return None
    rows = con.execute(
        "SELECT id, name FROM prometheus_entities WHERE type = ?", (type_,)
    ).fetchall()
    best = None
    best_len = -1
    for r in rows:
        rn = normalize_name(r["name"])
        if rn == n:
            return r["id"]
        # containment só para nomes ≥3 chars (evita "AI" ⊂ "AIM")
        if min(len(n), len(rn)) >= 3 and (n in rn or rn in n):
            if len(rn) > best_len:
                best = r
                best_len = len(rn)
    return best["id"] if best else None


def _parse_entities(raw: str) -> list:
    """Parse tolerante do JSON do LLM; slice [..] igual ao extractor._parse."""
    if not raw:
        return []
    start, end = raw.find("["), raw.rfind("]") + 1
    if start < 0 or end <= start:
        return []
    try:
        data = json.loads(raw[start:end])
    except (json.JSONDecodeError, ValueError):
        return []
    if not isinstance(data, list):
        return []
    out = []
    for item in data:
        if not isinstance(item, dict):
            continue
        name = str(item.get("name") or "").strip()
        typ = str(item.get("type") or "other").strip().lower()
        try:
            idx = int(item.get("fact"))
        except (TypeError, ValueError):
            idx = -1
        if not name or typ not in VALID_TYPES:
            continue
        out.append({"name": name, "type": typ, "fact": idx})
    return out


def _in_fact(name: str, fact: str) -> bool:
    """Guarda anti-alucinação: só aceita entidade presente no texto do fato."""
    return name.lower() in (fact or "").lower()


def extract_entities_llm(text: str, max_tokens: int = 300) -> list:
    """Extrai entidades via LLM (texto = fatos numerados). Vazio em falha."""
    raw = call_llm(ENTITY_PROMPT.format(numbered_facts=text or "(vazio)"),
                   max_tokens=max_tokens, temperature=0, timeout=45)
    return _parse_entities(raw)


def extract_entities_batch(facts: list) -> dict:
    """1 chamada LLM com fatos numerados → {índice_fato: [entidades]}.

    Entidade só é aceita se name estiver contido em algum fato (substring);
    o índice do LLM é hint: se apontar para o fato errado, faz scan e linka
    no fato que realmente contém o nome.
    """
    numbered = "\n".join(f"{i}. {f}" for i, f in enumerate(facts))
    out: dict = {}
    try:
        ents = extract_entities_llm(numbered)
    except Exception:
        ents = []
    for e in ents:
        idx = e["fact"]
        if 0 <= idx < len(facts) and _in_fact(e["name"], facts[idx]):
            out.setdefault(idx, []).append(e)
        else:
            hit = next((i for i, f in enumerate(facts) if _in_fact(e["name"], f)), None)
            if hit is not None:
                out.setdefault(hit, []).append(e)
    return out


def extract_and_link(memory_id: str, text: str, entities: list = None) -> int:
    """Linka entidades a uma memória. entities=None → LLM ou heurística (fallback)."""
    init_schema()
    con = get_conn()
    linked = 0
    try:
        if entities is None:
            if ENTITY_LLM:
                try:
                    ents = extract_entities_llm(text)
                    entities = [e for e in ents if _in_fact(e["name"], text)]
                except Exception:
                    entities = []
            if not entities:
                entities = [{"name": n, "type": "auto"} for n in extract_entities(text)]
        for ent in entities:
            name = ent["name"]
            typ = ent.get("type") or "auto"
            if typ not in VALID_TYPES:
                typ = "auto"
            # v1.2: resolve para canônico existente do mesmo type antes do lookup
            canonical = resolve_canonical(con, name, typ)
            if canonical is not None:
                c_row = con.execute(
                    "SELECT type FROM prometheus_entities WHERE id = ?", (canonical,)
                ).fetchone()
                if c_row and c_row["type"] == "auto" and typ != "auto":
                    con.execute(
                        "UPDATE prometheus_entities SET type = ?, last_seen = CURRENT_TIMESTAMP, "
                        "mention_count = mention_count + 1 WHERE id = ?", (typ, canonical)
                    )
                else:
                    con.execute(
                        "UPDATE prometheus_entities SET last_seen = CURRENT_TIMESTAMP, "
                        "mention_count = mention_count + 1 WHERE id = ?", (canonical,)
                    )
                eid = canonical
            else:
                row = con.execute(
                    "SELECT id, type FROM prometheus_entities WHERE name = ?", (name,)
                ).fetchone()
                if row:
                    eid = row["id"]
                    if row["type"] == "auto" and typ != "auto":
                        con.execute(
                            "UPDATE prometheus_entities SET type = ?, last_seen = CURRENT_TIMESTAMP, "
                            "mention_count = mention_count + 1 WHERE id = ?", (typ, eid)
                        )
                    else:
                        con.execute(
                            "UPDATE prometheus_entities SET last_seen = CURRENT_TIMESTAMP, "
                            "mention_count = mention_count + 1 WHERE id = ?", (eid,)
                        )
                else:
                    eid = uuid.uuid4().hex[:12]
                    con.execute(
                        "INSERT INTO prometheus_entities (id, name, type) VALUES (?,?, ?)", (eid, name, typ)
                    )
            con.execute(
                "INSERT OR IGNORE INTO prometheus_memory_entities (memory_id, entity_id) VALUES (?,?)",
                (memory_id, eid),
            )
            linked += 1
        con.commit()
    finally:
        con.close()
    return linked


def merge_into(con, alias_id: str, canonical_id: str) -> dict:
    """Funde `alias_id` em `canonical_id`: soma menções, re-linka memórias, marca alias.

    Alias não é deletado (rastreabilidade): fica com canonical_id preenchido.
    """
    alias = con.execute(
        "SELECT name, type, mention_count FROM prometheus_entities WHERE id = ?", (alias_id,)
    ).fetchone()
    if not alias:
        return {"ok": False, "error": "alias nao existe"}
    con.execute(
        "UPDATE prometheus_entities SET mention_count = mention_count + ? WHERE id = ?",
        (alias["mention_count"], canonical_id),
    )
    con.execute(
        """INSERT OR IGNORE INTO prometheus_memory_entities (memory_id, entity_id)
           SELECT memory_id, ? FROM prometheus_memory_entities WHERE entity_id = ?""",
        (canonical_id, alias_id),
    )
    con.execute("DELETE FROM prometheus_memory_entities WHERE entity_id = ?", (alias_id,))
    con.execute(
        "UPDATE prometheus_entities SET canonical_id = ? WHERE id = ?", (canonical_id, alias_id)
    )
    return {"ok": True, "alias": alias["name"], "canonical": canonical_id,
            "mentions_moved": alias["mention_count"]}


def memories_for(entity_name: str) -> list:
    init_schema()
    con = get_conn()
    try:
        rows = con.execute(
            """SELECT me.memory_id FROM prometheus_memory_entities me
               JOIN prometheus_entities e ON e.id = me.entity_id
               WHERE e.name = ?""",
            (entity_name,),
        ).fetchall()
        return [r["memory_id"] for r in rows]
    finally:
        con.close()


def list_entities(limit: int = 100) -> list:
    init_schema()
    con = get_conn()
    try:
        rows = con.execute(
            "SELECT name, type, mention_count, last_seen FROM prometheus_entities "
            "ORDER BY mention_count DESC LIMIT ?",
            (int(limit),),
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        con.close()
