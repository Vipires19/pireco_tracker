# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- Repository documentation and publishing standards (Sprint Infra 0).

## [0.1.0] - 2026-07-07

### Added

#### Gateway

- GT06 TCP server for device telemetry ingestion.
- Protocol parser, session management, and domain event mapping.
- Redis Streams publisher (`tracker:events`) with dead-letter stream support.
- Health and metrics endpoints on dedicated port.

#### Worker

- Redis Streams consumer group (`tracker-workers`).
- Event validation, persistence to PostgreSQL, and session cache updates.
- Retry policy with configurable backoff and dead-letter queue handling.
- Health endpoint for container orchestration.

#### CRM

- Customer domain with full CRUD API.
- Search, pagination, sorting, and soft delete.
- Audit logging for customer actions.

#### Fleet

- Vehicle domain with full CRUD API.
- Plate and chassis validation.
- Customer association and fleet management endpoints.

#### Devices

- Tracker (device) domain with IMEI management.
- Device origin tracking and assignment workflows.
- CRUD API with validation and soft delete.

#### Installations

- Installation operations domain linking trackers, vehicles, and customers.
- Scheduling and status management API.
- Frontend management screens.

#### Platform

- FastAPI backend with DDD-lite domain structure.
- Next.js administrative frontend with JWT authentication.
- Docker Compose stack (PostgreSQL, Redis, Gateway, Worker, Backend, Frontend).
- Alembic migrations and automatic admin bootstrap on first run.

[Unreleased]: https://github.com/your-org/vehicle-tracker/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/your-org/vehicle-tracker/releases/tag/v0.1.0
