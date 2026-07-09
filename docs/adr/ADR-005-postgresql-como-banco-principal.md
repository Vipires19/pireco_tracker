# ADR-005: PostgreSQL como banco principal

## Contexto

A plataforma precisa persistir cadastros multiempresa (companies, vehicles, trackers), histórico de posições, eventos e associações entre veículos e equipamentos.

## Problema

Redis é excelente para cache e mensageria, mas não é adequado como fonte de verdade para dados relacionais com integridade referencial, queries complexas e relatórios.

## Alternativas consideradas

1. **Redis como banco principal** — rápido, sem joins nem ACID completo para o modelo relacional.
2. **PostgreSQL** — relacional, maduro, suporte a JSON, extensões geoespaciais (PostGIS futuro).
3. **MongoDB** — flexível, porém o modelo é predominantemente relacional (company → vehicle → tracker).

## Decisão tomada

Utilizar **PostgreSQL 16** como banco principal de persistência. Redis permanece para Streams (barramento) e cache de sessão de dispositivos (`tracker:session:{imei}`).

Migrations gerenciadas por **Alembic** no serviço backend (único dono do schema).

## Consequências

- Integridade referencial entre Company, Vehicle, Tracker e TrackerAssignment.
- Worker e backend acessam o mesmo schema, cada um com seus próprios modelos SQLAlchemy (sem imports cruzados).
- Redis cache de sessão tem TTL e não substitui dados persistidos.
- PostGIS pode ser adicionado em migration futura para geofence e mapas.
