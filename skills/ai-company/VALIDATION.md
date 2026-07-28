# VALIDATION — Checklist de Validação

> Usado por QA + Security + Systems Analyst na Etapa 3 (validação da Spec) e Etapa 5 (validação de sprint).

## Validação da Tech Spec (Etapa 3)

### Cobertura e consistência
- [ ] Todos os requisitos do PRD têm solução técnica na Spec
- [ ] As 3 seções (Frontend, Backend, Banco de Dados) estão completas
- [ ] Não há contradições entre seções (ex: schema DB ≠ payload API)
- [ ] Estimativas de complexidade são realistas

### Riscos técnicos
- [ ] Dependências externas identificadas e com fallback
- [ ] Pontos únicos de falha mitigados
- [ ] Performance considerada (queries N+1, payloads grandes)

### Segurança (Security Specialist)
- [ ] Nenhum secret hardcoded ou em texto claro
- [ ] Autenticação/autorização definida
- [ ] Validação de inputs em todos os pontos de entrada
- [ ] Dados sensíveis (PII) identificados e protegidos

**Resultado:** ⬜ ✅ APROVADA · ⬜ ❌ Lista de correções (voltar para Etapa 2)

---

## Validação de Sprint (Etapa 5)

### Build e testes
- [ ] Compila/builda sem erros
- [ ] Testes novos escritos e passando
- [ ] Sem regressão

### Qualidade
- [ ] DoD da sprint completo
- [ ] Código segue padrões do projeto
- [ ] Documentação atualizada

### Segurança
- [ ] Sem secrets/commit acidentais
- [ ] Inputs validados

**Resultado:** ⬜ ✅ SPRINT VALIDADA · ⬜ ❌ Correções necessárias
