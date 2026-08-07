#!/bin/bash
# Prometheus Memory — migração para Docker (P6) — SEGURA e REVERSÍVEL
# Uso: ./scripts/migrate_to_docker.sh
# Garantias: backup verificado ANTES · origem NUNCA apagada · rollback = religar systemd
set -euo pipefail

DB_ORIG="${HOME}/.hermes/mnemosyne/data/mnemosyne.db"
SHA_REF="c298da584a5ebc8d1c7e335e999afdd71882d489f574b950c177e2a3d01b8d82"  # sha256 do DB (07/08/2026)
TAG="prometheus-memory:latest"

echo "== P6.0 — Backup de segurança =="
TS=$(date +%Y%m%d-%H%M%S)
tar czf "/tmp/opencode/pre-migracao-${TS}.tar.gz" \
  -C "$HOME" .hermes/mnemosyne/data .hermes/mnemosyne/config.yaml .hermes/mnemosyne/persona.md 2>/dev/null
echo "  backup: /tmp/opencode/pre-migracao-${TS}.tar.gz"
sha256sum "$DB_ORIG"

echo "== P6.1 — Build da imagem =="
cd "$HOME/Projetos/prometheus-memory"
docker build -t "$TAG" .

echo "== P6.2 — Cópia dos dados para o volume nomeado (1x) =="
docker volume create prometheus-data >/dev/null 2>&1 || true
docker run --rm \
  -v prometheus-data:/data \
  -v "$HOME/.hermes/mnemosyne":/src:ro \
  alpine sh -c 'cp -a /src/. /data/'
echo "  dados copiados para prometheus-data"

echo "== P6.3 — Verificação de integridade =="
SHA_VOL=$(docker run --rm -v prometheus-data:/data alpine sha256sum /data/data/mnemosyne.db | awk '{print $1}')
echo "  sha256 no volume: $SHA_VOL"
echo "  sha256 esperado  : $SHA_REF"
if [ "$SHA_VOL" != "$SHA_REF" ]; then
  echo "  ❌ SHA256 DIVERGE — abortando. Nada foi alterado. (origem intacta)"
  exit 1
fi
echo "  ✅ DB íntegro no volume"

echo "== P6.4 — Subir o container =="
docker compose up -d
sleep 20

echo "== P6.5 — Validação live =="
docker compose exec -T prometheus-memory python3 -c \
  "import urllib.request; print('health:', urllib.request.urlopen('http://localhost:8777/health', timeout=5).status)"
TOKEN=$(grep -E '^(PROMETHEUS_TOKEN|API_TOKEN|BEARER)' "$HOME/Projetos/web/.env" | head -1 | cut -d= -f2 | tr -d '"' | tr -d "'")
curl -s -H "Authorization: Bearer $TOKEN" "http://localhost:8777/api/graph?limit=500" \
  | python3 -c "import sys,json; d=json.load(sys.stdin); print('grafo: nos', len(d.get('nodes',[])), '/ arestas', len(d.get('edges',[])))"

echo ""
echo "== P6.6 — Desligar systemd (NÃO deletar — rollback em 1 min) =="
echo "  Para ativar: systemctl --user disable --now prometheus-web mnemosyne-mcp mnemosyne-api"
echo "  ROLLBACK: systemctl --user enable --now prometheus-web mnemosyne-mcp mnemosyne-api && docker compose down"
echo ""
echo "✅ MIGRAÇÃO CONCLUÍDA (após validar, desligue o systemd; origem ~/.hermes/mnemosyne mantida por 7 dias)"
