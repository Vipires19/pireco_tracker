"""Testes do Protocol Intelligence Engine."""

from __future__ import annotations

import asyncio
from pathlib import Path

import pytest

from app.intelligence.cluster import SessionClusterer
from app.intelligence.engine import ProtocolIntelligenceEngine
from app.intelligence.fingerprint import FingerprintBuilder
from app.intelligence.matcher import ConfidenceEngine, SimilarityEngine
from app.intelligence.signature import SignatureAnalyzer
from app.protocols.gt06.codec import Gt06Codec
from app.protocols.gt06.packets import START_BYTES_LONG, START_BYTES_SHORT


IMEI = "867686031234567"


def _session(
    session_id: str,
    *,
    header: bytes,
    frames: list[bytes],
    protocol_detected: str = "unknown",
    close_reason: str = "client_closed",
) -> dict:
    events = [{"event": "CONNECT", "elapsed_ms": 0}]
    elapsed = 10.0
    for frame in frames:
        events.append(
            {
                "event": "RX",
                "bytes": len(frame),
                "hex": frame.hex(),
                "elapsed_ms": elapsed,
            }
        )
        elapsed += 1000.0
    events.append({"event": "CLOSE", "close_reason": close_reason})
    return {
        "session_id": session_id,
        "protocol_detected": protocol_detected,
        "close_reason": close_reason,
        "duration_ms": elapsed,
        "remote_ip": "10.0.0.1",
        "remote_port": 1000,
        "events": events,
        "header_hint": header.hex(),
    }


@pytest.fixture
def classic_frames() -> list[bytes]:
    codec = Gt06Codec(protocol_name="gt06", start_marker=START_BYTES_SHORT)
    return [
        codec.encode_login(IMEI, 1),
        codec.encode_heartbeat(2),
        codec.encode_gps(-23.5, -46.6, serial_number=3),
    ]


@pytest.fixture
def v2_frames() -> list[bytes]:
    codec = Gt06Codec(protocol_name="gt06_v2", start_marker=START_BYTES_LONG)
    return [
        codec.encode_login(IMEI, 1),
        codec.encode_heartbeat(2),
        codec.encode_gps(-23.5, -46.6, serial_number=3),
    ]


def test_signature_analyzer_detects_packet_types(classic_frames: list[bytes]) -> None:
    session = _session("sig-1", header=START_BYTES_SHORT, frames=classic_frames)
    profile = SignatureAnalyzer().analyze(session)
    assert profile.header == "7878"
    assert profile.login_count >= 1
    assert profile.heartbeat_count >= 1
    assert profile.gps_count >= 1
    assert profile.crc_ok_count >= 1
    assert "0d0a" in profile.trailers_found


def test_clustering_groups_similar_sessions(classic_frames: list[bytes], v2_frames: list[bytes]) -> None:
    builder = FingerprintBuilder()
    fps = [
        builder.from_session(_session(f"c-{i}", header=START_BYTES_SHORT, frames=classic_frames))
        for i in range(3)
    ] + [
        builder.from_session(_session(f"v-{i}", header=START_BYTES_LONG, frames=v2_frames))
        for i in range(2)
    ]
    clusters = SessionClusterer().cluster(fps)
    assert len(clusters) >= 2
    sizes = sorted((c.size for c in clusters), reverse=True)
    assert sizes[0] >= 3
    assert any(c.signature == "7878" for c in clusters)
    assert any(c.signature == "7979" for c in clusters)


def test_confidence_suggests_known_protocols(classic_frames: list[bytes], v2_frames: list[bytes]) -> None:
    builder = FingerprintBuilder()
    confidence = ConfidenceEngine()

    classic_fp = builder.from_session(_session("conf-c", header=START_BYTES_SHORT, frames=classic_frames))
    v2_fp = builder.from_session(_session("conf-v", header=START_BYTES_LONG, frames=v2_frames))

    classic_suggestion = confidence.suggest_for_fingerprint(classic_fp)
    v2_suggestion = confidence.suggest_for_fingerprint(v2_fp)

    assert classic_suggestion is not None
    assert classic_suggestion.candidate == "GT06 Classic"
    assert classic_suggestion.confidence >= 70
    assert "Header 7878" in classic_suggestion.reason

    assert v2_suggestion is not None
    assert v2_suggestion.candidate == "GT06 V2"
    assert v2_suggestion.confidence >= 70


def test_similarity_engine_percentages(classic_frames: list[bytes]) -> None:
    fp = FingerprintBuilder().from_session(
        _session("sim-1", header=START_BYTES_SHORT, frames=classic_frames)
    )
    results = SimilarityEngine().compare_fingerprint(fp)
    by_name = {r.known_protocol: r.similarity_percent for r in results}
    assert by_name["GT06 Classic"] > by_name["GT06 V2"]
    assert by_name["GT06 Classic"] >= 80


def test_report_builder_summary(classic_frames: list[bytes], v2_frames: list[bytes]) -> None:
    engine = ProtocolIntelligenceEngine(sessions_dir=Path("."), promotions_dir=Path("."))
    sessions = [
        _session("r-c1", header=START_BYTES_SHORT, frames=classic_frames),
        _session("r-c2", header=START_BYTES_SHORT, frames=classic_frames),
        _session("r-v1", header=START_BYTES_LONG, frames=v2_frames),
    ]
    report = engine.analyze_sessions(sessions)
    text = report.summary_text()
    assert "Protocol Intelligence Report" in text
    assert report.sessions_analyzed == 3
    assert report.new_protocol_candidates >= 1
    assert report.largest_cluster_size >= 2
    assert report.to_dict()["statistics"] is not None


def test_promotion_workflow_is_manual(tmp_path: Path, classic_frames: list[bytes]) -> None:
    engine = ProtocolIntelligenceEngine(
        sessions_dir=tmp_path / "sessions",
        promotions_dir=tmp_path / "promotions",
    )
    sessions = [
        _session("p1", header=START_BYTES_SHORT, frames=classic_frames),
        _session("p2", header=START_BYTES_SHORT, frames=classic_frames),
    ]
    report = engine.analyze_sessions(sessions)
    assert report.clusters
    cluster_id = report.clusters[0].cluster_id

    proposal = engine.promote_cluster(cluster_id, protocol_name="GT06 Variant X", approved_by="dev")
    assert proposal.status == "pending_implementation"
    assert proposal.suggested_protocol_name == "gt06_variant_x"
    assert "approved_by=dev" in proposal.reasons

    saved = list((tmp_path / "promotions").glob("promo-*.json"))
    assert len(saved) == 1
    listed = engine.list_promotions()
    assert listed and listed[0]["cluster_id"] == cluster_id


def test_analyze_async_does_not_block_event_loop(classic_frames: list[bytes]) -> None:
    engine = ProtocolIntelligenceEngine()
    sessions = [_session("a1", header=START_BYTES_SHORT, frames=classic_frames)]

    async def _run():
        return await engine.analyze_async(sessions)

    report = asyncio.run(_run())
    assert report.sessions_analyzed == 1
