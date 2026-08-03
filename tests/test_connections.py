"""Testes Fase A2 — Conexões & Custos: scan .env (read-only), fingerprint, alertas, summary.

Env isolado por teste (monkeypatch) — imune à poluição entre arquivos de teste.
"""
import importlib
import os
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "web"))

_TEST_ROOT = Path("/tmp/test-conn-root")
_EV = _TEST_ROOT / "evscar"
_PV = _TEST_ROOT / "provador"
for d in (_EV, _PV):
    d.mkdir(parents=True, exist_ok=True)
(_EV / ".env").write_text(
    "DEEPSEEK_API_KEY=sk-compartilhada\nOCM_API_KEY=ocm-mapa-123\nDB_PASSWORD=senha-interna\nNAO_E_CHAVE=valor\n"
)
(_PV / ".env").write_text(
    "DEEPSEEK_API_KEY=sk-compartilhada\nFASHN_API_KEY=fashn-moda-456\n"
)


@pytest.fixture(autouse=True)
def _env(monkeypatch):
    monkeypatch.setenv("PROMETHEUS_DB", "/tmp/test-conn.db")
    monkeypatch.setenv("PROMETHEUS_PROJECTS_ROOT", str(_TEST_ROOT))
    if os.path.exists("/tmp/test-conn.db"):
        os.remove("/tmp/test-conn.db")
    for mod in ("prometheus_db", "connections_registry"):
        importlib.reload(importlib.import_module(mod))
    importlib.import_module("prometheus_db").init_schema()
    yield


def _reg():
    return importlib.import_module("connections_registry")


def _db():
    return importlib.import_module("prometheus_db")


def _set_created_ago(cid, days):
    from datetime import datetime, timedelta
    ts = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d %H:%M:%S.%f")
    con = _db().get_conn()
    try:
        con.execute("UPDATE prometheus_connections SET created_at = ? WHERE id = ?", (ts, cid))
        con.commit()
    finally:
        con.close()


def test_c1_scan_env_readonly_names_only():
    r = _reg().scan_project("evscar")
    assert r["scanned"] is True and r["created"] == 3  # DEEPSEEK + OCM + DB_PASSWORD; NAO_E_CHAVE não casa
    conns = _reg().list_connections("evscar")
    names = {c["env_var"] for c in conns}
    assert names == {"DEEPSEEK_API_KEY", "OCM_API_KEY", "DB_PASSWORD"}
    for c in conns:
        assert "sk-compartilhada" not in str(c), "valor vazou!"
        assert c["masked"].endswith("••••")


def test_c2_shared_fingerprint_across_projects():
    _reg().scan_project("evscar")
    _reg().scan_project("provador")
    conns = _reg().list_connections()
    fp_deepseek = {c["fingerprint"] for c in conns if c["env_var"] == "DEEPSEEK_API_KEY"}
    assert len(fp_deepseek) == 1, "mesma chave deveria ter mesmo fingerprint"
    alerts = _reg().alerts_for("evscar")
    assert any("compartilhada" in a["text"] for a in alerts), "deveria detectar chave compartilhada"


def test_c3_unused_and_expiring_alerts():
    r = _reg().add_connection("evscar", name="Firecrawl", provider="Firecrawl",
                              billing_type="subscription", cost_usd_month=9)
    _set_created_ago(r["id"], 40)  # paga e sem uso há 40 dias
    alerts = _reg().alerts_for("evscar")
    assert any("sem uso" in a["text"] for a in alerts), "deveria flagrar pago e sem uso"

    _reg().add_connection("evscar", name="OpenChargeMap", provider="OCM",
                          billing_type="paygo", expires_at="2026-08-12")
    alerts = _reg().alerts_for("evscar")
    assert any("expira" in a["text"] for a in alerts), "deveria flagrar expirando"


def test_c4_summary_and_update():
    _reg().scan_project("evscar")
    _reg().scan_project("provador")
    _reg().add_connection("evscar", name="AssinaturaX", provider="X",
                          billing_type="subscription", cost_usd_month=15)
    s = _reg().summary()
    assert s["total_cost_usd_month"] >= 15
    assert s["projects"].get("evscar")

    conns = _reg().list_connections("evscar")
    target = next(c for c in conns if c["name"] == "AssinaturaX")
    ok = _reg().update_connection(target["id"], {"cost_usd_month": 20, "billing_type": "paygo"})
    assert ok
    after = _reg().list_connections("evscar")
    upd = next(c for c in after if c["id"] == target["id"])
    assert upd["cost_usd_month"] == 20.0 and upd["billing_type"] == "paygo"


def test_c5_exclude_production_web():
    prod = _TEST_ROOT / "web"
    prod.mkdir(exist_ok=True)
    (prod / ".env").write_text("SUPER_SECRET_API_KEY=producao-nao-varrer\n")
    r = _reg().scan_project("web")
    assert r["scanned"] is False, "~/Projetos/web deve ser excluído da varredura"
