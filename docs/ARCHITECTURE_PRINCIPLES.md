# Princípios Arquiteturais — Vehicle Tracker

Este documento define as regras invioláveis da plataforma. Toda decisão técnica deve respeitar estes princípios.

---

## 1. Protocolos nunca chegam ao Backend

O Backend (FastAPI) não conhece GT06, Teltonika, Queclink ou JT808. Ele consome apenas objetos de domínio protocolo-agnósticos e dados persistidos no PostgreSQL.

## 2. Todo protocolo gera objetos de domínio

Cada gateway de protocolo transforma bytes em contratos públicos versionados (`DevicePosition`, `DeviceHeartbeat`, `DeviceEvent`, `DeviceConnection`) definidos em `shared/contracts/`.

## 3. Gateway não possui regra de negócio

O Gateway é camada de transporte e tradução. Não persiste dados, não aplica regras de negócio e não toma decisões sobre cadastro de veículos ou frotas.

## 4. Worker processa eventos

Todo evento do Redis Streams é consumido exclusivamente pelo Worker, que valida contratos, garante idempotência, aplica retry/DLQ e persiste no PostgreSQL.

## 5. Backend serve apenas APIs

O FastAPI expõe REST (e futuramente WebSocket) para consultas e operações administrativas. Não consome streams nem processa telemetria em tempo real.

## 6. Comunicação apenas por contratos públicos

Gateway → Redis Streams → Worker → PostgreSQL → Backend. A comunicação entre serviços ocorre exclusivamente por contratos versionados (`schema_version`), Redis Streams ou banco de dados.

## 7. Nenhum serviço importa código interno de outro

O pacote `shared/` contém apenas contratos, logging, exceções e configuração base. Lógica de protocolo fica no Gateway; lógica de persistência no Worker; lógica de API no Backend.

## 8. Toda decisão arquitetural relevante gera um ADR

Mudanças estruturais são documentadas em `docs/adr/` com contexto, alternativas, decisão e consequências.

## 9. Segurança é responsabilidade de todos os serviços

Cada serviço valida entradas, protege credenciais via variáveis de ambiente, não expõe dados sensíveis em logs e segue o princípio do menor privilégio.

## 10. Modularidade acima de conveniência

Preferimos serviços independentes, contratos explícitos e deploy separado em vez de atalhos que acoplam componentes.

---

## Rastreamento ponta a ponta

Todo evento possui `trace_id` gerado no Gateway e propagado via Redis Streams até o Worker e banco de dados, permitindo auditoria completa da jornada.

## Resiliência

- **Retry configurável** antes de desistir do processamento
- **Dead Letter Queue** (`tracker:dead-letter`) — nenhum evento é perdido
- **Idempotência** via `processed_events` — deduplicação por IMEI, timestamp GPS, serial e hash

## Observabilidade

- Logs estruturados JSON (Loki/ELK/OpenSearch)
- Métricas Prometheus em `/metrics`
- Health checks Kubernetes: `/health`, `/ready`, `/live`
