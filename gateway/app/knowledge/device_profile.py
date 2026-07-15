"""Device Profile — conhecimento estruturado sobre um rastreador / família."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass
class DeviceProfile:
    id: str
    manufacturer: str
    family: str
    model: str
    firmware: str | None = None
    possible_protocols: list[str] = field(default_factory=list)
    supported_sms: list[str] = field(default_factory=list)
    heartbeat_interval: int | None = None
    gps_interval: int | None = None
    apn_profiles: list[str] = field(default_factory=list)
    notes: str | None = None
    tac_codes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


DEFAULT_DEVICE_PROFILES: list[DeviceProfile] = [
    DeviceProfile(
        id="concox_gt06n",
        manufacturer="concox",
        family="GT06",
        model="GT06N",
        firmware="generic",
        possible_protocols=["gt06", "gt06_v2"],
        supported_sms=["SERVER", "APN", "RESET", "STATUS"],
        heartbeat_interval=180,
        gps_interval=30,
        apn_profiles=["vivo_zap", "claro_gprs", "tim_brasil"],
        notes="Família clássica Concox GT06",
        tac_codes=["86768603", "86655708"],
    ),
    DeviceProfile(
        id="jimi_j16_ultra",
        manufacturer="jimi",
        family="J16",
        model="J16 Ultra",
        firmware="generic",
        possible_protocols=["gt06", "gt06_v2"],
        supported_sms=["SERVER", "APN", "RESET"],
        heartbeat_interval=120,
        gps_interval=20,
        apn_profiles=["vivo_zap", "claro_gprs"],
        notes="Variante J16 com SMS SERVER,0,IP,PORT,0#",
        tac_codes=["86833403"],
    ),
    DeviceProfile(
        id="jimi_j16_pro",
        manufacturer="jimi",
        family="J16",
        model="J16 Pro",
        firmware="generic",
        possible_protocols=["gt06"],
        supported_sms=["SERVER", "APN"],
        heartbeat_interval=180,
        gps_interval=30,
        apn_profiles=["vivo_zap"],
        notes="Variante J16 Pro",
        tac_codes=["86833404"],
    ),
]
