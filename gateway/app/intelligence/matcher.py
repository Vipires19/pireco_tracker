"""Similarity + Confidence engines — comparação com protocolos conhecidos."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any

from app.intelligence.cluster import SessionCluster
from app.intelligence.fingerprint import SessionFingerprint


@dataclass(frozen=True)
class ProtocolProfile:
    name: str
    headers: tuple[str, ...]
    trailers: tuple[str, ...] = ("0d0a",)
    expects_login: bool = True
    expects_heartbeat: bool = True
    expects_gps: bool = True
    crc_compatible: bool = True
    typical_size_min: int = 10
    typical_size_max: int = 128


KNOWN_PROFILES: tuple[ProtocolProfile, ...] = (
    ProtocolProfile(
        name="GT06 Classic",
        headers=("7878",),
        typical_size_min=10,
        typical_size_max=64,
    ),
    ProtocolProfile(
        name="GT06 V2",
        headers=("7979",),
        typical_size_min=12,
        typical_size_max=256,
    ),
)


@dataclass
class ConfidenceSuggestion:
    candidate: str
    confidence: int
    reason: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class SimilarityResult:
    known_protocol: str
    similarity_percent: int
    details: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class SimilarityEngine:
    """Compara fingerprint/cluster com perfis conhecidos (sem inventar protocolos)."""

    def __init__(self, profiles: tuple[ProtocolProfile, ...] | None = None) -> None:
        self._profiles = profiles or KNOWN_PROFILES

    def compare_fingerprint(self, fp: SessionFingerprint) -> list[SimilarityResult]:
        return [self._score(fp, profile) for profile in self._profiles]

    def best_match(self, fp: SessionFingerprint) -> SimilarityResult | None:
        scores = self.compare_fingerprint(fp)
        if not scores:
            return None
        return max(scores, key=lambda item: item.similarity_percent)

    def _score(self, fp: SessionFingerprint, profile: ProtocolProfile) -> SimilarityResult:
        points = 0
        total = 0
        details: list[str] = []

        # Header (peso 40)
        total += 40
        if fp.header and fp.header in profile.headers:
            points += 40
            details.append(f"Header {fp.header}")
        elif fp.first_bytes[:4] in profile.headers:
            points += 30
            details.append(f"First bytes compatíveis com {profile.name}")

        # Trailer (peso 10)
        total += 10
        if fp.trailer and fp.trailer in profile.trailers:
            points += 10
            details.append(f"Trailer {fp.trailer}")

        # CRC (peso 20)
        total += 20
        if profile.crc_compatible and fp.crc_ok_ratio >= 0.7:
            points += 20
            details.append("CRC compatível")
        elif fp.crc_ok_ratio >= 0.3:
            points += 8
            details.append("CRC parcialmente compatível")

        # Packet types (peso 20)
        total += 20
        type_points = 0
        if profile.expects_login and fp.login_count > 0:
            type_points += 7
            details.append("Login semelhante")
        if profile.expects_heartbeat and fp.heartbeat_count > 0:
            type_points += 7
            details.append("Heartbeat semelhante")
        if profile.expects_gps and fp.gps_count > 0:
            type_points += 6
            details.append("GPS semelhante")
        points += type_points

        # Size (peso 10)
        total += 10
        if profile.typical_size_min <= fp.avg_packet_size <= profile.typical_size_max:
            points += 10
            details.append("Tamanho de pacote semelhante")
        elif fp.avg_packet_size > 0:
            points += 3

        percent = int(round((points / total) * 100)) if total else 0
        return SimilarityResult(
            known_protocol=profile.name,
            similarity_percent=percent,
            details=details,
        )


class ConfidenceEngine:
    """Sugestões com confiança — apenas candidatos conhecidos."""

    def __init__(self, similarity: SimilarityEngine | None = None) -> None:
        self._similarity = similarity or SimilarityEngine()

    def suggest_for_fingerprint(self, fp: SessionFingerprint) -> ConfidenceSuggestion | None:
        best = self._similarity.best_match(fp)
        if best is None or best.similarity_percent < 40:
            return None
        return ConfidenceSuggestion(
            candidate=best.known_protocol,
            confidence=best.similarity_percent,
            reason=list(best.details),
        )

    def suggest_for_cluster(self, cluster: SessionCluster) -> ConfidenceSuggestion | None:
        if not cluster.fingerprints:
            return None
        # Usa fingerprint mediano / primeiro como representante + reforço por tamanho do cluster
        suggestion = self.suggest_for_fingerprint(cluster.fingerprints[0])
        if suggestion is None:
            return None
        boost = min(5, cluster.size // 10)
        confidence = min(99, suggestion.confidence + boost)
        reasons = list(suggestion.reason)
        if cluster.size > 1:
            reasons.append(f"{cluster.size} sessões no cluster")
        return ConfidenceSuggestion(
            candidate=suggestion.candidate,
            confidence=confidence,
            reason=reasons,
        )

    def annotate_clusters(self, clusters: list[SessionCluster]) -> list[SessionCluster]:
        for cluster in clusters:
            suggestion = self.suggest_for_cluster(cluster)
            if suggestion is None:
                continue
            cluster.candidate = suggestion.candidate
            cluster.confidence = suggestion.confidence
            cluster.reasons = list(suggestion.reason)
        return clusters
