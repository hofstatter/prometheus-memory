# PLAN — MCP Multi-Usuário Remoto: DEV de qualquer lugar conecta ao Prometheus

> **Data:** 03/08/2026
> **Autor:** Arquiteto (Kimi K3) + Pedreiro (DeepSeek V4 Flash)
> **Aprovado por:** Herbert (decisões 1-4 confirmadas 03/08)
> **Classificação:** MEDIUM (MCP server novo + auth por token + rede)
> **Status:** Plano criado — aguarda execução faseada (M0 → M1 → M2 → M3)
> **Backup:** `~/backups/prometheus-memory/plano-mcp-multiusuario-remoto/20260804-005212/`

---

## 1. Decisões confirmadas por Herbert

1. **Rede**: **Tailscale** (recomendado) agora — privado, zero exposição pública; **quando escalar → VPS + TLS + domínio**.
2. **Transporte**: novo **servidor MCP (SSE)** do Prometheus com as PM tools (não só REST).
3. **Harnesses alvo**: OpenCode + Claude Code + Codex + outros conhecidos (cada um com seu transporte; bridge stdio quando não houver SSE).
4. **Escopo do dev remoto**: **só escreve eventos/memória do próprio usuário** (não lê relatórios do time; painel admin é plano separado).

## 2. Objetivo

Permitir que um dev — de outra cidade, estado ou país — conecte **seu harness** (OpenCode/Claude Code/Codex) ao Prometheus **via MCP**, autenticado por **token próprio**, escrevendo **eventos e memórias somente do seu usuário**, com presença visível (para o futuro painel CTO/CEO). Rede privada via **Tailscale**.

## 3. Arquitetura

### 3.1 Fluxo de conexão (dev remoto)
```
[Harness do dev]  --MCP (SSE ou stdio+bridge)-->  [Prometheus MCP :8778/sse]
   Bearer: <DEV_TOKEN> + author_id=<email>                     │
                                                              ▼
                                            valida token → usuário (hash)
                                                              │
                          prometheus_project_event / session_* / remember / recall / skill_suggest
                                                              │
                                              lanes proj:<slug> · sessions · events (author_id = usuário)
```

### 3.2 Superfícies após a implementação
| Superfície | Porta | Protocolo | Quem usa |
|---|---|---|---|
| Mnemosyne MCP (upstream) | `:8765/sse` | MCP SSE | agentes (remember/recall raw) |
| **Prometheus PM MCP (novo)** | `:8778/sse` | **MCP SSE** | agentes (sessões/eventos/presença/contexto/skills) |
| Web UI / API | `:8777` | REST | navegador (dev/CTO/CEO) |

## 4. Componentes

### 4.1 `web/users_registry.py` (novo — auth por token de dev)
```python
# tabela sidecar prometheus_users
# (id, name, email UNIQUE, role TEXT DEFAULT 'dev', token_hash TEXT, created_at, revoked_at)
def issue_token(email, name, role='dev') -> str  # retorna token em texto UMA vez; armazena hash
def validate_token(token) -> dict | None          # {user_id, email, role} ou None
def revoke_token(email) -> bool
def user_by_email(email) -> dict | None
def gate_admin(user) -> bool                       # role in ('admin','cto','ceo')
```
- Token: `pm_<32hex>`; armazenado como SHA-256 (nunca texto).
- CLI de administração: `python3 -m web.users_registry issue dev@email.com` (admin emite/revoga).

### 4.2 `web/pm_mcp.py` (novo — servidor MCP SSE do Prometheus)
- Framework: **FastMCP** (mesmo padrão do ScreenshotAPI MCP) com transporte **SSE** na porta `:8778`.
- Auth: valida `Authorization: Bearer <token>` em cada chamada → resolve usuário → injeta `author_id`/`user_id` no contexto.
- Tools (todas **escopo dev: só escreve/consulta o próprio**):

| Tool | Ação | Restrição |
|---|---|---|
| `prometheus_session_start` | inicia sessão (harness, session_id, project_slug, cwd, git_remote, current_action) | author_id = usuário do token |
| `prometheus_session_heartbeat` | heartbeat + current_action | sessão do usuário |
| `prometheus_session_close` | encerra sessão | sessão do usuário |
| `prometheus_project_event` | evento canônico (idempotente `client_event_id`) | `author_id` forçado = usuário do token |
| `prometheus_project_context` | contexto do projeto (decisões/últimas ações) | leitura permitida do próprio projeto |
| `prometheus_remember` | memória canônica (com `infer` opcional) | lane do usuário/projeto |
| `prometheus_recall` | recall restrito ao canal do usuário | somente canais do usuário |
| `prometheus_skill_suggest` | sugerir skill para o projeto | gera draft (aprovação continua manual) |

- Reutiliza `session_registry`, `projects_registry`, `memory`, `skills_builder` (sem duplicar lógica).
- Rate limit por usuário (ex.: 100 eventos/min) — protege custo LLM (infer).

### 4.3 Ligação usuário ↔ atividade
- `prometheus_project_events` ganha coluna `author_id` (ALTER sidecar é seguro — tabela é do Prometheus).
- `prometheus_sessions` já tem `author_id` (preenchido a partir do token, não confiar no envelope).

### 4.4 Rede — Tailscale (recomendado)
- Instalar/validar Tailscale no NB02 (`tailscale up`), nota do nó: `nb02-prometheus`.
- Devs remotos: `tailscale up` no notebook → mesmo tailnet → acessam `http://<tailscale-ip>:8777` e `:8778/sse`.
- **Escala (quando necessário)**: VPS Contabo + `https://prometheus.<dominio>` (Caddy TLS) + token por dev + rate limit.

### 4.5 Transporte por harness (guia no plano de execução)
| Harness | MCP remoto SSE? | Config |
|---|---|---|
| OpenCode | ✅ | `type: remote, url: http://<ts-ip>:8778/sse, headers: Bearer <DEV_TOKEN>` |
| Claude Code | ⚠️ (suporte HTTP recente) | SSE se suportado; senão bridge stdio |
| Codex | ⚠️ (config stdio) | bridge stdio `npx mcp-remote http://<ts-ip>:8778/sse` |
| Outros (Cursor, Cline, Windsurf...) | variável | SSE direto ou bridge stdio (universal) |

- **Bridge universal**: `npx mcp-remote http://<ts-ip>:8778/sse` — harness fala stdio com o bridge local, o bridge fala HTTP com o servidor.

## 5. Segurança (não negociável)

- Token do dev **sempre hash** no servidor (SHA-256) — nunca texto em disco/DB/log.
- Token emitido **uma única vez** em texto puro (admin copia para o dev; depois só hash).
- Escopo: dev escreve **apenas no próprio** `author_id` — servidor ignora/força `author_id` do token (nunca confia no envelope).
- Leitura de outros usuários/relatórios do time: **não** no escopo do dev (painel admin é plano separado).
- Rate limit por usuário (eventos + `infer`) — protege custo LLM.
- Tailscale = zero exposição pública; VPS+TLS só na escala.

## 6. Fases de execução

### 🟢 M0 — Usuários e tokens (2-3h)
- [ ] `web/users_registry.py` + tabela `prometheus_users` + CLI issue/revoke/list
- [ ] Hash de token, `validate_token`, `gate_admin`
- [ ] Testes: emitir → validar → revogar; token errado → None

**Aceite M0:** emitir token para `dev@exemplo.com`, validar com o token, revogar, validar falha.

### 🟡 M1 — Prometheus MCP (SSE) (4-6h)
- [ ] `web/pm_mcp.py` (FastMCP, SSE :8778) com as 8 tools
- [ ] Auth por token em cada chamada; `author_id` forçado = usuário
- [ ] Coluna `author_id` em `prometheus_project_events` + preenchimento
- [ ] Rate limit por usuário
- [ ] Registro de serviço systemd `prometheus-mcp` (porta :8778)

**Aceite M1:** dev com token roda um harness remoto → `prometheus_project_event` grava evento com o `author_id` dele; outro token não consegue gravar como ele; presence aparece no `GET /api/pm/presence`.

### 🟢 M2 — Rede Tailscale + bridge stdio (2h)
- [ ] Tailscale no NB02 + guia de conexão do dev (Linux/macOS/Windows)
- [ ] Guia por harness: OpenCode (SSE), Claude Code e Codex (SSE ou `mcp-remote`)
- [ ] Smoke: dev remoto simulado (outra máquina do tailnet) escreve evento

**Aceite M2:** dev em outro dispositivo do tailnet conecta o harness e o evento aparece na produção com `author_id` dele.

### 🟢 M3 — Docs + segurança final (2h)
- [ ] `docs/MCP_REMOTO.md` (guia do dev: instalar Tailscale, configurar harness, token)
- [ ] README (4 idiomas) — seção "MCP remoto multi-usuário"
- [ ] Revisão Inspetor (fronteira: auth/token + escopo dev) + commit + push

## 7. Arquivos

| Arquivo | Ação |
|---|---|
| `web/users_registry.py` | novo |
| `web/pm_mcp.py` | novo |
| `web/prometheus_db.py` | coluna `author_id` em events + tabela users |
| `web/session_registry.py` | author_id a partir do token |
| `web/projects_registry.py` | author_id no ingest |
| `web/app.py` | `/api/auth/dev-token` (emitir, admin-only) |
| `systemd/prometheus-mcp.service` | novo |
| `tests/test_users_registry.py` · `tests/test_pm_mcp.py` | novos |
| `docs/MCP_REMOTO.md` · README (4 idiomas) | docs |

## 8. Testes

- **T1**: emitir/validar/revogar token (hash, nunca texto).
- **T2**: MCP `prometheus_project_event` com token A → `author_id` = A; token B não altera.
- **T3**: session_start/heartbeat/close por usuário; presence por projeto mostra só sessões do usuário (escopo).
- **T4**: `prometheus_recall` restrito ao canal do usuário (sem vazamento).
- **T5**: rate limit por usuário (eventos/min).
- **T6**: idempotência `client_event_id` preservada no caminho MCP.

## 9. Critérios de aceite global

1. Dev remoto (Tailscale) conecta OpenCode/Claude/Codex ao Prometheus MCP com token próprio.
2. Eventos/memórias gravados com `author_id` = usuário do token — **nunca** de outro usuário.
3. Presença do dev aparece (para o futuro painel CTO/CEO).
4. Token nunca em texto no servidor; revogação funciona.
5. `pytest` verde (novos + existentes) + smoke MCP real (SSE) + revisão Inspetor.

## 10. Riscos

| Risco | Mitigação |
|---|---|
| Harness sem SSE remoto | bridge stdio `mcp-remote` (universal) |
| Token vazado | revogação imediata; hash no servidor; escopo só do usuário |
| Custo LLM por dev | rate limit + `infer` opcional |
| Tailscale indisponível | VPS + TLS (escala) — documentado |
| Vazamento entre usuários | `author_id` forçado do token; testes T2/T4 |

## 11. Ordem de execução

```
M0 usuários/tokens (2-3h) → M1 Prometheus MCP SSE (4-6h) → M2 Tailscale+bridge (2h) → M3 docs+release (2h)
```
**Estimativa:** ~10-13h (2-3 sessões Pedreiro + Inspetor na fronteira M1).

## 12. Referências

- Envelope multi-harness: `PLAN_PROJETOS_MULTI_SESSAO.md` (§5)
- Presença/sessões: `web/session_registry.py` · eventos: `web/projects_registry.py`
- Mnemosyne MCP (upstream, SSE :8765): `mnemosyne/mcp_server.py` · `mcp_tools.py` (suporta `author_id`/`channel_id`)
- Padrão FastMCP local: `~/.config/opencode/mcp-servers/screenshotapi_mcp.py`
- Bridge stdio↔remoto: `npx mcp-remote` · Tailscale: `https://tailscale.com`
