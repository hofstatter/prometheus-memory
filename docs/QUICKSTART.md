# QUICKSTART — Prometheus Memory

## 1. Instalar

```bash
git clone https://github.com/hofstatter/prometheus-memory.git
cd prometheus-memory
bash setup.sh
```

## 2. Configurar

```bash
nano ~/prometheus-memory/.env
```

Mínimo necessário:

```ini
DEEPSEEK_API_KEY=sk-sua-chave-aqui
PROMETHEUS_USER=seu-nome
PROMETHEUS_PROJECT=meu-projeto
```

Reinicie a Web UI:

```bash
systemctl --user restart prometheus-web
```

## 3. Usar

### Web UI

Abra http://localhost:8777 — 7 abas:

| Aba | O que faz |
|---|---|
| 📋 Timeline | Memórias agrupadas por data, filtro por projeto |
| 🕸️ Grafo | Grafo interativo (nós = memórias, diamantes = projetos) |
| 📐 Canvas | Diagrama Mermaid do fluxo do agente (clique nos nós) |
| 📄 RAG | Upload de documentos + busca semântica |
| 📝 Notes | Importar URLs, buscar e visualizar notas |
| 🧩 Skills | Registro de skills (global) + conteúdo |
| 🗂️ Projetos | Painel por projeto: kanban, timeline, progresso, presença de agentes, Stack & Runtime, Conexões & Custos, Skills do projeto |
| ✏️ Editor | Clique em uma memória → Editar (modal) |

### Pipeline (automático via cron)

- **A cada 6h:** fatos L1 → cenas L2 + atualização do Canvas
- **Segunda 08:00:** cenas → persona L3 + detecção de skills

### Execução manual

```bash
# Consolidar agora
python3 ~/bin/memory_aggregator.py

# Sintetizar persona agora
python3 ~/bin/persona_synthesizer.py

# Offloading manual
python3 ~/bin/ref_manager.py save web_search meu-projeto "$(cat log_grande.txt)"
python3 ~/bin/ref_manager.py load <node_id>
```

## 4. Verificar

```bash
systemctl --user status prometheus-web
curl -s http://localhost:8777/health
mnemosyne stats
```

## Troubleshooting

| Problema | Solução |
|---|---|
| UI mostra 0 memórias | Verifique se `mnemosyne` está no PATH do serviço (`Environment="PATH=..."` no unit) |
| Cenas não são criadas | `DEEPSEEK_API_KEY` ausente — o pipeline roda degradado (sem LLM) |
| OCR falha | `sudo apt install tesseract-ocr tesseract-ocr-por` |
| RAG lento no 1º uso | fastembed baixa o modelo (~100MB) na primeira execução |
