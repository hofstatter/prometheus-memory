#!/usr/bin/env python3
"""Atlas Loop — o neurônio pró-ativo da Prometheus-Memory.

Roda 24/7 na VM 101: percebe → decide → age → descansa (backoff 5→60min).
Coexiste com o MCP `atlas_memory_agent` (:8768), que continua servindo os agentes.

Uso:
  python3 atlas_loop.py            # loop infinito (produção, via systemd)
  python3 atlas_loop.py --dry-run  # 1 ciclo, imprime estado/acoes, sem agir
  python3 atlas_loop.py --once     # 1 ciclo real, agindo (teste/smoke)
"""
from __future__ import annotations
import json
import os
import re
import sqlite3
import subprocess
import sys
import threading
import time
import urllib.request
import urllib.error
from datetime import datetime, timezone
from pathlib import Path

# Reusa o módulo do MCP (mesmo diretório): diário, LLM, Mnemosyne, docs scan.
sys.path.insert(0, str(Path(__file__).resolve().parent))
from atlas_memory_agent import (  # noqa: E402
    PERSONA,
    _diario,
    _now_iso,
    _llm,
    _mnemosyne_post,
    _run_mnemosyne_sleep,
    _docs_scan,
    DOCS_DIR,
    MNEMOSYNE_API,
    MNEMOSYNE_TOKEN,
)

BACKOFF = [300, 600, 1200, 2400, 3600]                       # 5,10,20,40,60 min
LLM_BUDGET_DAY = int(os.environ.get("ATLAS_LLM_BUDGET_DAY", "20"))
CONSOLIDAR_MIN = int(os.environ.get("ATLAS_CONSOLIDAR_MIN", "20"))
HEARTBEAT_EVERY = int(os.environ.get("ATLAS_HEARTBEAT_EVERY", "6"))
SLEEP_STALE_S = int(os.environ.get("ATLAS_SLEEP_STALE_S", "360"))  # 6min
SLEEP_COOLDOWN_S = int(os.environ.get("ATLAS_SLEEP_COOLDOWN_S", "86400"))  # 24h
STATE_FILE = Path(os.environ.get("ATLAS_STATE_FILE", "/data/atlas/loop_state.json"))
INTENCOES_FILE = Path(os.environ.get("ATLAS_INTENCOES_FILE", "/data/atlas/intencoes.json"))
PAINEL_API = os.environ.get("ATLAS_PAINEL_API", "http://127.0.0.1:8777")
MNEMOSYNE_DB = os.environ.get(
    "MNEMOSYNE_DB",
    "/var/lib/docker/volumes/prometheus-data/_data/data/mnemosyne.db",
)
DRY_RUN = "--dry-run" in sys.argv
UM_CICLO = "--once" in sys.argv


def log(msg: str) -> None:
    print(f"[{_now_iso()}] {msg}", flush=True)


# ---------- util HTTP ----------
def _http_json(url: str, method: str = "GET", payload: dict | None = None,
               timeout: int = 15, token: str = "") -> dict:
    try:
        data = json.dumps(payload).encode() if payload is not None else None
        headers = {"Content-Type": "application/json"}
        if token:
            headers["Authorization"] = f"Bearer {token}"
        req = urllib.request.Request(url, data=data, method=method, headers=headers)
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return json.loads(r.read().decode())
    except Exception as e:  # noqa: BLE001
        return {"error": str(e)[:200]}


# ---------- estado do loop (orçamento + flags) ----------
def _ler_state() -> dict:
    try:
        return json.loads(STATE_FILE.read_text())
    except Exception:
        return {"dia": "", "llm_calls": 0, "sleep_em_andamento": False}


def _salvar_state(estado: dict) -> None:
    try:
        STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
        STATE_FILE.write_text(json.dumps(estado, ensure_ascii=False, indent=2))
    except OSError as e:
        log(f"state write error: {e}")


def _llm_restante() -> int:
    est = _ler_state()
    hoje = _now_iso()[:10]
    if est.get("dia") != hoje:
        # preserva flags/contadores do ciclo anterior (evita drop de estado)
        est = {"dia": hoje, "llm_calls": 0,
               "sleep_em_andamento": est.get("sleep_em_andamento", False),
               "sleep_ts": est.get("sleep_ts", 0),
               "last_unconsolidated": est.get("last_unconsolidated", 0),
               "last_sleep_ts": est.get("last_sleep_ts", 0)}
        _salvar_state(est)
    return LLM_BUDGET_DAY - int(est.get("llm_calls", 0))


def _llm_consumir() -> None:
    est = _ler_state()
    est["llm_calls"] = int(est.get("llm_calls", 0)) + 1
    _salvar_state(est)


def _llm_orcado(messages: list, max_tokens: int = 400) -> str:
    if _llm_restante() <= 0:
        return ""
    _llm_consumir()
    return _llm(messages, max_tokens)


def _sleep_em_andamento() -> bool:
    est = _ler_state()
    if not est.get("sleep_em_andamento"):
        return False
    ts = float(est.get("sleep_ts", 0) or 0)
    if time.time() - ts > SLEEP_STALE_S:  # flag velha (processo morreu no sleep) → expira
        est["sleep_em_andamento"] = False
        _salvar_state(est)
        return False
    return True


def _set_sleep_flag(valor: bool) -> None:
    est = _ler_state()
    est["sleep_em_andamento"] = valor
    est["sleep_ts"] = time.time() if valor else 0
    _salvar_state(est)


# ---------- percepção (R$0, sem LLM) ----------
def _mnemosyne_stats() -> dict:
    """unconsolidated via leitura direta do SQLite (root acessa o volume docker)."""
    try:
        c = sqlite3.connect(MNEMOSYNE_DB, timeout=10)
        un = c.execute(
            "SELECT COUNT(*) FROM working_memory WHERE consolidated_at IS NULL"
        ).fetchone()[0]
        total = c.execute("SELECT COUNT(*) FROM working_memory").fetchone()[0]
        c.close()
        return {"unconsolidated": int(un or 0), "working": int(total or 0)}
    except Exception as e:  # noqa: BLE001
        log(f"ERRO _mnemosyne_stats (DB inacessivel?): {e}")
        return {"unconsolidated": 0, "error": str(e)[:150]}


def _docs_alterados() -> list:
    docs = _docs_scan()
    diag = _diario()
    try:
        rows = {r["path"]: r["mtime"] for r in
                diag.execute("SELECT path, mtime FROM atlas_docs_index").fetchall()}
    except Exception:  # noqa: BLE001
        rows = {}
    return [d for d in docs if not rows.get(d["path"]) or d["mtime"] > rows[d["path"]]][:10]


def _ler_intencoes() -> list:
    if not INTENCOES_FILE.exists():
        return []
    try:
        data = json.loads(INTENCOES_FILE.read_text())
        return [i for i in data if not i.get("done")][:5]
    except Exception:  # noqa: BLE001
        return []


def _tarefas_abertas() -> list:
    for path in ("/api/pm/tasks", "/api/tasks"):
        r = _http_json(f"{PAINEL_API}{path}", timeout=8)
        if "error" in r:
            continue
        if isinstance(r, list):
            return [t for t in r if t.get("status") in ("doing", "todo")][:5]
        for key in ("tasks", "data"):
            v = r.get(key) if isinstance(r, dict) else None
            if isinstance(v, list):
                return [t for t in v if t.get("status") in ("doing", "todo")][:5]
    return []


def perceber() -> dict:
    return {
        "stats": _mnemosyne_stats(),
        "docs": _docs_alterados(),
        "intencoes": _ler_intencoes(),
        "tarefas": _tarefas_abertas(),
    }


# ---------- decisão (regras + LLM orçado) ----------
def decidir(est: dict) -> list:
    acoes = []
    un = int(est["stats"].get("unconsolidated", 0) or 0)
    if un >= CONSOLIDAR_MIN:
        acoes.append(("consolidar", {"un_atual": un}))
    if est["docs"]:
        acoes.append(("insight", {"docs": est["docs"]}))
    if est["intencoes"]:
        acoes.append(("responder_intencao", {"intencoes": est["intencoes"]}))
    if est["tarefas"] and not acoes:
        acoes.append(("organizar", {"tarefas": est["tarefas"]}))
    return acoes


# ---------- ações (efetores) ----------
def agir_consolidar(un_atual: int) -> str:
    if _sleep_em_andamento():
        return "sleep ja em andamento, pulando"
    est = _ler_state()
    last = int(est.get("last_unconsolidated", 0) or 0)
    last_sleep = float(est.get("last_sleep_ts", 0) or 0)
    # dedup por delta de count OU cooldown temporal (24h) — consolida antigas
    # mesmo sem memória nova (o `mnemosyne sleep` é por idade)
    if un_atual <= last and (time.time() - last_sleep) < SLEEP_COOLDOWN_S:
        return f"nada novo a consolidar (unconsolidated {un_atual} <= last {last})"
    _set_sleep_flag(True)
    try:
        resp = _run_mnemosyne_sleep(timeout=180)
        if "error" in resp:
            return f"erro: {resp['error']}"
        status = resp.get("status") or {}
        itens = int(status.get("items_consolidated", 0) or 0)
        resumo = (f"Consolidacao (loop): status={status.get('status','?')} "
                  f"itens={itens} resumos={status.get('summaries_created','?')} "
                  f"llm={status.get('llm_used','?')}")
        diag = _diario()
        diag.execute("INSERT INTO atlas_diario (ts, entry, kind) VALUES (?,?,'consolidacao')",
                     (_now_iso(), resumo[:500]))
        # lição só se consolidou de fato (evita gastar LLM em no-op)
        if itens > 0 and status.get("status") != "no_op":
            licao = _llm_orcado([{"role": "system", "content": PERSONA + "\nExtraia 1 licao (1 frase) do output."},
                                 {"role": "user", "content": resp["stdout"][-600:]}], max_tokens=150)
            if licao:
                diag.execute("INSERT INTO atlas_diario (ts, entry, kind) VALUES (?,?,'licao')",
                             (_now_iso(), licao[:300]))
        diag.commit()
        return resumo[:200]
    finally:
        est2 = _ler_state()
        est2["last_unconsolidated"] = un_atual  # lembra o count visto → dedup
        est2["last_sleep_ts"] = time.time()     # cooldown temporal (24h)
        _salvar_state(est2)
        _set_sleep_flag(False)


def _reindexar_docs(docs: list) -> None:
    """Upsert dos docs processados em atlas_docs_index (evita re-insight repetido)."""
    diag = _diario()
    diag.execute("""CREATE TABLE IF NOT EXISTS atlas_docs_index (
        path TEXT PRIMARY KEY, projeto TEXT, tipo TEXT, size INTEGER,
        first_line TEXT, mtime TEXT, indexed_at TEXT)""")
    now = _now_iso()
    for d in docs:
        diag.execute(
            "INSERT INTO atlas_docs_index (path, projeto, tipo, size, first_line, mtime, indexed_at) "
            "VALUES (?,?,?,?,?,?,?) ON CONFLICT(path) DO UPDATE SET "
            "projeto=excluded.projeto, tipo=excluded.tipo, size=excluded.size, "
            "first_line=excluded.first_line, mtime=excluded.mtime, indexed_at=excluded.indexed_at",
            (d["path"], d["projeto"], d["tipo"], d["size"], d["first_line"], d["mtime"], now),
        )
    diag.commit()


def agir_insight(docs: list) -> str:
    if _llm_restante() <= 0:
        return "orcamento LLM esgotado, pulando insight"
    if not docs:
        return "sem docs alterados"
    corpus = []
    for d in docs[:5]:
        try:
            txt = (DOCS_DIR / d["path"]).read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        corpus.append(f"### {d['path']} ({d['tipo']}, {d['projeto']})\n"
                      + "\n".join(txt.splitlines()[:60])[:2500])
    if not corpus:
        return "sem conteudo para insight"
    raw = _llm_orcado([
        {"role": "system", "content": PERSONA + "\nVoce analisa a base de documentacao."},
        {"role": "user", "content": ('Produza SOMENTE JSON: {"resumo_por_doc":[{"path":"...","resumo":"1 frase"}],'
                                     '"temas":["3-5"],"links":[{"a":"x","b":"y","relacao":"..."}],'
                                     '"flags":["..."]. Docs:\n\n' + "\n\n".join(corpus))},
    ], max_tokens=2000)
    data = {}
    if raw:
        try:
            m = re.search(r"\{.*\}", raw, re.S)
            data = json.loads(m.group(0)) if m else {"raw": raw[:300]}
        except json.JSONDecodeError:
            data = {"raw": raw[:300]}
    diag = _diario()
    diag.execute("INSERT INTO atlas_diario (ts, entry, kind) VALUES (?,?,'insight-docs')",
                 (_now_iso(), json.dumps(data, ensure_ascii=False)[:500]))
    diag.commit()
    _reindexar_docs(docs)  # marca como processados → não repete o insight
    return f"insight: {len(corpus)} docs analisados"


def agir_conectar() -> str:
    """Conecta memorias relacionadas via graph_link (fallback: registra no diario)."""
    if _llm_restante() <= 0:
        return "orcamento esgotado, pulando conectar"
    resp = _mnemosyne_post("/recall", {"query": "memorias recentes e conexoes", "top_k": 8})
    memorias = _parse_memorias(resp.get("result", ""))
    if len(memorias) < 2:
        return "poucas memorias para conectar"
    pares = _llm_orcado([
        {"role": "system", "content": PERSONA + "\nDada a lista de memorias (ID: content), retorne 2 pares relacionados como JSON [{\"a\":\"ID\",\"b\":\"ID\",\"relacao\":\"...\"}]."},
        {"role": "user", "content": json.dumps(memorias, ensure_ascii=False)[:2000]},
    ], max_tokens=300)
    feitos = 0
    for par in _extrair_pares(pares):
        r = _http_json(f"{MNEMOSYNE_API}/graph_link", method="POST",
                       payload={"source_id": par["a"], "target_id": par["b"],
                                "relationship": par["relacao"]}, token=MNEMOSYNE_TOKEN)
        if "error" not in r:
            feitos += 1
    if feitos == 0 and pares:
        diag = _diario()
        diag.execute("INSERT INTO atlas_diario (ts, entry, kind) VALUES (?,?,'conexoes')",
                     (_now_iso(), pares[:500]))
        diag.commit()
    return f"conectar: {feitos} grafos criados"


def _parse_memorias(raw: str) -> list:
    items, cur = [], {}
    for line in (raw or "").split("\n"):
        line = line.strip()
        if line.startswith("ID:"):
            if cur.get("content"):
                items.append(cur)
            cur = {"id": line.split(":", 1)[1].strip()}
        elif cur and "Content:" in line:
            cur["content"] = line.split("Content:", 1)[1].strip()[:200]
    if cur.get("content"):
        items.append(cur)
    return items


def _extrair_pares(raw: str) -> list:
    if not raw:
        return []
    try:
        m = re.search(r"\[.*\]", raw, re.S)
        data = json.loads(m.group(0)) if m else []
        return [{"a": str(p.get("a", "")), "b": str(p.get("b", "")),
                 "relacao": str(p.get("relacao", "related_to"))[:80]}
                for p in data if isinstance(p, dict) and p.get("a") and p.get("b")]
    except Exception:  # noqa: BLE001
        return []


def agir_organizar(tarefas: list) -> str:
    diag = _diario()
    resumo = (f"Reflexao organizacional: {len(tarefas)} tarefa(s) em andamento detectadas. "
              f"Titulos: {[str(t.get('title', '?'))[:60] for t in tarefas][:3]}")
    diag.execute("INSERT INTO atlas_diario (ts, entry, kind) VALUES (?,?,'organizacao')",
                 (_now_iso(), resumo[:500]))
    diag.commit()
    return resumo[:200]


def agir_responder_intencao(intencoes: list) -> str:
    alvo = intencoes[0]
    pedido = str(alvo.get("pedido", "")).lower()
    resposta = "intencao nao reconhecida"
    if "consolid" in pedido or "consolida" in pedido:
        est_stats = _mnemosyne_stats()
        resposta = agir_consolidar(int(est_stats.get("unconsolidated", 0) or 0))
    elif "stats" in pedido or "status" in pedido:
        est = _mnemosyne_stats()
        resposta = f"stats: {json.dumps(est, ensure_ascii=False)[:300]}"
    elif "diario" in pedido or "diário" in pedido:
        diag = _diario()
        ultimas = [r["entry"][:100] for r in
                   diag.execute("SELECT entry FROM atlas_diario ORDER BY id DESC LIMIT 5").fetchall()]
        resposta = f"diario: {json.dumps(ultimas, ensure_ascii=False)[:400]}"
    elif "insight" in pedido:
        resposta = agir_insight(_docs_alterados())
    # marca resolvido
    try:
        data = json.loads(INTENCOES_FILE.read_text())
        for item in data:
            if item.get("id") == alvo.get("id"):
                item["done"] = True
                item["resposta"] = resposta[:300]
        INTENCOES_FILE.write_text(json.dumps(data, ensure_ascii=False, indent=2))
    except Exception as e:  # noqa: BLE001
        resposta += f" (erro ao marcar resolvido: {e})"
    diag = _diario()
    diag.execute("INSERT INTO atlas_diario (ts, entry, kind) VALUES (?,?,'intencao')",
                 (_now_iso(), f"Respondeu: {pedido[:120]} -> {resposta[:200]}"))
    diag.commit()
    return resposta[:200]


def _heartbeat() -> None:
    diag = _diario()
    diag.execute("INSERT INTO atlas_diario (ts, entry, kind) VALUES (?,?,'heartbeat')",
                 (_now_iso(), "Loop vivo. Neurônio ativo, aguardando estímulos."))
    diag.commit()


EXECUTORES = {
    "consolidar": agir_consolidar,
    "insight": agir_insight,
    "conectar": agir_conectar,
    "organizar": agir_organizar,
    "responder_intencao": agir_responder_intencao,
}


# ---------- arco reflexo (F6): cache + recall PG rápido ----------
_CACHE: dict = {}          # cache do reflexo (TTL)
_CACHE_TTL = 30            # segundos


def _cache_get(key: str):
    item = _CACHE.get(key)
    if item and (time.time() - item[0]) < _CACHE_TTL:
        return item[1]
    return None


def _cache_set(key: str, value) -> None:
    _CACHE[key] = (time.time(), value)
    if len(_CACHE) > 200:  # limpa entradas velhas
        for k in [k for k, v in _CACHE.items() if (time.time() - v[0]) > _CACHE_TTL]:
            _CACHE.pop(k, None)


def _pg_recall(query: str, top_k: int = 3, tenant_id: int = 1) -> list:
    """REFLEXO: recall full-text rápido no PG (multi-tenant) com cache — sem LLM."""
    key = f"recall:{tenant_id}:{query}:{top_k}"
    cached = _cache_get(key)
    if cached is not None:
        return cached
    try:
        import psycopg2
        url = os.environ.get("PROMETHEUS_PG_URL", "").strip()
        if not url:
            return []
        c = psycopg2.connect(url)
        cur = c.cursor()
        cur.execute("SET app.tenant_id = %s", (tenant_id,))
        cur.execute(
            """SELECT id, content,
                      ts_rank(content_tsv, plainto_tsquery('portuguese', %s)) AS r
               FROM working_memory
               WHERE tenant_id=%s AND content_tsv @@ plainto_tsquery('portuguese', %s)
               ORDER BY r DESC, importance DESC LIMIT %s""",
            (query, tenant_id, query, top_k))
        rows = [{"id": r[0], "content": r[1]} for r in cur.fetchall()]
        c.close()
        _cache_set(key, rows)
        return rows
    except Exception:  # noqa: BLE001
        return []


def _disparar_profundo(nome: str, args: dict) -> None:
    """PROFUNDO (LLM) assíncrono: roda em thread daemon — o reflexo não espera."""
    def _run():
        try:
            res = EXECUTORES[nome](**args)
            log(f"PROFUNDO {nome}: {str(res)[:200]}")
        except Exception as e:  # noqa: BLE001
            log(f"ERRO PROFUNDO {nome}: {e}")
    threading.Thread(target=_run, daemon=True).start()


CICLO_LONGO_S = int(os.environ.get("ATLAS_CICLO_LONGO_S", "86400"))  # 24h


def _disparar_ciclo_longo() -> None:
    """DBA + neurônios-espelho + sinapse (24h): roda em thread — profundo."""
    def _run():
        try:
            sys.path.insert(0, str(Path(__file__).resolve().parent))
            from atlas_dba import dba_maintain
            from atlas_synapse import mirror_patterns, query_synapse, sync_synapse
            from persona_l3 import synthesize_all
            d = dba_maintain()
            m = mirror_patterns()
            s = sync_synapse()
            p = synthesize_all()
            diag = _diario()
            diag.execute("INSERT INTO atlas_diario (ts, entry, kind) VALUES (?,?,'dba')",
                         (_now_iso(), f"DBA: analyze {len(d.get('analyze', []))} tabelas | "
                                      f"espelho: {m.get('padroes_espelhados', 0)} padroes | "
                                      f"sinapse: {s.get('sinapses_criadas', 0)} arestas | "
                                      f"personas: {len(p.get('personas', {}))} tenants"))
            diag.commit()
            log(f"PROFUNDO ciclo-longo: DBA ok | espelho {m} | sinapse {s} | persona {p}")
        except Exception as e:  # noqa: BLE001
            log(f"ERRO ciclo-longo: {e}")
    threading.Thread(target=_run, daemon=True).start()


# ---------- loop ----------
def main() -> int:
    nivel = 0
    ciclo = 0
    log(f"Atlas Loop iniciado (dry_run={DRY_RUN}, once={UM_CICLO}, orcamento={LLM_BUDGET_DAY}/dia)")
    while True:
        ciclo += 1
        try:
            est = perceber()
        except Exception as e:  # noqa: BLE001
            log(f"erro na percepcao: {e}")
            time.sleep(BACKOFF[nivel])
            nivel = min(nivel + 1, len(BACKOFF) - 1)
            continue
        acoes = decidir(est)
        if DRY_RUN:
            print(json.dumps({
                "ciclo": ciclo, "nivel_descanso": nivel,
                "acoes": [a[0] for a in acoes],
                "estado": {
                    "unconsolidated": est["stats"].get("unconsolidated"),
                    "docs_alterados": len(est["docs"]),
                    "intencoes": len(est["intencoes"]),
                    "tarefas_abertas": len(est["tarefas"]),
                    "llm_restante": _llm_restante(),
                },
            }, ensure_ascii=False, indent=2))
            return 0
        if acoes:
            nivel = 0
            t0 = time.perf_counter()
            for nome, args in acoes:
                if nome in ("consolidar", "insight", "conectar"):
                    _disparar_profundo(nome, args)   # LLM → assíncrono (não bloqueia)
                else:
                    try:
                        res = EXECUTORES[nome](**args)  # reflexo (sem LLM)
                        log(f"REFLEXO {nome}: {str(res)[:200]}")
                    except Exception as e:  # noqa: BLE001
                        log(f"ERRO REFLEXO {nome}: {e}")
            log(f"ciclo {ciclo}: reflexo {((time.perf_counter() - t0) * 1000):.1f}ms")
            # amostra do recall PG (prova do reflexo rápido)
            if ciclo % 10 == 0:
                try:
                    t1 = time.perf_counter()
                    rows = _pg_recall("postgres", 3)
                    log(f"REFLEXO pg_recall: {len(rows)} itens em "
                        f"{((time.perf_counter() - t1) * 1000):.1f}ms (cache TTL {_CACHE_TTL}s)")
                except Exception as e:  # noqa: BLE001
                    log(f"ERRO pg_recall amostra: {e}")
        else:
            if ciclo % HEARTBEAT_EVERY == 0:
                try:
                    _heartbeat()
                    log(f"heartbeat (ciclo {ciclo}, descanso {BACKOFF[nivel]}s)")
                except Exception as e:  # noqa: BLE001
                    log(f"erro heartbeat: {e}")
        # ciclo longo (DBA + espelho + sinapse) a cada 24h
        try:
            est_s = _ler_state()
            if time.time() - float(est_s.get("last_ciclo_longo", 0) or 0) > CICLO_LONGO_S:
                _disparar_ciclo_longo()
                est_s["last_ciclo_longo"] = time.time()
                _salvar_state(est_s)
                log("ciclo-longo disparado (DBA+espelho+sinapse)")
        except Exception as e:  # noqa: BLE001
            log(f"erro agendamento ciclo-longo: {e}")
        if UM_CICLO:
            return 0
        time.sleep(BACKOFF[nivel])
        nivel = min(nivel + 1, len(BACKOFF) - 1)


if __name__ == "__main__":
    raise SystemExit(main())
