# Arquitetura — Vehicle Tracker (Fase 0.5)

## Pipeline de Telemetria E2E

```text
J16 Pro / J16 Ultra (ou Simulador GT06)
        │
        ▼
Telemetry Gateway (:5023 TCP)
  ├── Protocol Parser (GT06)
  ├── Session Manager
  └── Domain Mapper
        │
        ▼
Domain Objects (protocolo-agnósticos)
  ├── DevicePosition
  ├── DeviceHeartbeat
  ├── DeviceEvent
  └── DeviceConnection
        │
        ▼
Redis Streams (tracker:events)
        │
        ▼
Worker (consumer group: tracker-workers)
  ├── Validação de contrato
  ├── Persistência PostgreSQL
  └── Cache de sessão Redis
        │
        ▼
PostgreSQL
  ├── companies, fleets, vehicles, trackers
  ├── positions, device_events
  └── tracker_assignments
        │
        ▼
FastAPI (:8000)
  ├── GET /health
  └── GET /positions/latest/{imei}
```

## Responsabilidades

| Serviço | Faz | Não faz |
|---------|-----|---------|
| Gateway | TCP, GT06, domínio, sessões, métricas | Regras de negócio, SQL |
| Worker | Consumo stream, persistência, cache | HTTP API, parsing GT06 |
| Backend | Consultas REST, health | Processar eventos do gateway |
| Frontend | Placeholder | Telemetria (Fase 1+) |

## Observabilidade (Prometheus-ready)

### Gateway (`:5024/metrics`)

| Métrica | Tipo | Descrição |
|---------|------|-----------|
| `gateway_tcp_connections_active` | Gauge | Conexões TCP ativas |
| `gateway_packets_received_total` | Counter | Pacotes recebidos |
| `gateway_packets_invalid_total` | Counter | Pacotes inválidos |
| `gateway_acks_sent_total` | Counter | ACKs enviados |
| `gateway_events_published_total` | Counter | Eventos publicados (por tipo) |

### Worker (logs estruturados + métricas internas)

| Métrica | Tipo | Descrição |
|---------|------|-----------|
| `worker_events_processed_total` | Counter | Eventos processados |
| `worker_events_failed_total` | Counter | Falhas de processamento |
| `worker_pipeline_latency_seconds` | Histogram | Latência gateway→worker |

## ERP — Sprint 1 (Backend DDD-lite)

```text
Frontend (Next.js :3000)
  ├── Proxy /api/v1/* → Backend
  ├── AuthProvider (access token + refresh cookie)
  └── Layout administrativo
        │
        ▼
Backend FastAPI (:8000)
  ├── domains/identity/     User, Role, Auth API
  ├── domains/monitoring/   Dashboard overview
  ├── kernel/               config, database, security, middlewares
  └── seed/bootstrap.py     Admin automático
        │
        ▼
PostgreSQL
  ├── users, roles, user_roles
  ├── refresh_tokens, login_audit_logs
  └── (telemetria existente)
```

### Autenticação

- Access Token JWT (15 min) — Bearer header
- Refresh Token JWT (7 dias) — HttpOnly cookie
- Argon2 password hash
- Rate limit login (Redis)
- Auditoria `login_audit_logs`

## Validação E2E

```bash
# 1. Subir stack
cd docker && docker compose up -d --build
docker compose exec backend alembic upgrade head

# 2. Executar simulador
python scripts/gt06_simulator.py --imei 867686031234567

# 3. Consultar posição
curl http://localhost:8000/positions/latest/867686031234567
```

## ADRs

Ver `docs/adr/` — ADR-001 a ADR-006.

## Protocolos

Ver `docs/PROTOCOLS.md`.
