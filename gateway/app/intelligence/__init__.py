"""Protocol Intelligence Engine — análise determinística de sessões unknown."""

from app.intelligence.cluster import SessionCluster, SessionClusterer
from app.intelligence.engine import PromotionProposal, ProtocolIntelligenceEngine, get_intelligence_engine
from app.intelligence.fingerprint import FingerprintBuilder, SessionFingerprint
from app.intelligence.matcher import ConfidenceEngine, ConfidenceSuggestion, SimilarityEngine
from app.intelligence.report import IntelligenceReport, ReportBuilder
from app.intelligence.signature import SignatureAnalyzer, SignatureProfile
from app.intelligence.statistics import IntelligenceStatistics, StatisticsEngine

__all__ = [
    "ConfidenceEngine",
    "ConfidenceSuggestion",
    "FingerprintBuilder",
    "IntelligenceReport",
    "IntelligenceStatistics",
    "PromotionProposal",
    "ProtocolIntelligenceEngine",
    "ReportBuilder",
    "SessionCluster",
    "SessionClusterer",
    "SessionFingerprint",
    "SignatureAnalyzer",
    "SignatureProfile",
    "SimilarityEngine",
    "StatisticsEngine",
    "get_intelligence_engine",
]
