#!/bin/bash
# Start do Atlas (VM 101) — Caminho A: delega ao Mnemosyne (:8766)
# Lê DEEPSEEK_API_KEY + MNEMOSYNE_MCP_TOKEN de /opt/prometheus/.env (nunca imprime o valor)
cd ~/atlas-scripts
DSKEY=$(grep -E "^DEEPSEEK_API_KEY=" /opt/prometheus/.env | cut -d= -f2)
MTOK=$(grep -E "^MNEMOSYNE_MCP_TOKEN=" /opt/prometheus/.env | cut -d= -f2)
nohup env MNEMOSYNE_DB=/var/lib/docker/volumes/prometheus-data/_data/data/mnemosyne.db ATLAS_DIARIO_DB=/data/atlas/atlas_diario.db DEEPSEEK_API_KEY="$DSKEY" MNEMOSYNE_MCP_TOKEN="$MTOK" ~/atlas-venv/bin/python3 atlas_memory_agent.py > atlas.log 2>&1 &
echo $! > atlas.pid
sleep 1
echo "PID: $(cat atlas.pid)"
