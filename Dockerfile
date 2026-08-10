# Prometheus Memory — imagem Docker all-in-one (P6)
# python:3.14-slim + tesseract (OCR) + deps + supervisord (web/MCP/api/coletor/cron)
FROM python:3.14-slim

ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    DEBIAN_FRONTEND=noninteractive

# sistema: tesseract (OCR), sqlite3-vec deps, supervisor, git (pip install de pino git+)
RUN apt-get update && apt-get install -y --no-install-recommends \
    tesseract-ocr \
    tesseract-ocr-por \
    sqlite3 \
    libsqlite3-dev \
    supervisor \
    cron \
    git \
    procps \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# deps primeiro (cache de camada)
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# código (a cópia viva de produção é a fonte; o repo público é a base)
COPY web/*.py ./
COPY web/templates ./templates
COPY web/static ./static
COPY web/scripts ./scripts

# Cache de embeddings: path persistente no volume prometheus-data (external) — os
# modelos são baixados sob demanda no runtime (entrypoint/healthcheck) com essas envs;
# pre-download na build seria descartado pelo volume external montado por cima.
ENV FASTEMBED_CACHE_PATH=/data/mnemosyne/fastembed-cache

# UID do usuário do host (herbert=1000) — sem corrupção de permissão nos binds
RUN useradd -m -u 1000 -s /bin/bash herbert \
    && mkdir -p /data/mnemosyne /data/notes /data/projetos /telemetry/config /telemetry/share \
    && chown -R herbert:herbert /app /data /telemetry

COPY supervisord.conf /etc/supervisor/conf.d/prometheus.conf
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

EXPOSE 8777 8765 8766

# envs padrão (override no compose)
ENV HERMES_HOME=/data \
    MNEMOSYNE_HOME=/data/mnemosyne \
    PROMETHEUS_NOTES_DIR=/data/notes \
    PROMETHEUS_PROJECTS_ROOT=/data/projetos \
    OPENCODE_CONFIG_DIR=/telemetry/config \
    OPENCODE_DATA_DIR=/telemetry/share

VOLUME ["/data/mnemosyne"]

ENTRYPOINT ["/entrypoint.sh"]
# Container roda como ROOT (entrypoint configura crontab; supervisord dropa p/ herbert por programa:
# web/mcp/api/telemetry user=herbert · cron user=root — ver supervisord.conf)
