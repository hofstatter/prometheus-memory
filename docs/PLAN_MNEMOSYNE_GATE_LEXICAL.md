# PLAN — Upgrade mnemosyne no container + tunar gate lexical (`MNEMOSYNE_LEXICAL_GATE_MIN`)

> Autor: 🧱 Pedreiro · Data: 08/08/2026 · Projeto-alvo: `prometheus-memory`
> Contexto: **PR #639 MERGED** (08/08 12:28Z, commit `c4344f2d`) — o knob
> `MNEMOSYNE_LEXICAL_GATE_MIN` agora existe no `main` upstream, com autoria
> hofstatter. Este plano leva o knob para produção (container P6) e mede o
> impacto no recall com a régua PT existente.

---

## 1. Situação atual (fatos verificados em 08/08/2026)

| Item | Estado |
|---|---|
| Container `prometheus-memory` | **Up 27h healthy** · `127.0.0.1:8765-8766`, `:8777` · imagem `prometheus-memory:latest` |
| Pacote no container | `mnemosyne-memory[mcp]==3.15.1` (pino em `requirements.txt`) — **SEM knob** |
| Pacote no HOST (régua) | `mnemosyne-memory 3.15.1` — **SEM knob** |
| Upstream PyPI | Último release **v3.15.1** (30/07) — knob **ainda não publicado** |
| Upstream `main` | 69 commits desde v3.15.1 · knob em `mnemosyne/core/beam.py` `_minimum_recall_relevance` (linha ~1888) |
| Régua PT | `scripts/eval_pt_recall.py` (hit@5, DB isolado, 26 casos, report `evals/reports/p5-multilingue-pt.md`) · já tem bypass local `P5_BYPASS_LEXICAL=1` (monkeypatch) |
| Env do container | `env_file: ~/Projetos/web/.env` + bloco `environment` no compose; supervisord herda env do entrypoint |

### O knob (código real no main)

```python
env = os.environ.get("MNEMOSYNE_LEXICAL_GATE_MIN")
if env is not None:
    try:
        value = float(env)
    except ValueError:
        pass
    else:
        if math.isfinite(value):
            return min(max(value, 0.0), 1.0)
if len(query_tokens) >= 4:
    return 0.3
if len(query_tokens) == 3:
    return 0.5
return 0.15
```

- **Default** (unset): comportamento histórico por tamanho de query (`0.3 / 0.5 / 0.15`).
- **`0.0`**: admite candidatos puramente-vetoriais (recall-first) — é o que queremos.
- Clamp `[0.0, 1.0]` · não-finito/inválido → cai no default · **lido a cada chamada** (mas no container o env vem do compose → aplica via restart do container).

---

## 2. Decisões de arquitetura (registradas em DECISIONS.md — D9–D12)

- **D9 — Instalar do `main` pinado, não esperar release.** O knob não está em
  release (último v3.15.1) e o objetivo do Herbert é tê-lo em produção. Instalar
  via `pip install git+https://github.com/mnemosyne-oss/mnemosyne@c4344f2d8a02d7fff32b420eb708407c9f183847`
  (SHA do merge do PR #639) — **determinístico, reversível**, sem usar `@main` móvel.
  Alternativa conservadora registrada: aguardar release 3.15.2/3.16.0 se o
  Herbert preferir adiar.
- **D10 — Env via bloco `environment` do compose (não no `.env` de produção).**
  O `.env` (`~/Projetos/web/.env`) é compartilhado e carrega secrets; o knob é
  config de deploy e deve ficar versionado no compose, com override por env.
- **D11 — Valor inicial `0.0` (recall-first), decidido por medição.** Subir com
  `MNEMOSYNE_LEXICAL_GATE_MIN=0.0`; se a régua PT mostrar queda de precisão
  relevante, subir em degraus (0.15 → 0.3). Medir antes/depois, nunca no escuro.
- **D12 — Trocar o bypass local `P5_BYPASS_LEXICAL` (monkeypatch) pelo knob
  oficial** na régua. O monkeypatch vira histórico (regra do veterano: sem
  compat retroativa, obsoleto deleta). Mantém-se o suporte a `MNEMOSYNE_LEXICAL_GATE_MIN`
  real no eval (env repassado), removendo o patch de runtime.

---

## 3. Fases + critérios de aceite

### FASE 0 — Baseline e snapshot (pré-mudança)

**Ações:**
1. Rodar régua PT **no host** (mnemosyne 3.15.1, sem bypass e com `P5_BYPASS_LEXICAL=1`) e registrar baseline em `evals/reports/p5-multilingue-pt.md`.
2. Tag da imagem atual: `docker tag prometheus-memory:latest prometheus-memory:pre-knob-20260808` (rollback instantâneo).
3. Snapshot do volume: confirmar backup 6h NVMe recente (`docker run --rm -v prometheus-data:/src -v ~/backups/...:/dst ...`).

**Aceite (verde):**
- [ ] Baseline PT registrado (hit@5 default E com bypass) no report.
- [ ] Imagem `pre-knob-20260808` existente (`docker images`).
- [ ] Backup do volume ≤ 6h de idade.

---

### FASE 1 — Validação isolada do knob (host, venv temporário)

**Ações:**
1. Criar venv `/tmp/opencode/knob-venv` com o pacote do `main` pinado:
   `pip install "mnemosyne-memory[mcp] @ git+https://github.com/mnemosyne-oss/mnemosyne@c4344f2d8a02d7fff32b420eb708407c9f183847"`
2. Rodar o teste do PR: `python -m pytest tests/test_lexical_gate_knob.py` (do source ou via check no CI — já está no commit do merge).
3. Rodar a régua PT com o venv novo em 3 modos:
   - `MNEMOSYNE_LEXICAL_GATE_MIN` unset (default 3.15.1-equivalente)
   - `MNEMOSYNE_LEXICAL_GATE_MIN=0.0`
   - `MNEMOSYNE_LEXICAL_GATE_MIN=0.15`
4. Conferir que o `fail-loud dim` (mudança #518/#521 no main) **não** quebra com `bge-small-en-v1.5` (modelo conhecido na tabela; sem `MNEMOSYNE_EMBEDDING_DIM` explícito).

**Aceite (verde):**
- [ ] `test_lexical_gate_knob.py` passa no venv.
- [ ] Régua PT rodou nos 3 modos; tabela comparativa gerada.
- [ ] Nenhum `ValueError` de dimensão de embedding no boot do venv.

---

### FASE 2 — Upgrade do container + knob em produção

**Ações:**
1. `requirements.txt`: trocar `mnemosyne-memory[mcp]==3.15.1` pelo pino git SHA (D9).
2. `docker-compose.yml`: adicionar `MNEMOSYNE_LEXICAL_GATE_MIN: "0.0"` no bloco `environment` (D10/D11).
3. `docker compose build prometheus-memory && docker compose up -d` (volume `prometheus-data` external — dados intactos).
4. Aguardar healthcheck (30s) e validar:
   - `curl -s localhost:8777/health` → 200
   - `docker compose ps` → healthy
   - MCP `mnemosyne mcp` sobe na :8765 (token OK)
5. Validar `mnemosyne version` dentro do container → aponta para o SHA do knob (commit `77dd27424d` adicionou `--version`).

**Aceite (verde):**
- [ ] Container healthy com a imagem nova.
- [ ] `/health` 200 · MCP :8765 responde com token.
- [ ] `MNEMOSYNE_LEXICAL_GATE_MIN=0.0` visível no processo (`docker exec ... printenv`).
- [ ] Dados preservados (recall real devolve memórias antigas).

---

### FASE 3 — Tuning do gate + medição em produção

**Ações:**
1. Rodar recall real (tool Mnemosyne MCP, query sem overlap lexical p/ exercitar o vetor) com `0.0` — comparar resultado vs antes (sessão 46: recall funcionava).
2. Rodar régua PT **no host com o knob** (`MNEMOSYNE_LEXICAL_GATE_MIN=0.0` no venv) e comparar com o baseline da Fase 0.
3. Se acurácia cair > 2pp OU qualidade percebida do recall piorar: testar `0.15` e `0.3`, escolher o menor que preserve ganho.
4. Ajustar o valor no compose (Fase 2 refeita) se mudar de `0.0`.

**Aceite (verde):**
- [ ] Tabela comparativa baseline vs knob em `evals/reports/` (mesmos casos).
- [ ] Valor final decidido e documentado (D11) — `0.0` ou degrau superior.
- [ ] Recall real em produção demonstrado (1 query sem overlap → gold no top-5).

---

### FASE 4 — Docs, estado e commit

**Ações:**
1. `DECISIONS.md` (prometheus-memory): fechar D9–D12 com resultado da medição.
2. `STATE.md` (Bytex_AgentOS): nova seção no topo — PR #639 MERGED + upgrade + tuning com números.
3. `CONTEXT.md` (Bytex_AgentOS): bloco (1.5) — knob ativo, versão do pacote, valor do gate.
4. Backup do volume pós-upgrade (nvme) + verificar Sentinela ok.
5. Commit LOCAL no `prometheus-memory` (docs + requirements + compose + eval). **Push exige GIT GATE** (revisão Inspetor + confirmação SIM/NÃO do Herbert).

**Aceite (verde):**
- [ ] STATE.md/CONTEXT.md/DECISIONS.md atualizados e sincronizados.
- [ ] Commit local com mensagem descritiva (autor `hofstatter`, e-mail canônico).
- [ ] Backup pós-upgrade ok.

---

## 4. Riscos e mitigação

| Risco | Prob. | Mitigação |
|---|---|---|
| 69 commits do main trazem regressão (não só o knob) | Média | Pino no SHA do merge #639 (menor delta que contém o knob); Fase 1 valida isolado antes de tocar produção; imagem `pre-knob` para rollback |
| `fail-loud dim` (#518/#521) quebra boot do container | Baixa | Modelo `bge-small-en-v1.5` está na tabela interna do upstream; Fase 1 confirma |
| Gate `0.0` degrada precisão (ruído entra) | Média | Régua PT mede hit@5; degraus 0.15/0.3 como fallback (D11) |
| Rebuild Docker demora / falha de rede no `pip install git` | Baixa | Pino por SHA; `--no-cache-dir`; se falhar, imagem antiga intacta até `up -d` |
| Rollback | — | `docker tag pre-knob-20260808` + `docker compose up -d` reverte env e pacote (requirements em git) |

## 5. Fora de escopo (desta fase)

- Fix FK `memory_embeddings` upstream (bug cosmético — já documentado).
- M4 (Postgres via compose) · OSM EVSCAR · remoção do systemd (11/08).
- Tuning de `MNEMOSYNE_VEC_TYPE` / modelo de embedding (já decidido: manter bge-small).

## 6. Backups

- `~/backups/herbert/gate-lexical-knob/20260808-204459/` — requirements.txt + docker-compose.yml (manifest json).
- Imagem `prometheus-memory:pre-knob-20260808` (tag rollback).
- Volume `prometheus-data` — backup NVMe 6h (Fase 0) + pós-upgrade (Fase 4).
