#!/usr/bin/env python3
"""Merge one-shot de entidades (NER v1.2) — dry-run/apply + prune de genéricos.

Uso:
  python3 scripts/merge_entities.py --dry-run            # relatório, não escreve
  python3 scripts/merge_entities.py --apply              # aplica (backup do DB antes!)
  python3 scripts/merge_entities.py --prune MODEL --apply  # remove genérico sem canônico

Regras (D2/D4/D5):
  - agrupa por type; dentro do type: normaliza → match exato → containment
  - canônico = maior mention_count (empate → nome mais longo)
  - merge soma menções + re-linka memórias (INSERT OR IGNORE) + marca canonical_id
  - --prune NAME: remove entidade e seus links (só quando não há canônico legítimo)
"""
import argparse
import shutil
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "web"))

from prometheus_db import DB_PATH, get_conn, init_schema  # noqa: E402
from entity_store import merge_into, normalize_name  # noqa: E402


def _candidates(con):
    """Agrupa entidades por (type) e detecta pares alias→canônico."""
    rows = con.execute(
        "SELECT id, name, type, mention_count FROM prometheus_entities "
        "WHERE canonical_id IS NULL OR canonical_id = '' ORDER BY type, mention_count DESC"
    ).fetchall()
    groups: dict = {}
    for r in rows:
        groups.setdefault(r["type"], []).append(dict(r))
    merges = []
    for typ, ents in groups.items():
        ents.sort(key=lambda e: (-e["mention_count"], -len(e["name"])))
        for i, alias in enumerate(ents):
            an = normalize_name(alias["name"])
            if not an:
                continue
            for canon in ents[:i]:
                cn = normalize_name(canon["name"])
                if canon["id"] == alias["id"]:
                    continue
                if an == cn or (min(len(an), len(cn)) >= 3 and (an in cn or cn in an)):
                    merges.append({"alias": alias, "canonical": canon, "type": typ})
                    break
    return merges


def _prune_list(con, names):
    return con.execute(
        f"SELECT id, name, type FROM prometheus_entities WHERE name IN ({','.join('?' * len(names))})",
        names,
    ).fetchall()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--prune", nargs="+", default=[], help="nomes de genéricos a remover")
    args = ap.parse_args()

    if not (args.dry_run or args.apply):
        ap.error("informe --dry-run ou --apply")
    if args.apply and not args.dry_run:
        confirm = input("APPLY real no banco de produção? Digite 'APPLY' para confirmar: ")
        if confirm.strip() != "APPLY":
            print("Abortado.")
            return 1

    init_schema()
    con = get_conn()

    merges = _candidates(con)
    print(f"\n== Relatório de merge ({DB_PATH}) ==\n")
    for m in merges:
        a, c = m["alias"], m["canonical"]
        print(f"  [{m['type']:<7}] '{a['name']}' ({a['mention_count']}x) → '{c['name']}' ({c['mention_count']}x)")

    pruned = []
    if args.prune:
        rows = _prune_list(con, args.prune)
        for r in rows:
            pruned.append(dict(r))
            print(f"  [prune      ] '{r['name']}' ({r['type']})")

    if args.dry_run:
        print(f"\nResumo: {len(merges)} merge(s), {len(pruned)} prune(s). Nada foi escrito.")
        con.close()
        return 0

    # APPLY
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    backup = Path.home() / "backups" / "prometheus-memory" / "merge-entities" / stamp / "mnemosyne.db"
    backup.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(DB_PATH, backup)
    print(f"\nBackup do DB: {backup}")

    n = 0
    for m in merges:
        res = merge_into(con, m["alias"]["id"], m["canonical"]["id"])
        if res.get("ok"):
            n += 1
    for r in pruned:
        con.execute("DELETE FROM prometheus_memory_entities WHERE entity_id = ?", (r["id"],))
        con.execute("DELETE FROM prometheus_entities WHERE id = ?", (r["id"],))
    con.commit()
    con.close()
    print(f"Aplicado: {n} merge(s), {len(pruned)} prune(s). Backup em {backup}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
