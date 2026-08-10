# PLAN — Troca do pino git → release oficial do mnemosyne (MICRO)

> Autor: 🧱 Pedreiro · Data: 08/08/2026 · Projeto-alvo: `prometheus-memory` · **STATUS: PENDENTE (gatilho = PyPI publicar versão com o knob)**
> Origem: dívida registrada na D9 (PLAN_MNEMOSYNE_GATE_LEXICAL.md) — rodamos o `main` @ `c4344f2d`
> (69 commits além da última release v3.15.1). Quando o upstream publicar a release oficial que
> contém o PR #639 (provável **3.16.0**), trocar o pino git pelo pino de versão.

---

## 1. Gatilho (o que dispara este plano)

```bash
curl -s https://pypi.org/pypi/mnemosyne-memory/json | python3 -c "import json,sys; print(json.load(sys.stdin)['info']['version'])"
```
- **≥ 3.16.0** → executar (a release já contém o knob — confirmar `MNEMOSYNE_LEXICAL_GATE_MIN` no CHANGELOG/README da release).
- **= 3.15.1** → nada a fazer (hoje: 08/08/2026, ainda 3.15.1).

## 2. Ações (quando o gatilho disparar)

1. **Verificar que o knob está na release:** conferir `MNEMOSYNE_LEXICAL_GATE_MIN` no CHANGELOG da nova versão (upstream `CHANGELOG.md` tag).
2. **Backup** (rotina obrigatória):
   ```bash
   ~/bin/backup-before-edit.sh requirements.txt docker-compose.yml --feature=mnemosyne-release-swap --reason="troca pino git -> release oficial"
   ```
3. **requirements.txt:** trocar
   `mnemosyne-memory[mcp] @ git+https://github.com/mnemosyne-oss/mnemosyne@c4344f2d8a02d7fff32b420eb708407c9f183847`
   por `mnemosyne-memory[mcp]==<nova_versao>` (ex.: `==3.16.0`).
4. **Dockerfile:** manter `git` (inofensivo; remove em plano futuro se o pino git for aposentado de vez — NÃO nesta fase, zero abstração).
5. **Rebuild + up:** `docker compose build prometheus-memory && docker compose up -d` (volume `prometheus-data` external preservado).
6. **Validação (aceite):**
   - [ ] Container healthy · `/health` 200
   - [ ] `mnemosyne` no container reporta a versão releaseada (>=3.16.0)
   - [ ] `MNEMOSYNE_LEXICAL_GATE_MIN=0.0` continua no env (compose não muda)
   - [ ] Régua PT mantém ≥ 71.9% (rodar `scripts/eval_pt_recall.py` com o knob — host precisa do pacote releaseado ou usar venv novo)
   - [ ] Recall real OK (memória P6 `a163e3bf…` no topo)
7. **Backup NVMe do volume pós-upgrade** + sha256.
8. **Commit local + GIT GATE p/ push** (Inspetor revisa + SIM/NÃO do Herbert — 1 confirmação por push).

## 3. Rollback (se a release oficial regredir algo)

- Imagem atual `prometheus-memory:latest` → `docker tag` pré-troca (`prometheus-memory:pre-release-swap-<data>`)
- Reverter `requirements.txt` para o pino git (git revert do commit) + rebuild
- Tempo estimado: < 5 min

## 4. Fora de escopo

- Remover `git` do Dockerfile (só se pararmos de usar pino git em definitivo)
- Hygiene das 14 memórias-ruído (outro plano — ver STATE.md)
- OSM EVSCAR · M4 Postgres · remover systemd (~11/08)

## 5. Nota de monitoramento

Este plano é **disparado por evento externo** (publicação no PyPI). Não há timer automático —
o Herbert/agentes devem checar no início das sessões enquanto a pendência estiver aberta
(1 linha de curl — custo zero).
