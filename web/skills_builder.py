#!/usr/bin/env python3
"""Skills Builder (Fase B) — skills por projeto com aprovação humana.

Detecta padrões em eventos/memórias do projeto → gera skill DRAFT (nunca ativa
sem aprovação humana) com evidências. Promoção: skill active reutilizada em 2+
projetos vira candidata a global. Sidecar prometheus_skills (não toca o registry
global `skills`, que tem name como PK).
"""
import hashlib
import json
import re
import uuid
from datetime import datetime, timedelta
from pathlib import Path

from prometheus_db import get_conn, init_schema

MIN_EVIDENCE = 3
MIN_TOKEN_LEN = 4
EVIDENCE_DAYS = 30
CONF_BASE = 0.5
CONF_STEP = 0.05
CONF_MAX = 0.8


def _now() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")


def _checksum(content: str) -> str:
    return hashlib.sha256(content.encode("utf-8")).hexdigest()[:12]


def slugify_name(topic: str) -> str:
    s = re.sub(r"[^a-z0-9-]", "-", topic.lower()).strip("-")
    return s[:48] or "skill"


def _topic_from_events(rows: list) -> str | None:
    """Maior token comum (len>=4) presente em MIN_EVIDENCE+ títulos."""
    token_count: dict = {}
    token_titles: dict = {}
    for r in rows:
        tokens = {t.lower() for t in re.findall(r"[a-zA-ZÀ-ÿ0-9]{4,}", r["title"] or "")}
        for t in tokens:
            if t in ("implementacao", "implementation", "implementa", "implementar",
                     "fix", "decisao", "decisão", "bug", "issue", "plan", "para",
                     "configura", "configurar", "config", "pesquisa", "testa", "testar",
                     "otimiza", "adiciona", "adicionar", "cria", "criar", "faz", "fazer"):
                continue
            token_count[t] = token_count.get(t, 0) + 1
            token_titles.setdefault(t, []).append(r["title"])
    best = max(token_count.items(), key=lambda kv: kv[1]) if token_count else None
    if best and best[1] >= MIN_EVIDENCE:
        return best[0]
    return None


def _evidence_from_events(rows: list, topic: str) -> list:
    out = []
    for r in rows:
        if topic in (r["title"] or "").lower():
            out.append({"event_id": r["id"], "title": r["title"], "event_type": r["event_type"],
                        "created_at": r["created_at"]})
        if len(out) >= 10:
            break
    return out


def _skill_content(project_slug: str, topic: str, evidence: list) -> str:
    bullets = "\n".join(f"- {e['title']} ({e['event_type']}, {e['created_at']})" for e in evidence)
    return f"""---
name: {slugify_name(topic)}
description: >
  Skill autogerada para o projeto {project_slug} a partir do padrão "{topic}".
  Revisada antes de ativar (draft → active exige aprovação humana).
source: prometheus-skills-builder
project: {project_slug}
---

# {slugify_name(topic)} — {project_slug}

## Contexto do projeto
Padrão detectado em {len(evidence)} eventos recentes do projeto {project_slug}.

## Evidências
{bullets}

## Regras
1. Use este contexto para tarefas relacionadas a "{topic}".
2. Adicione exemplos práticos após a aprovação.
3. Promova para global somente quando reutilizado em 2+ projetos.
"""


def _existing(project_slug: str, name: str) -> dict | None:
    init_schema()
    con = get_conn()
    try:
        row = con.execute(
            "SELECT id, status FROM prometheus_skills WHERE project_slug = ? AND name = ? LIMIT 1",
            (project_slug, name),
        ).fetchone()
        return dict(row) if row else None
    finally:
        con.close()


def suggest_skill(project_slug: str) -> dict | None:
    """Detecta padrão nos eventos do projeto e cria/retorna DRAFT. Idempotente."""
    init_schema()
    cutoff = (datetime.now() - timedelta(days=EVIDENCE_DAYS)).strftime("%Y-%m-%d %H:%M:%S")
    con = get_conn()
    try:
        rows = con.execute(
            "SELECT id, title, event_type, created_at FROM prometheus_project_events "
            "WHERE project_slug = ? AND created_at >= ? ORDER BY created_at DESC LIMIT 200",
            (project_slug, cutoff),
        ).fetchall()
    finally:
        con.close()

    topic = _topic_from_events(rows)
    if not topic:
        return None
    name = slugify_name(topic)
    existing = _existing(project_slug, name)
    if existing:
        return {**existing, "project_slug": project_slug, "name": name, "duplicate": True}

    evidence = _evidence_from_events(rows, topic)
    count = len(evidence)
    confidence = round(min(CONF_BASE + CONF_STEP * (count - MIN_EVIDENCE), CONF_MAX), 2)
    content = _skill_content(project_slug, topic, evidence)
    benefits = _benefits(project_slug, topic, evidence)
    skill_id = uuid.uuid4().hex[:12]
    now = _now()
    con = get_conn()
    try:
        con.execute(
            """INSERT INTO prometheus_skills
               (id, project_slug, name, description, content, scope, status, confidence,
                evidence_json, source, version, checksum, created_at, updated_at)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (skill_id, project_slug, name,
             f"Skill autogerada p/ {project_slug}: padrão '{topic}'", content,
             "project", "draft", confidence,
             json.dumps(evidence, ensure_ascii=False), "builder", 1, _checksum(content),
             now, now),
        )
        con.commit()
    finally:
        con.close()
    return {"id": skill_id, "project_slug": project_slug, "name": name, "status": "draft",
            "confidence": confidence, "evidence_count": count, "duplicate": False,
            "topic": topic, "benefits": benefits, "evidence": evidence}


def _benefits(project_slug: str, topic: str, evidence: list) -> list:
    """Benefícios concretos da skill para o projeto (P5.6) — derivados das evidências."""
    if not evidence:
        return []
    types = {}
    for e in evidence:
        types[e.get("event_type", "work")] = types.get(e.get("event_type", "work"), 0) + 1
    most = max(types.items(), key=lambda kv: kv[1])[0] if types else "work"
    kind = {
        "implementation": "implementação", "planning": "planejamento",
        "review": "revisão", "fix": "correção", "decision": "decisão",
        "docs": "documentação", "work": "trabalho",
    }.get(most, most)
    n = len(evidence)
    return [
        f"Padrão '{topic}' recorrente: {n} ocorrência(s) recentes no projeto {project_slug} — a skill captura o procedimento para não re-descobrir do zero.",
        f"Foco principal: {kind} — aplicar a skill reduz tempo de setup e mantém consistência com o histórico do projeto.",
        f"Evidências disponíveis: {n} evento(s) indexado(s) como base de exemplos reais (revisar antes de ativar).",
        "Reuso: quando a mesma skill servir a 2+ projetos, candidata a promoção global (fluxo automático).",
    ]


def list_skills(project_slug: str | None = None, status: str | None = None) -> list:
    init_schema()
    con = get_conn()
    try:
        sql = ("SELECT id, project_slug, name, description, scope, status, confidence, "
               "evidence_json, version, checksum, created_at, updated_at, last_used_at, use_count "
               "FROM prometheus_skills")
        clauses, params = [], []
        if project_slug:
            clauses.append("project_slug = ?")
            params.append(project_slug)
        if status:
            clauses.append("status = ?")
            params.append(status)
        if clauses:
            sql += " WHERE " + " AND ".join(clauses)
        sql += " ORDER BY updated_at DESC"
        rows = con.execute(sql, params).fetchall()
    finally:
        con.close()
    return [dict(r, evidence=json.loads(r["evidence_json"] or "[]")) for r in rows]


def approve_skill(skill_id: str) -> dict | None:
    """Aprovação humana: draft → active."""
    init_schema()
    con = get_conn()
    try:
        row = con.execute("SELECT id, status FROM prometheus_skills WHERE id = ?", (skill_id,)).fetchone()
        if not row or row["status"] != "draft":
            return None
        con.execute("UPDATE prometheus_skills SET status = 'active', updated_at = ? WHERE id = ?",
                    (_now(), skill_id))
        con.commit()
    finally:
        con.close()
    return {"id": skill_id, "status": "active"}


def mark_used(skill_id: str) -> dict | None:
    init_schema()
    con = get_conn()
    try:
        cur = con.execute(
            "UPDATE prometheus_skills SET use_count = use_count + 1, last_used_at = ? WHERE id = ?",
            (_now(), skill_id),
        )
        con.commit()
        ok = cur.rowcount > 0
    finally:
        con.close()
    return {"id": skill_id, "used": ok}


def promotion_candidates() -> list:
    """Skills active reutilizadas (mesmo nome) em 2+ projetos."""
    init_schema()
    con = get_conn()
    try:
        rows = con.execute(
            """SELECT name, COUNT(DISTINCT project_slug) AS n_projects,
                      GROUP_CONCAT(DISTINCT project_slug) AS projects
               FROM prometheus_skills WHERE status = 'active'
               GROUP BY name HAVING n_projects >= 2 ORDER BY n_projects DESC"""
        ).fetchall()
    finally:
        con.close()
    return [{"name": r["name"], "n_projects": r["n_projects"], "projects": (r["projects"] or "").split(",")}
            for r in rows]
