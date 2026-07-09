<div align="center">

# Vehicle Tracker Platform

**White-label ERP and telemetry platform for fleet management, device tracking, and field operations.**

[![Python](https://img.shields.io/badge/Python-3.11+-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-009688?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![Next.js](https://img.shields.io/badge/Next.js-15-000000?logo=next.js&logoColor=white)](https://nextjs.org/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-16-4169E1?logo=postgresql&logoColor=white)](https://www.postgresql.org/)
[![Redis](https://img.shields.io/badge/Redis-7-DC382D?logo=redis&logoColor=white)](https://redis.io/)
[![Docker](https://img.shields.io/badge/Docker-Compose-2496ED?logo=docker&logoColor=white)](https://docs.docker.com/compose/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Status](https://img.shields.io/badge/Status-Alpha-orange)](CHANGELOG.md)

![Vehicle Tracker Platform](docs/assets/banner-placeholder.svg)

*End-to-end vehicle tracking with GT06 ingestion, ERP modules, and a modern admin dashboard.*

[Features](#features) ·
[Architecture](#architecture) ·
[Getting Started](#getting-started) ·
[Roadmap](#roadmap) ·
[Contributing](CONTRIBUTING.md) ·
[Português](README.pt-BR.md)

</div>

---

## Features

### ERP

| Module | Description |
|--------|-------------|
| **CRM** | Customer management with search, pagination, soft delete, and audit logs |
| **Fleet** | Vehicle registry with plate/chassis validation and customer linkage |
| **Devices** | Tracker (IMEI) inventory, origin tracking, and assignment workflows |
| **Installations** | Field installation scheduling linking trackers, vehicles, and customers |

### Tracking

| Component | Description |
|-----------|-------------|
| **GT06 Gateway** | TCP server for J16/GT06 protocol parsing and session management |
| **Worker** | Async consumer that validates and persists telemetry events |
| **Redis Streams** | Durable event bus (`tracker:events`) with dead-letter queue |
| **Telemetry** | Position, heartbeat, and connection events stored in PostgreSQL |

### Security

| Capability | Description |
|------------|-------------|
| **JWT** | Short-lived access tokens + HttpOnly refresh cookies |
| **RBAC** | Role-based access control (`admin`, `operator`, `viewer`) |
| **Audit Logs** | Login attempts and business action auditing |

### Infrastructure

| Capability | Description |
|------------|-------------|
| **Docker** | Full stack via Docker Compose with health checks |
| **Healthchecks** | `/live` endpoints on every service |
| **Observability** | Structured JSON logs and Prometheus-ready metrics |

---

## Architecture

```text
GT06 Devices / Simulator
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
    │ PostgreSQL │  ERP + telemetry tables
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

### Repository Structure

```text
vehicle-tracker/
├── backend/              # FastAPI REST API + ERP domains
│   ├── alembic/          # Database migrations
│   ├── app/
│   │   ├── domains/      # CRM, Fleet, Devices, Operations, Identity…
│   │   ├── kernel/       # Config, DB, security, middlewares
│   │   └── seed/         # Admin bootstrap
│   └── tests/
├── frontend/             # Next.js 15 + Tailwind CSS
├── gateway/              # GT06 TCP Gateway
├── worker/               # Redis Streams consumer
├── docker/               # Docker Compose stack
├── docs/                 # Architecture, ADRs, roadmap
├── scripts/              # Simulators and health-check utilities
├── .env.example          # Environment template
├── CHANGELOG.md
├── CONTRIBUTING.md
└── LICENSE
```

---

## Screenshots

> Placeholder sections for upcoming documentation images.

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

- **FastAPI** — async REST API
- **SQLAlchemy 2** — async ORM with PostgreSQL
- **Alembic** — schema migrations
- **Pydantic v2** — validation and settings
- **Argon2** — password hashing
- **PyJWT** — token management

### Frontend

- **Next.js 15** — App Router, standalone output
- **React 19** — UI components
- **Tailwind CSS** — styling
- **Lucide React** — icons

### Database

- **PostgreSQL 16** — primary data store
- **Redis 7** — sessions, rate limiting, event streams

### Infrastructure

- **Docker Compose** — local and deployment orchestration
- **Prometheus-ready metrics** — gateway and worker instrumentation
- **Structured JSON logging** — cross-service observability

---

## Getting Started

### Prerequisites

- [Docker](https://docs.docker.com/get-docker/) and Docker Compose v2
- Git

### Installation

```bash
git clone https://github.com/your-org/vehicle-tracker.git
cd vehicle-tracker
cp .env.example .env
```

Edit `.env` and set strong values for `POSTGRES_PASSWORD` and `JWT_SECRET_KEY`.

### Docker

```bash
cd docker
docker compose up --build
```

| Service | URL |
|---------|-----|
| Frontend | http://localhost:3000 |
| API Docs | http://localhost:8000/docs |
| Backend Health | http://localhost:8000/live |
| Gateway Health | http://localhost:5024/live |
| Worker Health | http://localhost:9100/live |

### Environment Variables

All variables are documented in [`.env.example`](.env.example). Key groups:

- **PostgreSQL** — `DATABASE_URL`, `POSTGRES_*`
- **Redis** — `REDIS_URL`, stream keys, consumer group
- **Auth** — `JWT_SECRET_KEY`, token TTL, rate limits
- **Gateway** — TCP port, health port, connection limits
- **Frontend** — `NEXT_PUBLIC_API_URL`, `INTERNAL_API_URL`

### Migrations

Alembic migrations run automatically on backend startup (`alembic upgrade head`). To run manually:

```bash
cd backend
alembic upgrade head
```

### Seed / Bootstrap

On first startup with an empty database, the backend creates:

| Field | Value |
|-------|-------|
| Email | `admin@example.com` |
| Password | `admin123` |

> **Warning:** Change the default password immediately in production environments.

### Default Login

1. Open http://localhost:3000
2. Sign in with `admin@example.com` / `admin123`
3. Explore CRM, Fleet, Devices, and Installations modules

---

## Roadmap

| Status | Item |
|--------|------|
| ✅ Done | CRM |
| ✅ Done | Fleet |
| ✅ Done | Devices |
| ✅ Done | Installations |
| 🔄 In Progress | Telemetry Sync |
| 📋 Planned | Monitoring |
| 📋 Planned | Commands |
| 📋 Planned | Alerts |
| 📋 Planned | Finance |
| 📋 Planned | License |

See [docs/ROADMAP.md](docs/ROADMAP.md) for detailed sprint planning.

---

## Documentation

- [Architecture](docs/architecture.md)
- [Architecture Principles](docs/ARCHITECTURE_PRINCIPLES.md)
- [ADRs](docs/adr/)
- [Changelog](CHANGELOG.md)
- [Contributing](CONTRIBUTING.md)

---

## License

This project is licensed under the [MIT License](LICENSE).

---

<div align="center">

Built for fleet operators, integrators, and white-label platforms.

</div>
