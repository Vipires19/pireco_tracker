"""Testes do Protocol Replay Lab."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from app.protocol.encoder import build_ack, build_login_packet
from app.protocol.parser import parse_packet
from tools.replay.loader import SessionLoadError, SessionLoader
from tools.replay.report import diff_bytes
from tools.replay.runner import ReplayRunner


IMEI = "867686031234567"


def _gt06_login_session() -> dict:
    login = build_login_packet(IMEI, serial_number=1)
    packet = parse_packet(login)
    assert packet is not None
    ack = build_ack(packet.protocol_number, packet.serial_number)
    return {
        "session_id": "replay-gt06-1",
        "protocol_detected": "gt06",
        "remote_ip": "127.0.0.1",
        "remote_port": 5555,
        "events": [
            {"event": "CONNECT", "elapsed_ms": 0},
            {"event": "RX", "bytes": len(login), "hex": login.hex(), "ascii": "." * len(login)},
            {"event": "TX", "bytes": len(ack), "hex": ack.hex(), "ascii": "." * len(ack)},
            {"event": "CLOSE", "close_reason": "client_closed"},
        ],
    }


def _unknown_session() -> dict:
    payload = b"\x7e\xaa\x01\x02\x03\x04"
    return {
        "session_id": "replay-unknown-1",
        "protocol_detected": "unknown",
        "remote_ip": "10.0.0.9",
        "remote_port": 4000,
        "events": [
            {"event": "CONNECT", "elapsed_ms": 0},
            {
                "event": "RX",
                "bytes": len(payload),
                "hex": payload.hex(),
                "ascii": "......",
            },
            {"event": "CLOSE", "close_reason": "client_closed"},
        ],
    }


def test_replay_gt06_session_matches_production_ack() -> None:
    session = SessionLoader().load(_gt06_login_session())
    report = ReplayRunner().replay(session)

    assert report.parser == "gt06"
    assert report.packets_total == 1
    assert report.packets_valid == 1
    assert report.packets_invalid == 0
    assert report.result == "MATCH"
    assert report.difference_count == 0


def test_replay_unknown_session_learning_mode() -> None:
    session = SessionLoader().load(_unknown_session())
    report = ReplayRunner().replay(session)

    assert report.parser == "unknown"
    assert report.packets_total == 1
    assert report.packets_valid == 0
    assert report.result == "MATCH"
    assert any("Nenhum TX" in note for note in report.notes)


def test_replay_invalid_session_raises() -> None:
    loader = SessionLoader()
    with pytest.raises(SessionLoadError, match="session_id"):
        loader.load({"events": []})

    with pytest.raises(SessionLoadError, match="events"):
        loader.load({"session_id": "x"})


def test_replay_empty_session() -> None:
    session = SessionLoader().load(
        {
            "session_id": "empty-1",
            "protocol_detected": "unknown",
            "events": [],
        }
    )
    report = ReplayRunner().replay(session)
    assert report.packets_total == 0
    assert report.result == "MATCH"


def test_packet_injection_gt06() -> None:
    login = build_login_packet(IMEI, serial_number=1)
    packet = parse_packet(login)
    assert packet is not None
    expected_ack = build_ack(packet.protocol_number, packet.serial_number)

    result = ReplayRunner().inject(protocol="GT06", hex=login.hex())
    assert result.valid is True
    assert result.frames == 1
    assert result.acks == [expected_ack.hex()]
    assert result.packet_types == ["0x01"]


def test_diff_engine_reports_byte_positions() -> None:
    diffs = diff_bytes(b"\x01\x02\x03", b"\x01\xff\x03\x04")
    assert len(diffs) == 2
    assert diffs[0].position == 1
    assert diffs[0].expected == "02"
    assert diffs[0].obtained == "ff"
    assert diffs[1].position == 3
    assert diffs[1].expected == "<missing>"
    assert diffs[1].obtained == "04"


def test_loader_jsonl_and_latest(tmp_path: Path) -> None:
    day = tmp_path / "2026-07-14.jsonl"
    sessions = [_unknown_session(), _gt06_login_session()]
    day.write_text(
        "\n".join(json.dumps(item) for item in sessions) + "\n",
        encoding="utf-8",
    )

    loader = SessionLoader(data_dir=tmp_path)
    loaded = loader.load_jsonl(day)
    assert len(loaded) == 2
    assert loaded[0].session_id == "replay-unknown-1"

    latest = loader.load_latest()
    assert latest.session_id == "replay-gt06-1"


def test_protocol_override_forces_gt06_parser() -> None:
    # Sessão gravada como unknown, mas bytes são GT06 → override deve parsear.
    login = build_login_packet(IMEI, serial_number=1)
    packet = parse_packet(login)
    assert packet is not None
    ack = build_ack(packet.protocol_number, packet.serial_number)

    payload = {
        "session_id": "override-1",
        "protocol_detected": "unknown",
        "events": [
            {"event": "CONNECT"},
            {"event": "RX", "hex": login.hex()},
            {"event": "TX", "hex": ack.hex()},
            {"event": "CLOSE", "close_reason": "client_closed"},
        ],
    }
    session = SessionLoader().load(payload)
    report = ReplayRunner().replay(session, protocol="GT06")
    assert report.parser == "gt06"
    assert report.result == "MATCH"
