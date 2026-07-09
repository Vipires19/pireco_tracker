# ADR-007: Hardening do núcleo de telemetria (Fase 0.6)

## Contexto

O pipeline E2E foi validado na Fase 0.5, mas carecia de resiliência, observabilidade e contratos formalizados para produção.

## Problema

Sem logs estruturados, trace_id, retry, DLQ e idempotência, o núcleo não suporta escala nem depuração em produção. Configurações monolíticas e exceções genéricas dificultam manutenção.

## Alternativas consideradas

1. **Hardening incremental por serviço** — risco de inconsistência entre Gateway, Worker e Backend.
2. **Pacote shared + padrões unificados** — contratos, logging, exceções e config centralizados.
3. **Biblioteca externa (OpenTelemetry only)** — adiciona dependência sem resolver DLQ/retry/idempotência.

## Decisão tomada

- Criar `shared/` com contratos versionados (`schema_version`), logging JSON, exceções e config modular
- Implementar `trace_id` ponta a ponta
- Retry configurável + DLQ `tracker:dead-letter`
- Idempotência via tabela `processed_events`
- Health `/health`, `/ready`, `/live` em todos os serviços
- Métricas Prometheus expandidas
- Simulador de carga `scripts/load_test.py`

## Consequências

- Núcleo preparado para Kubernetes e Grafana
- Refatoração significativa sem quebrar pipeline E2E
- Docker build context alterado para incluir `shared/`
- Testes e simulador devem ser reexecutados após deploy
