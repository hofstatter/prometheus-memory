# P4 — Ruler honesto + experimentos de retrieval (subset-20, judge real)

- Data: 04/08/2026 (tarde) · 19 instâncias · judge DeepSeek `deepseek-chat` temp 0 · mesma sessão
- **mode=llm REAL** (antes os runs da tarde eram proxy de overlap — LLM_BACKEND default=ollama, desligado)

| Config | QA accuracy | Δ |
|---|---|---|
| baseline (bge-small-en-v1.5, 33M) | **42.1%** | — |
| expansão da pergunta por IA (paráfrases) | 31.6% | **-10.5pp** ❌ |
| embedding BAAI/bge-large-en-v1.5 (1024 dims) | 26.3% | **-15.8pp** ❌ |

## Descobertas

1. **Régua era mentirosa**: o relatório dizia "LLM judge" mas, com LLM_BACKEND não
   setado (default ollama, desligado), `available()` = False → rodava proxy de overlap.
   O "36.8%" da tarde era PROXY; o baseline real com judge é **42.1%** (e 47.4% na
   manhã — drift de modelo). Consertado: runner reporta `mode` REAL + backend;
   CI fixa `LLM_BACKEND=deepseek` + `DEEPSEEK_MODEL=deepseek-chat`.
2. **Paráfrases pioram**: as perguntas EN do LongMemEval já são otimamente formuladas
   frente à evidência; paráfrases afastam e o merge max-score traz ruído (-10.5pp).
3. **bge-large piora**: modelos BGE precisam de prefixo de instrução de retrieval
   ("Represent this sentence for searching relevant passages:") que o mnemosyne
   upstream não adiciona — bge-small tolera, bge-large colapsa (-15.8pp, mesmo com
   MNEMOSYNE_EMBEDDING_DIM=1024). Stella 1.5B não está no catálogo do fastembed.

## Veredito

Régua estável e honesta = o ganho REAL da sessão. As 2 melhorias de retrieval foram
**revertidas** (faziam mal). O benchmark EN não melhora com truques de wrapper —
próximo passo real: alvo PT (produção) ou trabalho upstream (prefixo/reranker/granularidade).
