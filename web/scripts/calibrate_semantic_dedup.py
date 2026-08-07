#!/usr/bin/env python3
"""Calibração do dedup semântico (PLAN_QUALIDADE_RECALL, Fase 2) — rodar UMA vez.

Amostra memórias das lanes ativas, faz recall de cada uma contra a própria lane
e imprime a distribuição de scores do vizinho mais próximo NÃO-idêntico, junto
com a fração que o guard _is_near_dup flagraria em cada threshold candidato.

Uso:  python scripts/calibrate_semantic_dedup.py [--limit 50] [--channel proj:%]
"""
import argparse
import re
import sqlite3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "web"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from prometheus_db import DB_PATH  # noqa: E402


def _channels() -> list:
    con = sqlite3.connect(str(DB_PATH))
    rows = con.execute(
        "SELECT DISTINCT channel_id FROM working_memory "
        "WHERE channel_id LIKE 'proj:%' OR channel_id LIKE 'agent-%' OR channel_id = 'default' "
        "ORDER BY channel_id"
    ).fetchall()
    con.close()
    return [r[0] for r in rows]


def _sample(channel: str, limit: int) -> list:
    con = sqlite3.connect(str(DB_PATH))
    rows = con.execute(
        "SELECT id, content FROM working_memory WHERE channel_id = ? "
        "AND length(content) > 20 ORDER BY RANDOM() LIMIT ?",
        (channel, limit),
    ).fetchall()
    con.close()
    return [{"id": r[0], "content": r[1]} for r in rows]


def _overlap(a: str, b: str) -> float:
    ta = set(re.findall(r"\w+", (a or "").lower()))
    tb = set(re.findall(r"\w+", (b or "").lower()))
    if not ta or not tb:
        return 0.0
    return len(ta & tb) / min(len(ta), len(tb))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=50)
    ap.add_argument("--channel", default=None, help="filtro de lane (ex: proj:%%)")
    args = ap.parse_args()

    from memory import recall_lane

    channels = [c for c in _channels() if (args.channel is None or
               __import__("fnmatch").fnmatch(c, args.channel))]
    if not channels:
        print("Nenhuma lane encontrada no banco:", DB_PATH)
        return 1

    nearest = []      # (score, overlap) do vizinho não-idêntico
    total = 0
    for ch in channels:
        for m in _sample(ch, args.limit):
            total += 1
            try:
                results = recall_lane(ch, m["content"], top_k=5)
            except Exception as e:
                print(f"  [skip] {ch} recall falhou: {str(e)[:80]}")
                continue
            for r in results:
                if r.get("id") == m["id"]:
                    continue  # o próprio
                try:
                    score = float(r.get("score") or 0.0)
                except (TypeError, ValueError):
                    continue
                nearest.append((score, _overlap(m["content"], r.get("content", ""))))
                break  # só o vizinho mais próximo

    if not nearest:
        print("Amostra vazia (sem vizinhos não-idênticos). Dados ainda muito poucos?")
        return 1

    scores = sorted(s for s, _ in nearest)
    n = len(scores)
    print(f"\nCalibração dedup semântico — {total} memórias, {n} pares vizinho↔memória")
    print(f"Banco: {DB_PATH}\n")
    for pct in (50, 75, 90, 95, 99, 100):
        idx = min(n - 1, int(n * pct / 100) - 1 if pct < 100 else n - 1)
        print(f"  percentil {pct:>3}  score = {scores[idx]:.4f}")

    print("\nFração de pares que o guard flagraria por threshold (score + overlap>=0.65):")
    for t in (0.75, 0.80, 0.85, 0.88, 0.90, 0.92, 0.95):
        flagged = sum(1 for s, ov in nearest if s >= t and ov >= 0.65)
        print(f"  threshold {t:.2f} → {flagged}/{n} ({100 * flagged / n:.1f}%)")

    print("\nRecomendação: escolher o menor threshold com fração próxima de 0%")
    print("(pares que o guard flagra são candidatos a falso-positivo de dedup).")
    print("Se a fração em 0.90 for alta, subir para 0.92/0.95; se baixa e houver")
    print("quase-duplicatas conhecidas passando, o extractor prompt já cobre (1ª linha).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
