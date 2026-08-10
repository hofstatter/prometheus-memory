#!/bin/bash
# Entrypoint do container Prometheus (P6)
# sobe supervisord (web/MCP/api/coletor/cron) — crond via supervisord user=root
set -e

# garante permissões do volume nomeado (1ª execução após copiar dados)
chown -R herbert:herbert /data/mnemosyne 2>/dev/null || true

# Docker socket (:ro montado) — o gid do grupo docker do HOST é 116 (stat do socket);
# garante o grupo no container e adiciona o herbert para o painel ler `docker ps` (D10).
DOCKER_SOCK_GID=$(stat -c %g /var/run/docker.sock 2>/dev/null || echo "")
if [ -n "$DOCKER_SOCK_GID" ] && [ "$DOCKER_SOCK_GID" != "0" ]; then
  groupadd -g "$DOCKER_SOCK_GID" docker-host 2>/dev/null || true
  usermod -aG docker-host herbert 2>/dev/null || true
fi

# cron L2/L3 (cenas 6h, persona semanal) — crontab do ROOT (crond roda via supervisord)
printenv | grep -E '^(DEEPSEEK|PROMETHEUS|MNEMOSYNE|HERMES)' > /tmp/container.env 2>/dev/null || true
chmod 600 /tmp/container.env
{
  echo "0 */6 * * * . /tmp/container.env; python3 /app/scripts/memory_aggregator.py >> /var/log/cron-l2.log 2>&1"
  echo "0 8 * * 1 . /tmp/container.env; python3 /app/scripts/persona_synthesizer.py >> /var/log/cron-l3.log 2>&1"
} | crontab -u root - 2>/dev/null || true

# delega ao supervisord (web, mcp, api, coletor, cron)
exec supervisord -c /etc/supervisor/conf.d/prometheus.conf
