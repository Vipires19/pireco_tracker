# ADR-002: Redis Streams como barramento

## Contexto

O gateway publica eventos de rastreadores que precisam ser processados de forma assíncrona por workers, sem perda de mensagens em caso de reinício.

## Problema

Pub/Sub do Redis não garante entrega — mensagens publicadas enquanto nenhum consumidor está ativo são perdidas. Filas simples sem consumer groups dificultam processamento paralelo e reprocessamento.

## Alternativas consideradas

1. **Redis Pub/Sub** — baixa latência, sem persistência nem ACK.
2. **Redis Streams com consumer groups** — persistência, ACK, reprocessamento e múltiplos consumidores.
3. **RabbitMQ / Kafka** — robustos, porém adicionam complexidade operacional desnecessária na fase inicial.

## Decisão tomada

Utilizar **Redis Streams** (`tracker:events`) com **consumer groups** (`tracker-workers`) como barramento entre gateway e worker.

## Consequências

- Mensagens persistem até serem confirmadas (XACK).
- Múltiplos workers podem consumir em paralelo no futuro.
- Redis já faz parte da stack — sem novo componente de infraestrutura.
- Necessidade de monitorar lag do consumer group e PEL (Pending Entries List).
