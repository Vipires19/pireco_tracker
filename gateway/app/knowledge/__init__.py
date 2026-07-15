"""Device Knowledge Base (DKB) — conhecimento sobre famílias de rastreadores."""

from app.knowledge.apn_profiles import ApnCatalog, ApnProfile
from app.knowledge.device_profile import DeviceProfile
from app.knowledge.knowledge_base import (
    DeviceKnowledgeBase,
    KnowledgeResolution,
    KnowledgeVersion,
    get_knowledge_base,
)
from app.knowledge.manufacturer import Manufacturer, ManufacturerRegistry
from app.knowledge.protocol_history import ProtocolHistory, ProtocolObservation, ProtocolStats
from app.knowledge.sms_commands import SmsCommand, SmsKnowledge
from app.knowledge.tac import TacDatabase, TacLookupResult, TacRecord, extract_tac
from app.knowledge.variants import ProtocolVariant, VariantDatabase

__all__ = [
    "ApnCatalog",
    "ApnProfile",
    "DeviceKnowledgeBase",
    "DeviceProfile",
    "KnowledgeResolution",
    "KnowledgeVersion",
    "Manufacturer",
    "ManufacturerRegistry",
    "ProtocolHistory",
    "ProtocolObservation",
    "ProtocolStats",
    "ProtocolVariant",
    "SmsCommand",
    "SmsKnowledge",
    "TacDatabase",
    "TacLookupResult",
    "TacRecord",
    "VariantDatabase",
    "extract_tac",
    "get_knowledge_base",
]
