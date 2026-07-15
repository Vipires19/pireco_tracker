"""Session Fingerprint — representação compacta para clusterização e matching."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any

from app.intelligence.signature import SignatureAnalyzer, SignatureProfile


@dataclass(frozen=True)
class SessionFingerprint:
    session_id: str
    first_bytes: str
    header: str | None
    trailer: str | None
    avg_packet_size: float
    size_bucket: int
    avg_interval_ms: float | None
    interval_bucket: int | None
    login_count: int
    heartbeat_count: int
    gps_count: int
    crc_ok_ratio: float
    size_sequence: tuple[int, ...] = ()
    headers: tuple[str, ...] = ()
    trailers: tuple[str, ...] = ()
    features: dict[str, Any] = field(default_factory=dict)

    @property
    def signature_key(self) -> str:
        return self.header or self.first_bytes[:4] or "none"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class FingerprintBuilder:
    """Constrói fingerprints a partir de SignatureProfile ou sessão crua."""

    def __init__(self, analyzer: SignatureAnalyzer | None = None) -> None:
        self._analyzer = analyzer or SignatureAnalyzer()

    def from_profile(self, profile: SignatureProfile) -> SessionFingerprint:
        total_crc = profile.crc_ok_count + profile.crc_fail_count
        crc_ratio = (profile.crc_ok_count / total_crc) if total_crc else 0.0
        size_bucket = int(profile.avg_packet_size // 16) * 16
        interval_bucket = None
        if profile.avg_interval_ms is not None:
            interval_bucket = int(profile.avg_interval_ms // 500) * 500

        return SessionFingerprint(
            session_id=profile.session_id,
            first_bytes=profile.first_bytes,
            header=profile.header,
            trailer=profile.trailer,
            avg_packet_size=profile.avg_packet_size,
            size_bucket=size_bucket,
            avg_interval_ms=profile.avg_interval_ms,
            interval_bucket=interval_bucket,
            login_count=profile.login_count,
            heartbeat_count=profile.heartbeat_count,
            gps_count=profile.gps_count,
            crc_ok_ratio=round(crc_ratio, 3),
            size_sequence=profile.size_sequence,
            headers=tuple(profile.headers_found),
            trailers=tuple(profile.trailers_found),
            features={
                "packet_count": profile.packet_count,
                "total_bytes": profile.total_bytes,
                "close_reason": profile.close_reason,
                "duration_ms": profile.duration_ms,
                "protocol_byte_histogram": profile.protocol_byte_histogram,
            },
        )

    def from_session(self, session: dict[str, Any]) -> SessionFingerprint:
        return self.from_profile(self._analyzer.analyze(session))
