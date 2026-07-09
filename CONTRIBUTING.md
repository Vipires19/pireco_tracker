# Contributing to Vehicle Tracker

Thank you for your interest in contributing. This document outlines the workflow, conventions, and architectural principles for this monorepo.

## Table of Contents

- [Getting Started](#getting-started)
- [Branches](#branches)
- [Commits](#commits)
- [Pull Requests](#pull-requests)
- [Code Style](#code-style)
- [Architecture](#architecture)
- [Project Patterns](#project-patterns)
- [Testing](#testing)

## Getting Started

1. Fork the repository and clone it locally.
2. Copy the environment template: `cp .env.example .env`
3. Start the stack: `cd docker && docker compose up --build`
4. Read [README.md](README.md) and [docs/architecture.md](docs/architecture.md).

Never commit `.env` files or secrets. Use `.env.example` for documenting new variables.

## Branches

| Branch | Purpose |
|--------|---------|
| `main` | Stable, release-ready code |
| `develop` | Integration branch (if used) |
| `feature/<name>` | New features |
| `fix/<name>` | Bug fixes |
| `infra/<name>` | Tooling, CI, documentation |
| `chore/<name>` | Maintenance without behavior changes |

Keep branches focused and short-lived. Rebase or merge from `main` regularly to avoid drift.

## Commits

Follow [Conventional Commits](https://www.conventionalcommits.org/):

```
<type>(<scope>): <short description>

[optional body]
```

**Types:** `feat`, `fix`, `docs`, `style`, `refactor`, `test`, `chore`, `infra`

**Scopes (examples):** `backend`, `frontend`, `gateway`, `worker`, `docker`, `crm`, `fleet`, `devices`

Examples:

```
feat(fleet): add vehicle export endpoint
fix(gateway): handle partial GT06 frames
docs(readme): update getting started section
infra(docker): add healthcheck for worker
```

Write commit messages in English. Keep the subject line under 72 characters.

## Pull Requests

1. Open a PR against `main` (or `develop` if the project uses it).
2. Fill in the description: **what** changed, **why**, and **how to test**.
3. Link related issues when applicable.
4. Ensure `docker compose up --build` succeeds locally.
5. Run relevant tests before requesting review.
6. Keep PRs small and reviewable — prefer multiple focused PRs over one large change.

PRs that modify application behavior require at least one approving review. Documentation-only PRs may be merged with lighter review.

## Code Style

### Python (Backend, Gateway, Worker)

- Python 3.11+
- 4-space indentation
- Type hints on public functions and service methods
- `async`/`await` for I/O-bound operations
- Pydantic models for schemas and settings
- Structured JSON logging via the shared logger setup

### TypeScript (Frontend)

- Next.js 15 App Router conventions
- 2-space indentation
- Functional React components with hooks
- Tailwind CSS for styling
- API calls through the Next.js proxy (`/api/v1/*`)

### General

- Respect [.editorconfig](.editorconfig) and [.gitattributes](.gitattributes).
- No secrets in code, commits, or PR descriptions.
- Prefer explicit naming over abbreviations.
- Match existing patterns in the module you are editing.

## Architecture

Vehicle Tracker is a **monorepo** with clear service boundaries:

```text
GT06 Devices
     │
     ▼
  Gateway  ──►  Redis Streams  ──►  Worker  ──►  PostgreSQL
                                                      │
                                                      ▼
                                                  FastAPI  ──►  Next.js
```

### Service Responsibilities

| Service | Responsibility |
|---------|----------------|
| **Gateway** | TCP ingestion, GT06 parsing, event publishing |
| **Worker** | Stream consumption, persistence, cache updates |
| **Backend** | REST API, business domains, authentication |
| **Frontend** | Administrative UI and API proxy |

### Backend Domains (`backend/app/domains/`)

Each domain follows a layered structure:

```text
domain/
├── api/           # FastAPI routers and dependencies
├── models/        # SQLAlchemy entities
├── repositories/  # Data access
├── schemas/       # Pydantic request/response models
├── services/      # Business logic
└── validators.py  # Domain-specific validation
```

Shared infrastructure lives in `backend/app/kernel/` (config, database, security, middlewares).

### Rules

- **Gateway and Worker** must not contain ERP business rules.
- **Backend** must not parse GT06 or consume Redis Streams directly.
- Cross-service contracts should remain protocol-agnostic domain events.
- Database migrations go through Alembic (`backend/alembic/versions/`).

## Project Patterns

- **Settings:** Pydantic Settings per service, loaded from `.env`.
- **Auth:** JWT access token (Bearer) + refresh token (HttpOnly cookie).
- **RBAC:** Role-based permissions defined in `kernel/security/permissions.py`.
- **Soft delete:** Prefer `deleted_at` over hard deletes for business entities.
- **Audit:** Log significant actions (login, CRUD mutations) to audit tables.
- **Health checks:** Each service exposes `/live` (and metrics where applicable).
- **Docker:** All services orchestrated via `docker/docker-compose.yml`.

## Testing

```bash
# Backend
cd backend && pytest tests/ -q

# Gateway
cd gateway && pytest tests/ -q

# Worker
cd worker && pytest tests/ -q
```

Add tests for new API endpoints, validators, and critical business logic. Integration tests should use the existing `conftest.py` fixtures.

---

Questions? Open an issue or start a discussion on GitHub.
