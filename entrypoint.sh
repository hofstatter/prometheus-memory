#!/bin/bash
# Entrypoint do container Prometheus (P6)
# sobe supervisord (web/MCP/api) + cron L2/L3 + loop do coletor
set -e

# garante permissões do volume nomeado (1ª execução após copiar dados)
chown -R herbert:herbert /data/mnemosyne 2>/dev/null || true

# cron L2/L3 (cenas 6h, persona semanal) — aponta para o .env do container
printenv | grep -E '^(DEEPSEEK|PROMETHEUS|MNEMOSYNE|HERMES)' > /tmp/container.env 2>/dev/null || true
chmod 600 /tmp/container.env
{
  echo "0 */6 * * * . /tmp/container.env; python3 /app/scripts/memory_aggregator.py >> /var/log/cron-l2.log 2>&1"
  echo "0 8 * * 1 . /tmp/container.env; python3 /app/scripts/persona_synthesizer.py >> /var/log/cron-l3.log 2>&1"
} | crontab -

# inicia o cron em background (precisa ser root para crond; roda via supervisor user=root)
/usr/sbin/cron 2>/dev/null || true

# delega ao supervisord (web, mcp, api, coletor)
exec supervisord -c /etc/supervisor/conf.d/prometheus.conf
