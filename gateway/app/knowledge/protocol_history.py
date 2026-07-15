"""Protocol History — histórico acumulativo por dispositivo / família."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from typing import Any


@dataclass
class ProtocolObservation:
    protocol: str
    firmware: str | None
    parser: str | None
    success: bool
    observed_at: str
    source: str = "runtime"
    notes: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class ProtocolStats:
    protocol: str
    successes: int = 0
    failures: int = 0
    firmwares: list[str] = field(default_factory=list)
    parsers: list[str] = field(default_factory=list)

    @property
    def total(self) -> int:
        return self.successes + self.failures

    @property
    def success_rate(self) -> float:
        return round((self.successes / self.total) * 100, 2) if self.total else 0.0

    def share_of(self, grand_total: int) -> float:
        return round((self.total / grand_total) * 100, 2) if grand_total else 0.0

    def to_dict(self, *, grand_total: int | None = None) -> dict[str, Any]:
        payload = asdict(self)
        payload["total"] = self.total
        payload["success_rate"] = self.success_rate
        if grand_total is not None:
            payload["share_percent"] = self.share_of(grand_total)
        return payload


class ProtocolHistory:
    """Nunca apaga histórico — apenas acumula observações."""

    def __init__(self) -> None:
        self._by_device: dict[str, list[ProtocolObservation]] = defaultdict(list)

    def record(
        self,
        device_key: str,
        *,
        protocol: str,
        success: bool,
        firmware: str | None = None,
        parser: str | None = None,
        source: str = "runtime",
        notes: str | None = None,
    ) -> ProtocolObservation:
        observation = ProtocolObservation(
            protocol=protocol,
            firmware=firmware,
            parser=parser,
            success=success,
            observed_at=datetime.now(UTC).isoformat(),
            source=source,
            notes=notes,
        )
        self._by_device[device_key].append(observation)
        return observation

    def history_for(self, device_key: str) -> list[ProtocolObservation]:
        return list(self._by_device.get(device_key, []))

    def stats_for(self, device_key: str) -> list[ProtocolStats]:
        buckets: dict[str, ProtocolStats] = {}
        observations = self._by_device.get(device_key, [])
        for obs in observations:
            stats = buckets.setdefault(obs.protocol, ProtocolStats(protocol=obs.protocol))
            if obs.success:
                stats.successes += 1
            else:
                stats.failures += 1
            if obs.firmware and obs.firmware not in stats.firmwares:
                stats.firmwares.append(obs.firmware)
            if obs.parser and obs.parser not in stats.parsers:
                stats.parsers.append(obs.parser)
        grand_total = len(observations)
        return sorted(
            buckets.values(),
            key=lambda s: (s.share_of(grand_total), s.success_rate, s.total),
            reverse=True,
        )

    def dominant_protocol(self, device_key: str) -> tuple[str, float] | None:
        """Retorna (protocolo, participação %). Ex.: ('gt06_v2', 95.0)."""
        observations = self._by_device.get(device_key, [])
        if not observations:
            return None
        stats = self.stats_for(device_key)
        if not stats:
            return None
        top = stats[0]
        return top.protocol, top.share_of(len(observations))
