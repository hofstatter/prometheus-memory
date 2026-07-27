"""Testes multi-agent scoping (isolamento por channel_id)."""
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "web"))

os.environ["PROMETHEUS_DB"] = "/tmp/test-multiagent.db"
if os.path.exists("/tmp/test-multiagent.db"):
    os.remove("/tmp/test-multiagent.db")


def test_remember_recall_isolated():
    import importlib
    import memory
    importlib.reload(memory)
    memory.remember("segredo do atlas", agent_id="atlas", importance=0.9)
    memory.remember("segredo da nova", agent_id="nova", importance=0.9)
    r_atlas = [x["content"] for x in memory.recall("segredo", agent_id="atlas", top_k=10)]
    r_nova = [x["content"] for x in memory.recall("segredo", agent_id="nova", top_k=10)]
    assert "segredo do atlas" in r_atlas
    assert "segredo da nova" not in r_atlas, "vazamento: atlas viu memória da nova"
    assert "segredo da nova" in r_nova
    assert "segredo do atlas" not in r_nova, "vazamento: nova viu memória do atlas"


def test_recall_cross_agent_no_leak():
    import memory
    # atlas buscando termo que só existe na memória da nova → vazio
    r = [x["content"] for x in memory.recall("segredo da nova", agent_id="atlas", top_k=10)]
    assert "segredo da nova" not in r


def test_list_agents():
    import memory
    agents = memory.list_agents()
    assert "atlas" in agents and "nova" in agents


def test_default_shared():
    import memory
    memory.remember("memória compartilhada global", agent_id="", importance=0.9)
    r = [x["content"] for x in memory.recall("compartilhada global", top_k=10)]
    assert "memória compartilhada global" in r
