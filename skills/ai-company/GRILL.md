# GRILL — Entrevista Implacável do PRD (com Checkpointing)

> Baseada na skill `grill-me` de mattpocock (github.com/mattpocock/skills), com melhoria Bytex: **checkpointing obrigatório** — nenhuma resposta se perde, mesmo em entrevistas longas.

## O que é

Entreviste o usuário **implacavelmente** sobre o plano/design do produto até vocês dois terem um entendimento COMPARTILHADO e COMPLETO. Uma pergunta por vez. Sempre.

## Regras

1. **Uma pergunta por vez** — nunca agrupe perguntas. Se precisar de 12 respostas, faça 12 perguntas.
2. **Respostas recomendadas** — a cada pergunta, ofereça 2-4 opções de resposta (com sua recomendação marcada) + opção de resposta livre
3. **Cave até o fundo** — resposta vaga gera follow-up, não aceitação. "Quero um app de tarefas" → "Para quem? O que eles fazem hoje que não funciona?"
4. **Desafie premissas** — se o usuário pedir algo que parece errado, pergunte o porquê antes de aceitar
5. **Cubra os 6 eixos obrigatórios:**
   - Problema (o que dói, pra quem, como resolvem hoje)
   - Usuários (quem paga, quem usa, quem decide)
   - Escopo (o que está DENTRO e o que está FORA — igualmente importante)
   - Sucesso (métrica que prova que funcionou)
   - Restrições (prazo, orçamento, stack, integrações)
   - Receita (como ganha dinheiro — consulte `REVENUE.md`; se for launch, `VIRAL.md`)
6. **Regra do paywall (obrigatória):** se o produto tiver qualquer forma de trial, free tier ou "grátis por X dias", o regime é **decisão explícita do usuário, nunca silenciosa**. Pergunte: "trial exige cartão?" — VIRAL #8 (hard paywall) recomenda pedir cartão sempre. Documente a decisão no checkpoint do brainstorm (lição do teste v2: trial sem cartão passou batido na 1ª rodada e só foi pego no review)
7. **Só termina quando** você conseguir repetir o plano de volta ao usuário sem nenhuma surpresa da parte dele

## Checkpointing OBRIGATÓRIO

Após **CADA** pergunta respondida, faça append imediato em `brainstorms/<projeto>.md` (crie a pasta se não existir):

```markdown
## Q<N> — <pergunta feita>
**Resposta:** <resposta do usuário>
**Decisão:** <decisão derivada, se houver — senão "—">
**Destaque:** <insight relevante, se houver — senão "—">
```

### Header do arquivo (criar na primeira pergunta)

```markdown
# Brainstorm — <nome do projeto>
- **Data:** DD/MM/AAAA
- **Status:** em andamento | concluído
- **Eixos cobertos:** problema ☐ usuários ☐ escopo ☐ sucesso ☐ restrições ☐ receita ☐
```

Atualize os checkboxes dos eixos a cada checkpoint. Marque `Status: concluído` quando os 6 eixos estiverem cobertos.

### Por que isso existe

Entrevistas longas perdem contexto. Com checkpointing:
- A resposta de 40 minutos atrás está gravada — nunca "esquece"
- O usuário pode retomar a entrevista em outra sessão lendo o arquivo
- O PRD (Etapa 1) é gerado a partir do arquivo de brainstorm, não da memória da conversa

## Proibições

- ❌ Avançar para o PRD com eixo descoberto
- ❌ Fazer pergunta sem oferecer respostas recomendadas
- ❌ Responder a pergunta pelo usuário sem confirmação
- ❌ Pular o checkpoint após uma resposta

## Transição para o PRD

Quando os 6 eixos estiverem cobertos:
1. Marque `Status: concluído` no brainstorm
2. Gere o `PRD.md` (template `./PRD.md`) **citando o brainstorm como fonte**
3. Apresente o PRD ao usuário → GATE de aprovação
