"""Health operacional do rastreador a partir de last_seen (sem cron)."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from app.domains.devices.models import HealthStatus

ONLINE_WINDOW = timedelta(minutes=2)


def resolve_health_status(last_seen_at: datetime | None) -> HealthStatus:
    """ONLINE se last_seen <= 2 min; OFFLINE se > 2 min; UNKNOWN se nunca comunicou."""
    if last_seen_at is None:
        return HealthStatus.UNKNOWN
    ts = last_seen_at if last_seen_at.tzinfo is not None else last_seen_at.replace(tzinfo=UTC)
    if datetime.now(UTC) - ts <= ONLINE_WINDOW:
        return HealthStatus.ONLINE
    return HealthStatus.OFFLINE


def online_since() -> datetime:
    return datetime.now(UTC) - ONLINE_WINDOW
