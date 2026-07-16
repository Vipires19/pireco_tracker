from datetime import UTC, datetime, timedelta

from app.domains.devices.health import ONLINE_WINDOW, resolve_health_status
from app.domains.devices.models import HealthStatus


def test_resolve_health_unknown_without_last_seen() -> None:
    assert resolve_health_status(None) == HealthStatus.UNKNOWN


def test_resolve_health_online_within_window() -> None:
    last_seen = datetime.now(UTC) - timedelta(seconds=30)
    assert resolve_health_status(last_seen) == HealthStatus.ONLINE


def test_resolve_health_offline_after_window() -> None:
    last_seen = datetime.now(UTC) - ONLINE_WINDOW - timedelta(seconds=1)
    assert resolve_health_status(last_seen) == HealthStatus.OFFLINE
