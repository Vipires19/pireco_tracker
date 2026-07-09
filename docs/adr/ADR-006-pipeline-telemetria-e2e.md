# ADR-006: Pipeline de telemetria E2E (Fase 0.5)

## Contexto

A arquitetura base (Fase 0) separou gateway, worker e API, mas não validava o fluxo completo de telemetria do rastreador até a consulta via API.

## Problema

Sem um pipeline funcional ponta a ponta, não é possível validar integrações, medir latência real nem demonstrar valor técnico antes de investir em funcionalidades de usuário.

## Alternativas consideradas

1. **Testar apenas com equipamento físico J16** — dependência de hardware, difícil automatizar.
2. **Pipeline E2E com simulador GT06 + persistência + API de consulta** — reproduzível e automatizável.
3. **Mock completo sem Redis/PostgreSQL** — não valida infraestrutura real.

## Decisão tomada

Implementar pipeline completo:

```text
Simulador GT06 → Gateway → Redis Streams → Worker → PostgreSQL → GET /positions/latest/{imei}
```

Incluir tabelas `positions` e `device_events`, simulador, testes unitários e métricas Prometheus preparatórias.

## Consequências

- POC reproduzível via Docker Compose + simulador.
- Validação de latência gateway→worker via campo `published_at`.
- Base sólida para Fase 1 (CRUD, auth, dashboard).
- Simulador e testes permitem CI sem hardware.
