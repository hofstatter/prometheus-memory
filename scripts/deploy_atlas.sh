#!/bin/bash
# Deploy do Atlas (F0 docs + F2 Atlas) na VM 101 (<IP_VM>)
# Uso: bash deploy_atlas.sh  (roda APÓS o teste de RAM terminar)
set -e
VM="herbert@<IP_VM>"
REPO=~/Projetos/prometheus-memory

echo "=== 1. Copia scripts para a VM ==="
scp -q $REPO/web/scripts/docs_mcp_server.py $VM:/tmp/
scp -q $REPO/web/scripts/atlas_memory_agent.py $VM:/tmp/
scp -q $REPO/web/scripts/start_atlas.sh $VM:/tmp/

echo "=== 2. Instala na VM (supervisord) ==="
ssh -o ConnectTimeout=12 $VM 'sudo bash -s' <<'SCRIPT'
set -e
echo "--- move scripts ---"
sudo cp /tmp/docs_mcp_server.py /opt/prometheus/web/scripts/ 2>/dev/null || sudo cp /tmp/docs_mcp_server.py /opt/prometheus/scripts/ 2>/dev/null || sudo mkdir -p /opt/prometheus/scripts && sudo cp /tmp/docs_mcp_server.py /opt/prometheus/scripts/
sudo cp /tmp/atlas_memory_agent.py /opt/prometheus/scripts/
sudo cp /tmp/start_atlas.sh ~/atlas-scripts/start_atlas.sh
# cria /data/docs (docs centralizados)
sudo mkdir -p /data/docs
sudo chown herbert:herbert /data/docs
echo "--- git init em /data/docs ---"
cd /data/docs && [ -d .git ] || { sudo -u herbert git init && sudo -u herbert git config user.email "atlas@prometheus.local" && sudo -u herbert git config user.name "Atlas"; }
echo "SCRIPTS OK"
SCRIPT
echo "=== Deploy preparado ==="
