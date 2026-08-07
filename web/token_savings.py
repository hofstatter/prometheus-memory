#!/usr/bin/env python3
"""
Prometheus Token Savings — estima tokens economizados pelo sistema.

Fontes de economia:
1. Offloading (refs/*.md): bytes offloaded / 4 = tokens que nao entraram no contexto
2. Compressao L0->L3: fatos L1 comprimidos em cenas L2 e persona L3 —
   a economia por recall = (media_fato - media_cena) * recalls servidos (proxy)
"""
import os
from pathlib import Path

MNEMOSYNE_HOME = Path(os.environ.get("MNEMOSYNE_HOME", Path.home() / ".hermes" / "mnemosyne"))
REFS_DIR = MNEMOSYNE_HOME / "refs"
CHARS_PER_TOKEN = 4


def offloaded_bytes() -> int:
    if not REFS_DIR.exists():
        return 0
    return sum(f.stat().st_size for f in REFS_DIR.rglob("*.md") if f.is_file())


def compute_savings(recalls_served: int = 0) -> dict:
    ob = offloaded_bytes()
    offload_tokens = ob // CHARS_PER_TOKEN
    # compressao: fato cru ~120 tok -> cena ~80 tok (economia ~40 tok/fato consolidado)
    compression_tokens = recalls_served * 40
    total = offload_tokens + compression_tokens
    return {
        "offloaded_bytes": ob,
        "offload_tokens_saved": offload_tokens,
        "recalls_served": recalls_served,
        "compression_tokens_saved": compression_tokens,
        "total_tokens_saved": total,
        "note": "Estimativa: bytes_offloaded/4 + 40 tok por recall consolidado (L1->L2/L3)",
    }


if __name__ == "__main__":
    import json
    print(json.dumps(compute_savings(), indent=2))
