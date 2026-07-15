"""Protocol Intelligence Engine — análise offline de sessões Learning Mode."""

from __future__ import annotations

import asyncio
import json
import re
import threading
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from app.core.observability import get_logger
from app.intelligence.cluster import SessionCluster, SessionClusterer
from app.intelligence.fingerprint import FingerprintBuilder, SessionFingerprint
from app.intelligence.matcher import ConfidenceEngine, ConfidenceSuggestion, SimilarityEngine
from app.intelligence.report import IntelligenceReport, ReportBuilder
from app.intelligence.signature import SignatureAnalyzer, SignatureProfile
from app.intelligence.statistics import IntelligenceStatistics, StatisticsEngine

logger = get_logger(__name__)


@dataclass
class PromotionProposal:
    """
    Resultado de uma promoção manual.

    NÃO registra parser automaticamente — apenas gera artefato para o
    desenvolvedor implementar e registrar no Registry.
    """

    proposal_id: str
    cluster_id: str
    suggested_protocol_name: str
    signatures: list[str]
    confidence: int
    reasons: list[str] = field(default_factory=list)
    session_ids: list[str] = field(default_factory=list)
    status: str = "pending_implementation"
    created_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())
    notes: str = (
        "Promoção manual: implementar parser e registrar no ProtocolRegistry. "
        "Nenhuma promoção automática é aplicada em runtime."
    )

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class ProtocolIntelligenceEngine:
    """
    Orquestra Signature → Fingerprint → Cluster → Confidence → Report.

    Todo processamento é offline (fora do hot path TCP). Use `analyze_async`.
    """

    def __init__(
        self,
        *,
        sessions_dir: str | Path | None = None,
        promotions_dir: str | Path | None = None,
    ) -> None:
        if sessions_dir is None:
            sessions_dir = Path(__file__).resolve().parents[2] / "data" / "sessions"
        if promotions_dir is None:
            promotions_dir = Path(__file__).resolve().parents[2] / "data" / "promotions"

        self.sessions_dir = Path(sessions_dir)
        self.promotions_dir = Path(promotions_dir)
        self._analyzer = SignatureAnalyzer()
        self._fingerprints = FingerprintBuilder(self._analyzer)
        self._clusterer = SessionClusterer()
        self._similarity = SimilarityEngine()
        self._confidence = ConfidenceEngine(self._similarity)
        self._statistics = StatisticsEngine()
        self._reports = ReportBuilder()
        self._lock = threading.Lock()
        self._last_report: IntelligenceReport | None = None
        self._last_clusters: list[SessionCluster] = []

    def load_sessions(self, *, unknown_only: bool = True) -> list[dict[str, Any]]:
        if not self.sessions_dir.exists():
            return []
        sessions: list[dict[str, Any]] = []
        for path in sorted(self.sessions_dir.glob("*.jsonl")):
            for line in path.read_text(encoding="utf-8").splitlines():
                text = line.strip()
                if not text:
                    continue
                try:
                    payload = json.loads(text)
                except json.JSONDecodeError:
                    continue
                if not isinstance(payload, dict):
                    continue
                if unknown_only and str(payload.get("protocol_detected") or "unknown") != "unknown":
                    continue
                sessions.append(payload)
        return sessions

    def analyze_sessions(self, sessions: list[dict[str, Any]] | None = None) -> IntelligenceReport:
        with self._lock:
            return self._analyze_locked(sessions)

    async def analyze_async(self, sessions: list[dict[str, Any]] | None = None) -> IntelligenceReport:
        """Executa análise em thread pool — não bloqueia o event loop TCP."""
        return await asyncio.to_thread(self.analyze_sessions, sessions)

    def _analyze_locked(self, sessions: list[dict[str, Any]] | None) -> IntelligenceReport:
        data = sessions if sessions is not None else self.load_sessions(unknown_only=False)
        unknown = [
            s
            for s in data
            if str(s.get("protocol_detected") or "unknown") == "unknown"
        ]

        profiles: list[SignatureProfile] = [self._analyzer.analyze(s) for s in unknown]
        fingerprints: list[SessionFingerprint] = [
            self._fingerprints.from_profile(p) for p in profiles
        ]
        clusters = self._clusterer.cluster(fingerprints)
        clusters = self._confidence.annotate_clusters(clusters)

        suggestions: list[ConfidenceSuggestion] = []
        for cluster in clusters:
            if cluster.candidate:
                suggestions.append(
                    ConfidenceSuggestion(
                        candidate=cluster.candidate,
                        confidence=cluster.confidence,
                        reason=list(cluster.reasons),
                    )
                )

        known_profiles = [
            self._analyzer.analyze(s)
            for s in data
            if str(s.get("protocol_detected") or "unknown") != "unknown"
        ]
        stats = self._statistics.build(
            sessions=data,
            profiles=profiles + known_profiles,
            clusters=clusters,
        )

        report = self._reports.build(
            sessions_analyzed=len(data),
            clusters=clusters,
            suggestions=suggestions,
            statistics=stats,
        )
        self._last_report = report
        self._last_clusters = clusters
        logger.info(
            "Intelligence analysis complete sessions=%s clusters=%s candidates=%s",
            report.sessions_analyzed,
            len(clusters),
            report.new_protocol_candidates,
        )
        return report

    def similarity(self, session: dict[str, Any]) -> list[dict[str, Any]]:
        fp = self._fingerprints.from_session(session)
        return [item.to_dict() for item in self._similarity.compare_fingerprint(fp)]

    def promote_cluster(
        self,
        cluster_id: str,
        *,
        protocol_name: str | None = None,
        approved_by: str = "developer",
    ) -> PromotionProposal:
        """
        Workflow manual de promoção.

        Gera proposta em disco. NÃO altera o Registry em runtime.
        """
        cluster = self._find_cluster(cluster_id)
        if cluster is None:
            raise ValueError(f"Cluster não encontrado: {cluster_id}")

        slug = self._slugify(protocol_name or cluster.candidate or f"cluster_{cluster_id}")
        proposal = PromotionProposal(
            proposal_id=f"promo-{datetime.now(UTC).strftime('%Y%m%d%H%M%S')}-{slug}",
            cluster_id=cluster.cluster_id,
            suggested_protocol_name=slug,
            signatures=[cluster.signature] if cluster.signature else [],
            confidence=cluster.confidence,
            reasons=list(cluster.reasons) + [f"approved_by={approved_by}"],
            session_ids=list(cluster.session_ids),
        )
        self.promotions_dir.mkdir(parents=True, exist_ok=True)
        path = self.promotions_dir / f"{proposal.proposal_id}.json"
        path.write_text(
            json.dumps(proposal.to_dict(), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        logger.info(
            "Promotion proposal written cluster=%s protocol=%s path=%s",
            cluster.cluster_id,
            slug,
            path,
        )
        return proposal

    def list_promotions(self) -> list[dict[str, Any]]:
        if not self.promotions_dir.exists():
            return []
        items: list[dict[str, Any]] = []
        for path in sorted(self.promotions_dir.glob("promo-*.json")):
            try:
                items.append(json.loads(path.read_text(encoding="utf-8")))
            except json.JSONDecodeError:
                continue
        return items

    @property
    def last_report(self) -> IntelligenceReport | None:
        return self._last_report

    def _find_cluster(self, cluster_id: str) -> SessionCluster | None:
        needle = cluster_id.strip().lower()
        for cluster in self._last_clusters:
            if cluster.cluster_id.lower() == needle:
                return cluster
            # Aceita "001" ou "Cluster 001"
            if needle in cluster.cluster_id.lower():
                return cluster
        return None

    @staticmethod
    def _slugify(name: str) -> str:
        cleaned = name.strip().lower().replace(" ", "_")
        cleaned = cleaned.replace("-", "_")
        cleaned = re.sub(r"[^a-z0-9_]+", "", cleaned)
        return cleaned or "new_protocol"


def get_intelligence_engine() -> ProtocolIntelligenceEngine:
    return ProtocolIntelligenceEngine()
