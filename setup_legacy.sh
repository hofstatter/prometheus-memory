#!/usr/bin/env bash
# Prometheus Memory — Instalação automatizada
# Uso: bash setup.sh
set -euo pipefail

INSTALL_DIR="$HOME/prometheus-memory"
BIN_DIR="$HOME/bin"
SKILLS_DIR="$HOME/.opencode/skills"
SKILLS_DIR_NEW="$HOME/.config/opencode/skills"
SYSTEMD_DIR="$HOME/.config/systemd/user"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "⚡ Prometheus Memory — Setup"
echo "================================"

# 1. Python
if ! command -v python3 >/dev/null 2>&1; then
    echo "❌ Python 3.9+ não encontrado. Instale antes de continuar."
    exit 1
fi
PY_VER=$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
echo "✓ Python $PY_VER"

# 2. Mnemosyne
if ! command -v mnemosyne >/dev/null 2>&1; then
    echo "→ Instalando Mnemosyne..."
    pip install --user "mnemosyne-memory[all]>=3.12"
fi
echo "✓ Mnemosyne $(mnemosyne --version 2>/dev/null || echo 'instalado')"

# 3. Dependências Python
echo "→ Instalando dependências..."
pip install --user -r "$SCRIPT_DIR/requirements.txt"

# 4. Tesseract (OCR — opcional mas recomendado)
if ! command -v tesseract >/dev/null 2>&1; then
    echo "⚠ Tesseract não encontrado. Para OCR em PDFs/imagens:"
    echo "  sudo apt install tesseract-ocr tesseract-ocr-por"
else
    echo "✓ Tesseract $(tesseract --version 2>/dev/null | head -1 | awk '{print $2}')"
fi

# 5. Copiar para INSTALL_DIR
if [ "$SCRIPT_DIR" != "$INSTALL_DIR" ]; then
    echo "→ Copiando para $INSTALL_DIR..."
    mkdir -p "$INSTALL_DIR"
    cp -r "$SCRIPT_DIR"/* "$INSTALL_DIR/"
fi

# 6. Scripts do pipeline → ~/bin
mkdir -p "$BIN_DIR"
cp "$INSTALL_DIR/scripts/"*.py "$BIN_DIR/"
chmod +x "$BIN_DIR/"*.py
echo "✓ Scripts do pipeline em $BIN_DIR"

# 7. Skills → ~/.opencode/skills
mkdir -p "$SKILLS_DIR"
cp -r "$INSTALL_DIR/skills/auto-memory" "$SKILLS_DIR/"
mkdir -p "$SKILLS_DIR_NEW"
cp -r "$INSTALL_DIR/skills/auto-memory" "$SKILLS_DIR_NEW/"
echo "✓ Skill auto-memory instalada (novo + legado)"

# 8. .env
if [ ! -f "$INSTALL_DIR/.env" ]; then
    cp "$INSTALL_DIR/.env.example" "$INSTALL_DIR/.env"
    echo "⚠ Configure suas chaves em $INSTALL_DIR/.env (DEEPSEEK_API_KEY obrigatória)"
fi

# 9. Cron jobs
CRON_MARKER="# prometheus-memory"
if ! crontab -l 2>/dev/null | grep -q "$CRON_MARKER"; then
    (crontab -l 2>/dev/null; cat <<EOF
$CRON_MARKER
0 */6 * * * set -a; . $INSTALL_DIR/.env; set +a; python3 $BIN_DIR/memory_aggregator.py
0 8 * * 1 set -a; . $INSTALL_DIR/.env; set +a; python3 $BIN_DIR/persona_synthesizer.py
EOF
    ) | crontab -
    echo "✓ Cron jobs instalados (L2 a cada 6h, L3 semanal)"
else
    echo "✓ Cron jobs já existem"
fi

# 10. Systemd (Web UI 24/7)
if command -v systemctl >/dev/null 2>&1; then
    mkdir -p "$SYSTEMD_DIR"
    cp "$INSTALL_DIR/systemd/prometheus-web.service" "$SYSTEMD_DIR/"
    systemctl --user daemon-reload
    systemctl --user enable --now prometheus-web.service
    echo "✓ Serviço prometheus-web ativo"
fi

echo ""
echo "================================"
echo "✅ Instalação concluída!"
echo "   Web UI: http://localhost:8777"
echo "   Config: $INSTALL_DIR/.env"
echo "================================"
