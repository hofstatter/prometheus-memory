#!/usr/bin/env python3
"""CLI de chaves do Prometheus-Memory (F5) — emite/valida/revoga API keys por agente.

Uso:
  pm-key issue <agent_id> [--tenant 1] [--harness opencode] [--channel agent-<id>]
  pm-key validate <api_key>
  pm-key revoke <agent_id> [--tenant 1]
  pm-key list [--tenant 1]

Requer PROMETHEUS_PG_URL (ou usa o default). A senha vem do /opt/prometheus/.env.
"""
from __future__ import annotations

import argparse
import os
import sys


def _load_pg_url() -> str:
    url = os.environ.get("PROMETHEUS_PG_URL", "").strip()
    if url:
        return url
    # lê a senha do .env da VM (quando roda na própria VM)
    env_path = "/opt/prometheus/.env"
    if os.path.exists(env_path):
        for line in open(env_path):
            if line.startswith("PROMETHEUS_PG_PASSWORD="):
                pw = line.strip().split("=", 1)[1]
                return f"postgresql://prometheus:{pw}@127.0.0.1:5432/prometheus_memory"
    return "postgresql://prometheus@127.0.0.1:5432/prometheus_memory"


def main() -> int:
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    os.environ["PROMETHEUS_PG_URL"] = _load_pg_url()
    from auth_gateway import issue_key, list_agents, revoke_agent, validate_key

    ap = argparse.ArgumentParser(prog="pm-key", description="Gerencia API keys dos agentes")
    sub = ap.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("issue", help="emite uma API key para um agente")
    p.add_argument("agent_id")
    p.add_argument("--tenant", type=int, default=1)
    p.add_argument("--harness", default="")
    p.add_argument("--channel", default=None)

    p = sub.add_parser("validate", help="valida uma API key")
    p.add_argument("api_key")

    p = sub.add_parser("revoke", help="revoga a chave de um agente")
    p.add_argument("agent_id")
    p.add_argument("--tenant", type=int, default=1)

    p = sub.add_parser("list", help="lista agentes/chaves")
    p.add_argument("--tenant", type=int, default=None)

    args = ap.parse_args()

    if args.cmd == "issue":
        key = issue_key(args.tenant, args.agent_id, args.harness, args.channel)
        print(f"API KEY gerada (guarde — não será mostrada de novo):")
        print(f"  {key}")
        print(f"  agente={args.agent_id} tenant={args.tenant} channel={args.channel or f'agent-{args.agent_id}'}")
    elif args.cmd == "validate":
        info = validate_key(args.api_key)
        if info:
            print(f"VALIDO: tenant={info['tenant_id']} agent={info['agent_id']} channel={info['channel_id']}")
        else:
            print("INVALIDO: chave não encontrada ou revogada")
            return 1
    elif args.cmd == "revoke":
        revoke_agent(args.tenant, args.agent_id)
        print(f"REVOGADO: agente={args.agent_id} tenant={args.tenant}")
    elif args.cmd == "list":
        for a in list_agents(args.tenant):
            status = "revogado" if a["revoked_at"] else "ativo"
            print(f"  [{a['tenant_id']}] {a['agent_id']} ({a['harness'] or '?'}) channel={a['channel_id']} — {status}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
