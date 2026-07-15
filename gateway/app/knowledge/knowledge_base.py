"""Device Knowledge Base — base de conhecimento versionada sobre dispositivos."""

from __future__ import annotations

import json
import threading
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from app.core.observability import get_logger
from app.knowledge.apn_profiles import ApnCatalog, ApnProfile
from app.knowledge.device_profile import DEFAULT_DEVICE_PROFILES, DeviceProfile
from app.knowledge.manufacturer import Manufacturer, ManufacturerRegistry
from app.knowledge.protocol_history import ProtocolHistory
from app.knowledge.sms_commands import SmsCommand, SmsKnowledge
from app.knowledge.tac import TacDatabase, TacLookupResult, extract_tac
from app.knowledge.variants import ProtocolVariant, VariantDatabase

logger = get_logger(__name__)


@dataclass
class KnowledgeVersion:
    version: str
    date: str
    origin: str
    notes: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class KnowledgeResolution:
    imei: str
    tac: str
    manufacturers: list[str]
    families: list[str]
    models: list[str]
    profiles: list[DeviceProfile]
    recommended_protocols: list[str]
    recommended_parser: str | None
    confidence: int
    reasons: list[str] = field(default_factory=list)
    ambiguous: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "imei": self.imei,
            "tac": self.tac,
            "manufacturers": self.manufacturers,
            "families": self.families,
            "models": self.models,
            "profiles": [p.to_dict() for p in self.profiles],
            "recommended_protocols": self.recommended_protocols,
            "recommended_parser": self.recommended_parser,
            "confidence": self.confidence,
            "reasons": list(self.reasons),
            "ambiguous": self.ambiguous,
        }


class DeviceKnowledgeBase:
    """
    Camada auxiliar de conhecimento.

    Não participa do hot path TCP — Gateway/Worker/Redis/Backend permanecem intactos.
    """

    def __init__(
        self,
        *,
        data_dir: str | Path | None = None,
        version: str = "1.0.0",
        origin: str = "seed",
    ) -> None:
        if data_dir is None:
            data_dir = Path(__file__).resolve().parents[2] / "data" / "knowledge"
        self.data_dir = Path(data_dir)
        self.manufacturers = ManufacturerRegistry()
        self.tac = TacDatabase()
        self.sms = SmsKnowledge()
        self.apn = ApnCatalog()
        self.variants = VariantDatabase()
        self.history = ProtocolHistory()
        self._profiles: dict[str, DeviceProfile] = {
            p.id: p for p in DEFAULT_DEVICE_PROFILES
        }
        self._versions: list[KnowledgeVersion] = []
        self._lock = threading.Lock()
        self._bump_version(version=version, origin=origin, notes="Inicialização da DKB")

    # --- Versionamento ---

    @property
    def current_version(self) -> KnowledgeVersion:
        return self._versions[-1]

    def versions(self) -> list[KnowledgeVersion]:
        return list(self._versions)

    def _bump_version(self, *, version: str | None = None, origin: str, notes: str | None) -> KnowledgeVersion:
        if version is None:
            major, minor, patch = self.current_version.version.split(".")
            version = f"{major}.{minor}.{int(patch) + 1}"
        entry = KnowledgeVersion(
            version=version,
            date=datetime.now(UTC).isoformat(),
            origin=origin,
            notes=notes,
        )
        self._versions.append(entry)
        return entry

    # --- Profiles ---

    def upsert_profile(self, profile: DeviceProfile, *, origin: str = "manual") -> DeviceProfile:
        with self._lock:
            self._profiles[profile.id] = profile
            self._bump_version(origin=origin, notes=f"Upsert profile {profile.id}")
            return profile

    def get_profile(self, profile_id: str) -> DeviceProfile | None:
        return self._profiles.get(profile_id)

    def list_profiles(self) -> list[DeviceProfile]:
        return list(self._profiles.values())

    def profiles_by_tac(self, tac: str) -> list[DeviceProfile]:
        return [p for p in self._profiles.values() if tac in p.tac_codes]

    def profiles_by_family(self, family: str) -> list[DeviceProfile]:
        needle = family.lower()
        return [p for p in self._profiles.values() if p.family.lower() == needle]

    # --- Learning ---

    def learn_protocol_observation(
        self,
        *,
        imei: str | None = None,
        device_key: str | None = None,
        protocol: str,
        success: bool,
        firmware: str | None = None,
        parser: str | None = None,
        source: str = "runtime",
        notes: str | None = None,
    ) -> None:
        """Atualiza histórico sem apagar registros anteriores."""
        key = device_key or (f"imei:{imei}" if imei else None)
        if key is None:
            raise ValueError("imei ou device_key é obrigatório")
        with self._lock:
            self.history.record(
                key,
                protocol=protocol,
                success=success,
                firmware=firmware,
                parser=parser,
                source=source,
                notes=notes,
            )
            self._bump_version(
                origin=source,
                notes=f"Observação protocol={protocol} success={success} device={key}",
            )

    # --- Resolver ---

    def resolve(self, imei: str, *, header_hint: str | None = None) -> KnowledgeResolution:
        """
        IMEI → TAC → DKB → família provável → parser recomendado.

        Camada auxiliar: não altera o fluxo do Gateway.
        """
        tac_result = self.tac.lookup_imei(imei)
        profiles = self.profiles_by_tac(tac_result.tac)

        # Enriquece famílias/modelos com profiles se TAC for genérico
        families = list(tac_result.families)
        models = list(tac_result.models)
        manufacturers = list(tac_result.manufacturers)
        for profile in profiles:
            if profile.family not in families:
                families.append(profile.family)
            if profile.model not in models:
                models.append(profile.model)
            if profile.manufacturer not in manufacturers:
                manufacturers.append(profile.manufacturer)

        recommended_protocols: list[str] = []
        for profile in profiles:
            for proto in profile.possible_protocols:
                if proto not in recommended_protocols:
                    recommended_protocols.append(proto)

        # Preferência por histórico dominante
        device_key = f"imei:{''.join(ch for ch in imei if ch.isdigit())}"
        dominant = self.history.dominant_protocol(device_key)
        reasons: list[str] = list(tac_result.notes)

        if header_hint:
            variants = self.variants.by_header(header_hint)
            for variant in variants:
                if variant.parent_protocol not in recommended_protocols:
                    recommended_protocols.insert(0, variant.name)
                reasons.append(f"Header hint {header_hint} → variant {variant.name}")

        recommended_parser = None
        confidence = 40 if profiles or manufacturers else 0

        if dominant and dominant[1] >= 50:
            recommended_parser = dominant[0]
            confidence = max(confidence, int(dominant[1]))
            reasons.append(f"Histórico dominante {dominant[0]} ({dominant[1]}%)")
        elif recommended_protocols:
            # Mapeia variante → parser name
            recommended_parser = self._protocol_to_parser(recommended_protocols[0])
            confidence = max(confidence, 70 if not tac_result.ambiguous else 55)
            reasons.append(f"Protocolo candidato da família: {recommended_protocols[0]}")

        if header_hint == "7878":
            recommended_parser = "gt06"
            confidence = max(confidence, 85)
            reasons.append("Header 7878 → GT06 Classic")
        elif header_hint == "7979":
            recommended_parser = "gt06_v2"
            confidence = max(confidence, 85)
            reasons.append("Header 7979 → GT06 V2")

        return KnowledgeResolution(
            imei=imei,
            tac=tac_result.tac,
            manufacturers=manufacturers,
            families=families,
            models=models,
            profiles=profiles,
            recommended_protocols=recommended_protocols,
            recommended_parser=recommended_parser,
            confidence=min(99, confidence),
            reasons=reasons,
            ambiguous=tac_result.ambiguous or len(profiles) > 1,
        )

    @staticmethod
    def _protocol_to_parser(protocol_or_variant: str) -> str:
        mapping = {
            "gt06": "gt06",
            "gt06_classic": "gt06",
            "gt06_v2": "gt06_v2",
        }
        return mapping.get(protocol_or_variant, protocol_or_variant)

    # --- Persistência opcional (sincronização futura) ---

    def export_snapshot(self) -> dict[str, Any]:
        return {
            "version": self.current_version.to_dict(),
            "versions": [v.to_dict() for v in self._versions],
            "profiles": [p.to_dict() for p in self._profiles.values()],
            "manufacturers": [m.to_dict() for m in self.manufacturers.list()],
            "tac": [t.to_dict() for t in self.tac.list()],
            "sms": [c.to_dict() for c in self.sms.list()],
            "apn": [a.to_dict() for a in self.apn.list()],
            "variants": [v.to_dict() for v in self.variants.list()],
        }

    def save_snapshot(self, path: str | Path | None = None) -> Path:
        self.data_dir.mkdir(parents=True, exist_ok=True)
        target = Path(path) if path else self.data_dir / f"dkb-{self.current_version.version}.json"
        target.write_text(
            json.dumps(self.export_snapshot(), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        logger.info("DKB snapshot saved path=%s version=%s", target, self.current_version.version)
        return target


_dkb: DeviceKnowledgeBase | None = None


def get_knowledge_base() -> DeviceKnowledgeBase:
    global _dkb
    if _dkb is None:
        _dkb = DeviceKnowledgeBase()
    return _dkb
