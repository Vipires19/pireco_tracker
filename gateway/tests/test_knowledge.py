"""Testes da Device Knowledge Base (DKB)."""

from __future__ import annotations

from pathlib import Path

import pytest

from app.knowledge import (
    ApnCatalog,
    DeviceKnowledgeBase,
    DeviceProfile,
    SmsKnowledge,
    TacDatabase,
    VariantDatabase,
    extract_tac,
)
from app.knowledge.apn_profiles import ApnProfile
from app.knowledge.sms_commands import SmsCommand
from app.knowledge.tac import TacRecord
from app.knowledge.variants import ProtocolVariant


def test_tac_lookup_known_and_ambiguous() -> None:
    db = TacDatabase()
    result = db.lookup_imei("866557081234567")
    assert result.tac == "86655708"
    assert "concox" in result.manufacturers
    assert "GT06" in result.families
    assert result.ambiguous is True  # múltiplos models

    multi = db.lookup_imei("867686031234567")
    assert multi.tac == "86768603"
    assert len(multi.manufacturers) >= 2
    assert multi.ambiguous is True


def test_tac_extract_and_unknown() -> None:
    assert extract_tac("86-7655-7012-34567") == "86765570"
    with pytest.raises(ValueError):
        extract_tac("123")

    result = TacDatabase().lookup_imei("999999991234567")
    assert result.manufacturers == []
    assert "não encontrado" in result.notes[0].lower()


def test_device_profile_upsert_and_list() -> None:
    dkb = DeviceKnowledgeBase(data_dir=Path("."), version="1.0.0")
    profile = DeviceProfile(
        id="test_family",
        manufacturer="concox",
        family="TEST",
        model="T1",
        possible_protocols=["gt06"],
        supported_sms=["STATUS"],
        heartbeat_interval=60,
        gps_interval=10,
        apn_profiles=["vivo_zap"],
        notes="perfil de teste",
        tac_codes=["11112222"],
    )
    dkb.upsert_profile(profile, origin="test")
    assert dkb.get_profile("test_family") is not None
    assert dkb.profiles_by_family("TEST")[0].model == "T1"
    assert dkb.current_version.origin == "test"


def test_protocol_history_never_deletes_and_dominance() -> None:
    dkb = DeviceKnowledgeBase(data_dir=Path("."))
    imei = "867686031234567"
    for _ in range(95):
        dkb.learn_protocol_observation(imei=imei, protocol="gt06_v2", success=True, parser="gt06_v2")
    for _ in range(5):
        dkb.learn_protocol_observation(imei=imei, protocol="gt06", success=True, parser="gt06")

    key = f"imei:{imei}"
    history = dkb.history.history_for(key)
    assert len(history) == 100

    stats = dkb.history.stats_for(key)
    assert stats[0].protocol == "gt06_v2"
    assert stats[0].share_of(100) == 95.0

    dominant = dkb.history.dominant_protocol(key)
    assert dominant == ("gt06_v2", 95.0)


def test_sms_knowledge_by_family() -> None:
    sms = SmsKnowledge()
    commands = sms.find(command="SERVER", family="J16 Ultra")
    assert len(commands) == 1
    assert commands[0].example == "SERVER,0,IP,PORT,0#"
    assert "J16 Pro" in commands[0].families

    sms.register(
        SmsCommand(
            command="CUSTOM",
            description="x",
            families=["J16 Ultra"],
            manufacturer="jimi",
        )
    )
    assert sms.find(command="CUSTOM")


def test_apn_profiles_by_operator() -> None:
    catalog = ApnCatalog()
    vivo = catalog.by_operator("Vivo")
    assert len(vivo) == 1
    assert vivo[0].apn == "zap.vivo.com.br"
    assert catalog.by_manufacturer("concox")
    catalog.register(
        ApnProfile(id="oi_gprs", operator="Oi", apn="gprs.oi.com.br", manufacturers=["concox"])
    )
    assert catalog.get("oi_gprs") is not None


def test_variant_database() -> None:
    db = VariantDatabase()
    classic = db.by_header("7878")
    v2 = db.by_header("7979")
    assert classic and classic[0].parent_protocol == "gt06"
    assert v2 and v2[0].name == "gt06_v2"
    assert db.by_parent("gt06")
    db.register(
        ProtocolVariant(
            name="gt06_custom",
            parent_protocol="gt06",
            known_headers=["7a7a"],
            known_crc=["crc16_x25"],
        )
    )
    assert db.get("gt06_custom") is not None


def test_knowledge_resolver_flow() -> None:
    dkb = DeviceKnowledgeBase(data_dir=Path("."))
    resolution = dkb.resolve("866557081234567", header_hint="7979")
    assert resolution.tac == "86655708"
    assert "GT06" in resolution.families
    assert resolution.recommended_parser == "gt06_v2"
    assert resolution.confidence >= 85
    assert any("7979" in r for r in resolution.reasons)

    classic = dkb.resolve("867686031234567", header_hint="7878")
    assert classic.recommended_parser == "gt06"


def test_knowledge_versioning_and_snapshot(tmp_path: Path) -> None:
    dkb = DeviceKnowledgeBase(data_dir=tmp_path, version="1.0.0", origin="seed")
    v0 = dkb.current_version.version
    dkb.learn_protocol_observation(imei="867686031234567", protocol="gt06", success=True)
    assert dkb.current_version.version != v0
    assert len(dkb.versions()) >= 2

    path = dkb.save_snapshot()
    assert path.exists()
    payload = path.read_text(encoding="utf-8")
    assert "profiles" in payload
    assert "version" in payload
