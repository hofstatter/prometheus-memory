# Prometheus Memory — imagem Docker all-in-one (P6)
# python:3.14-slim + tesseract (OCR) + deps + supervisord (web/MCP/api/coletor/cron)
FROM python:3.14-slim

ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    DEBIAN_FRONTEND=noninteractive

# sistema: tesseract (OCR), sqlite3-vec deps, supervisor
RUN apt-get update && apt-get install -y --no-install-recommends \
    tesseract-ocr \
    tesseract-ocr-por \
    sqlite3 \
    libsqlite3-dev \
    supervisor \
    cron \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# deps primeiro (cache de camada)
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# código (a cópia viva de produção é a fonte; o repo público é a base)
COPY app.py auth_guard.py connections_registry.py dedup.py editor_routes.py \
     entity_store.py extractor.py graph_service.py memory.py notes_routes.py \
     pm_routes.py projects_registry.py prometheus_db.py rag_engine.py rag_routes.py \
     session_registry.py skills_builder.py skills_registry.py storage.py tech_profile.py \
     telemetry_collector.py token_savings.py ./
COPY templates ./templates
COPY static ./static
COPY scripts ./scripts

# UID do usuário do host (herbert=1000) — sem corrupção de permissão nos binds
RUN useradd -m -u 1000 -s /bin/bash herbert \
    && mkdir -p /data/mnemosyne /data/notes /data/projetos /telemetry/config /telemetry/share \
    && chown -R herbert:herbert /app /data /telemetry

COPY supervisord.conf /etc/supervisor/conf.d/prometheus.conf
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

USER herbert

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
