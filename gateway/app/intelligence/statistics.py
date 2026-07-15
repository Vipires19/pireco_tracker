"""Statistics — métricas agregadas de sessões e clusters."""

from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import asdict, dataclass, field
from typing import Any

from app.intelligence.cluster import SessionCluster
from app.intelligence.signature import SignatureProfile


@dataclass
class ProtocolStats:
    protocol: str
    sessions: int = 0
    connections: int = 0
    failures: int = 0
    parser_errors: int = 0
    timeouts: int = 0
    bytes_total: int = 0
    avg_duration_ms: float = 0.0
    avg_heartbeat_count: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class UnknownStats:
    sessions: int = 0
    clusters: int = 0
    top_signatures: list[dict[str, Any]] = field(default_factory=list)
    top_candidates: list[dict[str, Any]] = field(default_factory=list)
    close_reasons: dict[str, int] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class IntelligenceStatistics:
    by_protocol: list[ProtocolStats] = field(default_factory=list)
    unknown: UnknownStats = field(default_factory=UnknownStats)
    sessions_analyzed: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "sessions_analyzed": self.sessions_analyzed,
            "by_protocol": [item.to_dict() for item in self.by_protocol],
            "unknown": self.unknown.to_dict(),
        }


class StatisticsEngine:
    """Agrega estatísticas por protocolo e para o universo Unknown."""

    def build(
        self,
        *,
        sessions: list[dict[str, Any]],
        profiles: list[SignatureProfile],
        clusters: list[SessionCluster],
    ) -> IntelligenceStatistics:
        by_proto: dict[str, dict[str, Any]] = defaultdict(
            lambda: {
                "sessions": 0,
                "connections": 0,
                "failures": 0,
                "parser_errors": 0,
                "timeouts": 0,
                "bytes": 0,
                "durations": [],
                "heartbeats": [],
            }
        )

        profile_by_id = {p.session_id: p for p in profiles}
        signature_counter: Counter[str] = Counter()
        candidate_counter: Counter[str] = Counter()
        close_reasons: Counter[str] = Counter()

        for session in sessions:
            protocol = str(session.get("protocol_detected") or "unknown")
            bucket = by_proto[protocol]
            bucket["sessions"] += 1
            bucket["connections"] += 1

            close_reason = session.get("close_reason")
            if close_reason:
                close_reasons[str(close_reason)] += 1
                if close_reason in {"exception", "socket_error"}:
                    bucket["failures"] += 1
                if close_reason == "parser_error":
                    bucket["parser_errors"] += 1
                if close_reason == "timeout":
                    bucket["timeouts"] += 1

            profile = profile_by_id.get(str(session.get("session_id")))
            if profile:
                bucket["bytes"] += profile.total_bytes
                if profile.duration_ms is not None:
                    bucket["durations"].append(profile.duration_ms)
                bucket["heartbeats"].append(profile.heartbeat_count)
                if protocol == "unknown" and profile.header:
                    signature_counter[profile.header] += 1

        for cluster in clusters:
            if cluster.candidate:
                candidate_counter[cluster.candidate] += cluster.size

        protocol_stats: list[ProtocolStats] = []
        for name, data in sorted(by_proto.items()):
            durations = data["durations"]
            heartbeats = data["heartbeats"]
            protocol_stats.append(
                ProtocolStats(
                    protocol=name,
                    sessions=data["sessions"],
                    connections=data["connections"],
                    failures=data["failures"],
                    parser_errors=data["parser_errors"],
                    timeouts=data["timeouts"],
                    bytes_total=data["bytes"],
                    avg_duration_ms=round(sum(durations) / len(durations), 3) if durations else 0.0,
                    avg_heartbeat_count=round(sum(heartbeats) / len(heartbeats), 3) if heartbeats else 0.0,
                )
            )

        unknown_sessions = by_proto.get("unknown", {}).get("sessions", 0)
        top_signatures = [
            {"signature": sig, "count": count} for sig, count in signature_counter.most_common(10)
        ]
        top_candidates = [
            {"candidate": name, "sessions": count}
            for name, count in candidate_counter.most_common(10)
        ]

        return IntelligenceStatistics(
            by_protocol=protocol_stats,
            unknown=UnknownStats(
                sessions=unknown_sessions,
                clusters=len(clusters),
                top_signatures=top_signatures,
                top_candidates=top_candidates,
                close_reasons=dict(close_reasons),
            ),
            sessions_analyzed=len(sessions),
        )
