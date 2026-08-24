#!/bin/bash
# Deploy do Atlas (F0 docs + F2 Atlas + Neurônio loop) na VM 101 (<IP_VM>)
# Uso: bash deploy_atlas.sh
set -e
VM="herbert@<IP_VM>"
REPO=~/Projetos/prometheus-memory

echo "=== 1. Copia scripts para a VM ==="
scp -q $REPO/web/scripts/docs_mcp_server.py $VM:/tmp/
scp -q $REPO/web/scripts/atlas_memory_agent.py $VM:/tmp/
scp -q $REPO/web/scripts/start_atlas.sh $VM:/tmp/
scp -q $REPO/web/scripts/atlas_loop.py $VM:/tmp/
scp -q $REPO/web/scripts/atlas-loop.service $VM:/tmp/

echo "=== 2. Instala na VM ==="
ssh -o ConnectTimeout=12 $VM 'sudo bash -s' <<'SCRIPT'
set -e
echo "--- move scripts (MCP + docs) ---"
sudo cp /tmp/docs_mcp_server.py /opt/prometheus/web/scripts/ 2>/dev/null || sudo cp /tmp/docs_mcp_server.py /opt/prometheus/scripts/ 2>/dev/null || sudo mkdir -p /opt/prometheus/scripts && sudo cp /tmp/docs_mcp_server.py /opt/prometheus/scripts/
sudo cp /tmp/atlas_memory_agent.py /opt/prometheus/scripts/
# runtime do Atlas (MCP + loop) — IMPORTANTE: o WAL e o loop importam daqui
sudo cp /tmp/atlas_memory_agent.py ~/atlas-scripts/atlas_memory_agent.py
sudo cp /tmp/start_atlas.sh ~/atlas-scripts/start_atlas.sh
sudo cp /tmp/atlas_loop.py ~/atlas-scripts/atlas_loop.py
sudo chown -R herbert:herbert ~/atlas-scripts
# cria /data/docs (docs centralizados)
sudo mkdir -p /data/docs
sudo chown herbert:herbert /data/docs
echo "--- git init em /data/docs ---"
cd /data/docs && [ -d .git ] || { sudo -u herbert git init && sudo -u herbert git config user.email "atlas@prometheus.local" && sudo -u herbert git config user.name "Atlas"; }
# unit do loop (neurônio)
sudo cp /tmp/atlas-loop.service /etc/systemd/system/atlas-loop.service
sudo systemctl daemon-reload
sudo systemctl enable atlas-loop.service
echo "SCRIPTS OK"
SCRIPT
echo "=== 3. Reinicia MCP (root, uniforme) + sobe loop ==="
ssh -o ConnectTimeout=12 $VM 'bash -s' <<'SCRIPT'
set -e
# restart do MCP como ROOT (uniforme com o loop; WAL no runtime)
sudo pkill -f atlas_memory_agent.py 2>/dev/null || true
sleep 1
cd ~/atlas-scripts && sudo bash start_atlas.sh
# sobe o loop (neurônio)
sudo systemctl restart atlas-loop.service
sleep 3
echo "--- status ---"
systemctl is-active atlas-loop.service
curl -s -m 5 http://127.0.0.1:8768/sse -o /dev/null -w "MCP atlas: HTTP %{http_code}\n" || true
SCRIPT
echo "=== Deploy concluído ==="
