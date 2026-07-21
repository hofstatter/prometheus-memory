---
name: auto-memory
description: >
  Ativa o Mnemosyne como cérebro automático de toda sessão do agente.
  Grava decisões, implementações e contexto sem intervenção manual.
  Recupera contexto relevante no início de cada sessão.
user_invocable: true
---

# Auto-Memory — Cérebro Transparente

Você é um agente com memória persistente via Mnemosyne. Sua função é garantir
que **toda** sessão seja registrada automaticamente, sem que o usuário precise
pedir.

## Regras Obrigatórias (NÃO negociáveis)

### 1. INÍCIO DE SESSÃO — Recuperar Contexto

**Sempre** execute estes passos antes de qualquer ação:

1. `mnemosyne_stats` — verificar quantas memórias existem
2. `mnemosyne_recall "últimas decisões e implementações"` — contexto relevante
3. Se houver memórias relevantes, mencione-as brevemente ("Contexto recuperado: N memórias encontradas sobre X")

### 2. DURANTE A SESSÃO — Gravar Automaticamente

Após **cada** uma destas ações, chame `mnemosyne_remember`:

| Gatilho | Exemplo de store |
|---|---|
| **Implementação concluída** | `"[PROJETO] implementacao [descrição curta] — DD/MM/AAAA"` |
| **Decisão importante** | `"[PROJETO] decisao [descrição curta] — DD/MM/AAAA"` |
| **Nova ferramenta instalada** | `"[PROJETO] nova-ferramenta [nome] instalada em [path] — DD/MM/AAAA"` |
| **Configuração alterada** | `"[PROJETO] config [arquivo] modificado: [o quê] — DD/MM/AAAA"` |
| **Bug encontrado** | `"[PROJETO] issue [descrição curta] — DD/MM/AAAA"` |

**Formato:** Use sempre `[PROJETO] [tipo] [descrição] — DD/MM/AAAA` para facilitar busca.

Importância: use `0.8` para decisões/implementações, `0.5` para contexto geral.

### 2.5 OFFLOADING DE LOGS — Manter Contexto Limpo

Quando uma ferramenta retornar **> 500 caracteres** de output, faça offload:

1. `python3 ~/bin/ref_manager.py save "<tool_name>" "<project>" "<conteudo>"` — obtém node_id
2. Substitua o output bruto no contexto por: `[ref:NODE_ID] <tool>: "<query>" — X.XKB offloaded`
3. Se precisar do texto completo depois: `python3 ~/bin/ref_manager.py load <node_id>`

> Isso reduz o consumo de tokens em até 61% (baseado no TencentDB-Agent-Memory).

### 3. FIM DE SESSÃO — Resumo

Quando a sessão estiver terminando (usuário sai, tarefa concluída):

1. Liste mentalmente tudo que foi feito
2. `mnemosyne_remember` com resumo consolidado:
   `"[PROJETO] sessao-resumo [N] implementações: [lista curta] — DD/MM/AAAA"`
3. Execute: `python3 ~/bin/session_logger.py "PROJETO" "resumo da sessão" "ação1,ação2,ação3" TOKENS`
4. Guarde o session_id retornado e inclua no último remember: `"... | ref:SESSION_ID"`

## Nunca faça

- ❌ Não espere o usuário pedir para gravar — grave automaticamente
- ❌ Não pule o recall no início da sessão
- ❌ Não armazene secrets, tokens ou senhas
- ❌ Não faça store de informações triviais (ex: "usuário disse olá")
- ❌ Não exceda 500 tokens por store
