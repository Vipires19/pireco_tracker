<div align="center">

# Vehicle Tracker Platform

**Plataforma white-label de ERP e telemetria para gestão de frotas, rastreadores e operações de campo.**

[![Python](https://img.shields.io/badge/Python-3.11+-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-009688?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![Next.js](https://img.shields.io/badge/Next.js-15-000000?logo=next.js&logoColor=white)](https://nextjs.org/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-16-4169E1?logo=postgresql&logoColor=white)](https://www.postgresql.org/)
[![Redis](https://img.shields.io/badge/Redis-7-DC382D?logo=redis&logoColor=white)](https://redis.io/)
[![Docker](https://img.shields.io/badge/Docker-Compose-2496ED?logo=docker&logoColor=white)](https://docs.docker.com/compose/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Status](https://img.shields.io/badge/Status-Alpha-orange)](CHANGELOG.md)

![Vehicle Tracker Platform](docs/assets/banner-placeholder.svg)

*Rastreamento veicular ponta a ponta com ingestão GT06, módulos ERP e painel administrativo moderno.*

[Funcionalidades](#funcionalidades) ·
[Arquitetura](#arquitetura) ·
[Primeiros Passos](#primeiros-passos) ·
[Roadmap](#roadmap) ·
[Contribuindo](CONTRIBUTING.md) ·
[English](README.md)

</div>

---

## Funcionalidades

### ERP

| Módulo | Descrição |
|--------|-----------|
| **CRM** | Gestão de clientes com busca, paginação, soft delete e audit logs |
| **Fleet** | Cadastro de veículos com validação de placa/chassi e vínculo com clientes |
| **Devices** | Inventário de rastreadores (IMEI), origem e fluxos de atribuição |
| **Installations** | Agendamento de instalações vinculando rastreadores, veículos e clientes |

### Tracking

| Componente | Descrição |
|------------|-----------|
| **GT06 Gateway** | Servidor TCP para parsing do protocolo J16/GT06 e gestão de sessões |
| **Worker** | Consumer assíncrono que valida e persiste eventos de telemetria |
| **Redis Streams** | Barramento de eventos (`tracker:events`) com dead-letter queue |
| **Telemetry** | Posições, heartbeats e eventos de conexão armazenados no PostgreSQL |

### Security

| Capacidade | Descrição |
|------------|-----------|
| **JWT** | Access tokens de curta duração + cookies HttpOnly de refresh |
| **RBAC** | Controle de acesso por papéis (`admin`, `operator`, `viewer`) |
| **Audit Logs** | Auditoria de tentativas de login e ações de negócio |

### Infrastructure

| Capacidade | Descrição |
|------------|-----------|
| **Docker** | Stack completa via Docker Compose com health checks |
| **Healthchecks** | Endpoints `/live` em todos os serviços |
| **Observability** | Logs estruturados em JSON e métricas prontas para Prometheus |

---

## Arquitetura

```text
Dispositivos GT06 / Simulador
         │
         ▼
    ┌─────────┐
    │ Gateway │  :5023 TCP / :5024 health
    └────┬────┘
         │
         ▼
    ┌─────────┐
    │  Redis  │  Streams: tracker:events
    └────┬────┘
         │
         ▼
    ┌─────────┐
    │ Worker  │  Consumer group: tracker-workers
    └────┬────┘
         │
         ▼
    ┌────────────┐
    │ PostgreSQL │  Tabelas ERP + telemetria
    └─────┬──────┘
          │
          ▼
    ┌─────────┐
    │ FastAPI │  :8000 REST API
    └────┬────┘
         │
         ▼
    ┌─────────┐
    │ Next.js │  :3000 Admin UI
    └─────────┘
```

### Estrutura do Repositório

```text
vehicle-tracker/
├── backend/              # API REST FastAPI + domínios ERP
│   ├── alembic/          # Migrações de banco
│   ├── app/
│   │   ├── domains/      # CRM, Fleet, Devices, Operations, Identity…
│   │   ├── kernel/       # Config, DB, security, middlewares
│   │   └── seed/         # Bootstrap do admin
│   └── tests/
├── frontend/             # Next.js 15 + Tailwind CSS
├── gateway/              # GT06 TCP Gateway
├── worker/               # Consumer Redis Streams
├── docker/               # Stack Docker Compose
├── docs/                 # Arquitetura, ADRs, roadmap
├── scripts/              # Simuladores e utilitários de health-check
├── .env.example          # Template de variáveis de ambiente
├── CHANGELOG.md
├── CONTRIBUTING.md
└── LICENSE
```

---

## Screenshots

> Seções placeholder para futuras imagens de documentação.

| Dashboard | Vehicles |
|:---------:|:--------:|
| ![Dashboard placeholder](docs/assets/screenshot-dashboard-placeholder.svg) | ![Vehicles placeholder](docs/assets/screenshot-vehicles-placeholder.svg) |

| Trackers | Installations |
|:--------:|:-------------:|
| ![Trackers placeholder](docs/assets/screenshot-trackers-placeholder.svg) | ![Installations placeholder](docs/assets/screenshot-installations-placeholder.svg) |

| Monitoring |
|:----------:|
| ![Monitoring placeholder](docs/assets/screenshot-monitoring-placeholder.svg) |

---

## Tech Stack

### Backend

- **FastAPI** — API REST assíncrona
- **SQLAlchemy 2** — ORM assíncrono com PostgreSQL
- **Alembic** — migrações de schema
- **Pydantic v2** — validação e settings
- **Argon2** — hash de senhas
- **PyJWT** — gestão de tokens

### Frontend

- **Next.js 15** — App Router, output standalone
- **React 19** — componentes de UI
- **Tailwind CSS** — estilização
- **Lucide React** — ícones

### Database

- **PostgreSQL 16** — armazenamento principal
- **Redis 7** — sessões, rate limiting, event streams

### Infrastructure

- **Docker Compose** — orquestração local e de deploy
- **Métricas Prometheus-ready** — instrumentação no Gateway e Worker
- **Logs JSON estruturados** — observabilidade entre serviços

---

## Primeiros Passos

### Pré-requisitos

- [Docker](https://docs.docker.com/get-docker/) e Docker Compose v2
- Git

### Instalação

```bash
git clone https://github.com/your-org/vehicle-tracker.git
cd vehicle-tracker
cp .env.example .env
```

Edite o `.env` e defina valores seguros para `POSTGRES_PASSWORD` e `JWT_SECRET_KEY`.

### Docker

```bash
cd docker
docker compose up --build
```

| Serviço | URL |
|---------|-----|
| Frontend | http://localhost:3000 |
| API Docs | http://localhost:8000/docs |
| Backend Health | http://localhost:8000/live |
| Gateway Health | http://localhost:5024/live |
| Worker Health | http://localhost:9100/live |

### Variáveis de Ambiente

Todas as variáveis estão documentadas em [`.env.example`](.env.example). Grupos principais:

- **PostgreSQL** — `DATABASE_URL`, `POSTGRES_*`
- **Redis** — `REDIS_URL`, chaves de stream, consumer group
- **Auth** — `JWT_SECRET_KEY`, TTL dos tokens, rate limits
- **Gateway** — porta TCP, porta de health, limites de conexão
- **Frontend** — `NEXT_PUBLIC_API_URL`, `INTERNAL_API_URL`

### Migrações

As migrações Alembic rodam automaticamente no startup do backend (`alembic upgrade head`). Para executar manualmente:

```bash
cd backend
alembic upgrade head
```

### Seed / Bootstrap

Na primeira inicialização com banco vazio, o backend cria:

| Campo | Valor |
|-------|-------|
| E-mail | `admin@example.com` |
| Senha | `admin123` |

> **Atenção:** Altere a senha padrão imediatamente em ambientes de produção.

### Login Padrão

1. Acesse http://localhost:3000
2. Entre com `admin@example.com` / `admin123`
3. Explore os módulos CRM, Fleet, Devices e Installations

---

## Roadmap

| Status | Item |
|--------|------|
| ✅ Concluído | CRM |
| ✅ Concluído | Fleet |
| ✅ Concluído | Devices |
| ✅ Concluído | Installations |
| 🔄 Em andamento | Telemetry Sync |
| 📋 Próximos | Monitoring |
| 📋 Próximos | Commands |
| 📋 Próximos | Alerts |
| 📋 Próximos | Finance |
| 📋 Próximos | License |

Consulte [docs/ROADMAP.md](docs/ROADMAP.md) para o planejamento detalhado das sprints.

---

## Documentação

- [Arquitetura](docs/architecture.md)
- [Princípios de Arquitetura](docs/ARCHITECTURE_PRINCIPLES.md)
- [ADRs](docs/adr/)
- [Changelog](CHANGELOG.md)
- [Contribuindo](CONTRIBUTING.md)

---

## License

Este projeto está licenciado sob a [MIT License](LICENSE).

---

<div align="center">

Desenvolvido para operadores de frota, integradores e plataformas white-label.

</div>
