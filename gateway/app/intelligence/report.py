"""Intelligence Report — saída humana e estruturada."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from typing import Any

from app.intelligence.cluster import SessionCluster
from app.intelligence.matcher import ConfidenceSuggestion
from app.intelligence.statistics import IntelligenceStatistics


@dataclass
class IntelligenceReport:
    sessions_analyzed: int
    new_protocol_candidates: int
    largest_cluster_id: str | None
    largest_cluster_candidate: str | None
    largest_cluster_confidence: int
    largest_cluster_size: int
    clusters: list[SessionCluster] = field(default_factory=list)
    suggestions: list[ConfidenceSuggestion] = field(default_factory=list)
    statistics: IntelligenceStatistics | None = None
    generated_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())

    def to_dict(self) -> dict[str, Any]:
        return {
            "generated_at": self.generated_at,
            "sessions_analyzed": self.sessions_analyzed,
            "new_protocol_candidates": self.new_protocol_candidates,
            "largest_cluster": {
                "cluster_id": self.largest_cluster_id,
                "candidate": self.largest_cluster_candidate,
                "confidence": self.largest_cluster_confidence,
                "size": self.largest_cluster_size,
            },
            "clusters": [c.to_dict() for c in self.clusters],
            "suggestions": [s.to_dict() for s in self.suggestions],
            "statistics": self.statistics.to_dict() if self.statistics else None,
        }

    def to_json(self, *, indent: int = 2) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=indent)

    def summary_text(self) -> str:
        lines = [
            "Protocol Intelligence Report",
            "",
            f"Sessões analisadas: {self.sessions_analyzed}",
            f"Novos protocolos (candidatos): {self.new_protocol_candidates}",
            f"Maior cluster: {self.largest_cluster_candidate or self.largest_cluster_id or '-'}",
            f"Confiança: {self.largest_cluster_confidence}%",
            f"Tamanho do maior cluster: {self.largest_cluster_size}",
            "",
            "Clusters:",
        ]
        for cluster in self.clusters[:10]:
            lines.append(
                f"  {cluster.cluster_id}: {cluster.size} sessões | "
                f"assinatura={cluster.signature or '-'} | "
                f"provável={cluster.candidate or '-'} ({cluster.confidence}%)"
            )
        return "\n".join(lines)


class ReportBuilder:
    def build(
        self,
        *,
        sessions_analyzed: int,
        clusters: list[SessionCluster],
        suggestions: list[ConfidenceSuggestion],
        statistics: IntelligenceStatistics | None = None,
    ) -> IntelligenceReport:
        if clusters:
            largest = max(clusters, key=lambda c: c.size)
            largest_id = largest.cluster_id
            largest_candidate = largest.candidate
            largest_confidence = largest.confidence
            largest_size = largest.size
        else:
            largest_id = None
            largest_candidate = None
            largest_confidence = 0
            largest_size = 0

        unique_candidates = {s.candidate for s in suggestions if s.confidence >= 60}
        unique_candidates.update({c.candidate for c in clusters if c.candidate and c.confidence >= 60})

        return IntelligenceReport(
            sessions_analyzed=sessions_analyzed,
            new_protocol_candidates=len(unique_candidates),
            largest_cluster_id=largest_id,
            largest_cluster_candidate=largest_candidate,
            largest_cluster_confidence=largest_confidence,
            largest_cluster_size=largest_size,
            clusters=list(clusters),
            suggestions=list(suggestions),
            statistics=statistics,
        )
