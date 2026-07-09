# ADR-003: Worker dedicado para processamento

## Contexto

Eventos publicados pelo gateway precisam ser persistidos, transformados em estado de negócio e submetidos a regras que não devem bloquear nem o gateway TCP nem a API REST.

## Problema

Processar eventos do Redis dentro do FastAPI mistura responsabilidades de ingestão com API, dificulta retry independente e pode degradar latência de endpoints HTTP durante picos de telemetria.

## Alternativas consideradas

1. **Processamento no FastAPI via background tasks** — simples, acoplado e não resiliente a reinícios.
2. **Celery + broker** — maduro, porém overhead de setup para a fase atual.
3. **Worker dedicado consumindo Redis Streams** — serviço focado, deploy independente.

## Decisão tomada

Criar serviço **`worker/`** dedicado que consome Redis Streams, persiste no PostgreSQL, atualiza cache de sessão e executará regras de negócio nas fases seguintes.

O FastAPI permanece exclusivamente como camada de API (REST, WebSocket futuro, autenticação, consultas).

## Consequências

- Separação clara entre ingestão (gateway), processamento (worker) e consulta (backend).
- Worker pode ser escalado independentemente conforme volume de eventos.
- FastAPI não importa nem conhece módulos internos do gateway ou worker.
- Necessidade de health check operacional do worker (via logs/métricas; HTTP opcional em fase futura).
