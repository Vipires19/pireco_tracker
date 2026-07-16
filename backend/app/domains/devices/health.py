"""HealthService — fonte única do estado operacional do dispositivo.

Toda a plataforma (Dashboard, Rastreadores, Mapa) calcula Online/Offline
exclusivamente a partir de ``last_seen_at``. Nenhum campo persistido é
utilizado para determinar o estado.

Regras:
- UNKNOWN  → nunca comunicou (last_seen_at nulo)
- ONLINE   → última comunicação ≤ 60 segundos
- UNSTABLE → entre 61 e 180 segundos
- OFFLINE  → acima de 180 segundos
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.devices.models import HealthStatus, Tracker

ONLINE_WINDOW = timedelta(seconds=60)
UNSTABLE_WINDOW = timedelta(seconds=180)


def resolve_health_status(last_seen_at: datetime | None) -> HealthStatus:
    if last_seen_at is None:
        return HealthStatus.UNKNOWN
    ts = last_seen_at if last_seen_at.tzinfo is not None else last_seen_at.replace(tzinfo=UTC)
    elapsed = datetime.now(UTC) - ts
    if elapsed <= ONLINE_WINDOW:
        return HealthStatus.ONLINE
    if elapsed <= UNSTABLE_WINDOW:
        return HealthStatus.UNSTABLE
    return HealthStatus.OFFLINE


def online_since() -> datetime:
    return datetime.now(UTC) - ONLINE_WINDOW


def unstable_since() -> datetime:
    return datetime.now(UTC) - UNSTABLE_WINDOW


def health_conditions(health: HealthStatus) -> list:
    """Condições SQL sobre ``Tracker.last_seen_at`` para o health informado."""
    if health == HealthStatus.ONLINE:
        return [Tracker.last_seen_at.is_not(None), Tracker.last_seen_at >= online_since()]
    if health == HealthStatus.UNSTABLE:
        return [
            Tracker.last_seen_at.is_not(None),
            Tracker.last_seen_at < online_since(),
            Tracker.last_seen_at >= unstable_since(),
        ]
    if health == HealthStatus.OFFLINE:
        return [Tracker.last_seen_at.is_not(None), Tracker.last_seen_at < unstable_since()]
    return [Tracker.last_seen_at.is_(None)]


COMPUTED_HEALTH_STATUSES = (
    HealthStatus.ONLINE,
    HealthStatus.UNSTABLE,
    HealthStatus.OFFLINE,
    HealthStatus.UNKNOWN,
)


@dataclass(frozen=True)
class HealthCounts:
    online: int
    unstable: int
    offline: int
    unknown: int


async def count_tracker_health(session: AsyncSession) -> HealthCounts:
    """Contagens por health — mesma regra utilizada na listagem de rastreadores."""

    async def _count(health: HealthStatus) -> int:
        result = await session.execute(
            select(func.count())
            .select_from(Tracker)
            .where(Tracker.deleted_at.is_(None), *health_conditions(health))
        )
        return int(result.scalar_one())

    return HealthCounts(
        online=await _count(HealthStatus.ONLINE),
        unstable=await _count(HealthStatus.UNSTABLE),
        offline=await _count(HealthStatus.OFFLINE),
        unknown=await _count(HealthStatus.UNKNOWN),
    )
