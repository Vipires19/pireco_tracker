from datetime import UTC, datetime, timedelta

from app.domains.devices.health import (
    ONLINE_WINDOW,
    UNSTABLE_WINDOW,
    resolve_health_status,
)
from app.domains.devices.models import HealthStatus


def test_resolve_health_unknown_without_last_seen() -> None:
    assert resolve_health_status(None) == HealthStatus.UNKNOWN


def test_resolve_health_online_within_60s() -> None:
    last_seen = datetime.now(UTC) - timedelta(seconds=30)
    assert resolve_health_status(last_seen) == HealthStatus.ONLINE


def test_resolve_health_online_at_boundary() -> None:
    last_seen = datetime.now(UTC) - ONLINE_WINDOW + timedelta(milliseconds=50)
    assert resolve_health_status(last_seen) == HealthStatus.ONLINE


def test_resolve_health_unstable() -> None:
    last_seen = datetime.now(UTC) - timedelta(seconds=90)
    assert resolve_health_status(last_seen) == HealthStatus.UNSTABLE


def test_resolve_health_unstable_upper_boundary() -> None:
    last_seen = datetime.now(UTC) - UNSTABLE_WINDOW + timedelta(milliseconds=50)
    assert resolve_health_status(last_seen) == HealthStatus.UNSTABLE


def test_resolve_health_offline_after_180s() -> None:
    last_seen = datetime.now(UTC) - UNSTABLE_WINDOW - timedelta(seconds=1)
    assert resolve_health_status(last_seen) == HealthStatus.OFFLINE


def test_resolve_health_naive_datetime_treated_as_utc() -> None:
    last_seen = datetime.now(UTC).replace(tzinfo=None) - timedelta(seconds=10)
    assert resolve_health_status(last_seen) == HealthStatus.ONLINE
