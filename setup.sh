#!/usr/bin/env bash
# Prometheus Memory — Instalação automatizada (wrapper multiplataforma)
# Linux/macOS/WSL: bash setup.sh | Windows nativo: python setup.py
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
if [ "${1:-}" = "--legacy" ]; then
  exec bash "$SCRIPT_DIR/setup_legacy.sh"
fi
exec python3 "$SCRIPT_DIR/setup.py" "$@"
