# Security Policy

## Modelo de segurança

O Prometheus Memory é **single-user e local-first**. O bind padrão é `127.0.0.1`
— nesse modo, a trust boundary é a máquina local.

- Se `PROMETHEUS_HOST != 127.0.0.1`, **todas** as rotas exigem
  `Authorization: Bearer $PROMETHEUS_TOKEN`. Sem token configurado, o serviço
  responde 500 até que você defina um (`openssl rand -hex 24`).
- Não é multi-tenant: todos os agentes da máquina compartilham o mesmo store
  (isolamento por agente chega na v0.2 — ver docs/ROADMAP.md).
- Anti-SSRF com revalidação de redirects, anti path-traversal, sanitização de
  coleções, uploads com whitelist de extensão e limite de 50MB.

## Reportar vulnerabilidade

Abra uma issue com o prefixo `[security]` ou contate via X @hofstatter.
Não inclua PoC pública antes de 14 dias para correção.
