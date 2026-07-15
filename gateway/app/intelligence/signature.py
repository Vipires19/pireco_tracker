"""Signature Analyzer — extrai padrões determinísticos de sessões unknown."""

from __future__ import annotations

from collections import Counter
from dataclasses import asdict, dataclass, field
from typing import Any

from app.protocols.gt06.crc import crc16_x25
from app.protocols.gt06.packets import (
    START_BYTES_LONG,
    START_BYTES_SHORT,
    STOP_BYTES,
    ProtocolNumber,
)


KNOWN_HEADERS = {
    START_BYTES_SHORT.hex(): "7878",
    START_BYTES_LONG.hex(): "7979",
}


@dataclass
class SignatureProfile:
    session_id: str
    first_bytes: str
    header: str | None
    trailer: str | None
    avg_packet_size: float
    packet_count: int
    total_bytes: int
    rx_count: int
    intervals_ms: list[float] = field(default_factory=list)
    avg_interval_ms: float | None = None
    login_count: int = 0
    heartbeat_count: int = 0
    gps_count: int = 0
    crc_ok_count: int = 0
    crc_fail_count: int = 0
    headers_found: list[str] = field(default_factory=list)
    trailers_found: list[str] = field(default_factory=list)
    close_reason: str | None = None
    duration_ms: float | None = None
    size_sequence: tuple[int, ...] = ()
    protocol_byte_histogram: dict[str, int] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class SignatureAnalyzer:
    """Calcula assinatura estrutural de uma sessão Learning Mode."""

    def analyze(self, session: dict[str, Any]) -> SignatureProfile:
        session_id = str(session.get("session_id") or "unknown")
        events = session.get("events") or []
        rx_events = [e for e in events if e.get("event") == "RX" and e.get("hex")]

        payloads: list[bytes] = []
        elapsed: list[float] = []
        for event in rx_events:
            try:
                payloads.append(bytes.fromhex(str(event["hex"])))
            except ValueError:
                continue
            try:
                elapsed.append(float(event.get("elapsed_ms") or 0.0))
            except (TypeError, ValueError):
                elapsed.append(0.0)

        sizes = [len(p) for p in payloads]
        total_bytes = sum(sizes)
        avg_size = (total_bytes / len(sizes)) if sizes else 0.0

        intervals: list[float] = []
        for i in range(1, len(elapsed)):
            delta = elapsed[i] - elapsed[i - 1]
            if delta >= 0:
                intervals.append(round(delta, 3))
        avg_interval = round(sum(intervals) / len(intervals), 3) if intervals else None

        first_bytes = payloads[0][:8].hex() if payloads else ""
        header = None
        if payloads:
            head = payloads[0][:2].hex()
            header = KNOWN_HEADERS.get(head, head if len(payloads[0]) >= 2 else None)

        headers = Counter()
        trailers = Counter()
        login = heartbeat = gps = 0
        crc_ok = crc_fail = 0
        proto_hist: Counter[str] = Counter()

        for payload in payloads:
            if len(payload) >= 2:
                headers[payload[:2].hex()] += 1
            if len(payload) >= 2 and payload.endswith(STOP_BYTES):
                trailers[STOP_BYTES.hex()] += 1
            elif len(payload) >= 2:
                trailers[payload[-2:].hex()] += 1

            for frame in self._candidate_frames(payload):
                result = self._inspect_frame(frame)
                if result is None:
                    continue
                kind, crc_ok_flag, protocol_number = result
                proto_hist[f"0x{protocol_number:02X}"] += 1
                if crc_ok_flag:
                    crc_ok += 1
                else:
                    crc_fail += 1
                if kind == "login":
                    login += 1
                elif kind == "heartbeat":
                    heartbeat += 1
                elif kind == "gps":
                    gps += 1

        trailer = STOP_BYTES.hex() if trailers.get(STOP_BYTES.hex()) else (
            trailers.most_common(1)[0][0] if trailers else None
        )

        return SignatureProfile(
            session_id=session_id,
            first_bytes=first_bytes,
            header=header,
            trailer=trailer,
            avg_packet_size=round(avg_size, 3),
            packet_count=len(payloads),
            total_bytes=total_bytes,
            rx_count=len(rx_events),
            intervals_ms=intervals,
            avg_interval_ms=avg_interval,
            login_count=login,
            heartbeat_count=heartbeat,
            gps_count=gps,
            crc_ok_count=crc_ok,
            crc_fail_count=crc_fail,
            headers_found=sorted(headers.keys()),
            trailers_found=sorted(trailers.keys()),
            close_reason=session.get("close_reason"),
            duration_ms=_as_float(session.get("duration_ms")),
            size_sequence=tuple(sizes[:16]),
            protocol_byte_histogram=dict(proto_hist),
        )

    def _candidate_frames(self, payload: bytes) -> list[bytes]:
        frames: list[bytes] = []
        for marker in (START_BYTES_SHORT, START_BYTES_LONG):
            offset = 0
            while True:
                idx = payload.find(marker, offset)
                if idx < 0:
                    break
                length_size = 1 if marker == START_BYTES_SHORT else 2
                if idx + 2 + length_size > len(payload):
                    break
                if length_size == 1:
                    packet_length = payload[idx + 2]
                    header_size = 3
                else:
                    packet_length = int.from_bytes(payload[idx + 2 : idx + 4], "big")
                    header_size = 4
                total = header_size + packet_length + 2
                if idx + total > len(payload):
                    offset = idx + 2
                    continue
                frame = payload[idx : idx + total]
                if frame.endswith(STOP_BYTES):
                    frames.append(frame)
                    offset = idx + total
                else:
                    offset = idx + 2
        if not frames and payload:
            frames.append(payload)
        return frames

    def _inspect_frame(self, frame: bytes) -> tuple[str, bool, int] | None:
        if len(frame) < 10:
            return None
        if frame.startswith(START_BYTES_SHORT):
            length = frame[2]
            data_start = 3
        elif frame.startswith(START_BYTES_LONG):
            length = int.from_bytes(frame[2:4], "big")
            data_start = 4
        else:
            return None

        data_end = data_start + length - 2
        if data_end + 4 > len(frame):
            return None
        protocol_number = frame[data_start]
        received_crc = int.from_bytes(frame[data_end : data_end + 2], "big")
        ok = crc16_x25(frame[2:data_end]) == received_crc

        if protocol_number == ProtocolNumber.LOGIN:
            kind = "login"
        elif protocol_number == ProtocolNumber.HEARTBEAT:
            kind = "heartbeat"
        elif protocol_number in (ProtocolNumber.GPS_LOCATION, ProtocolNumber.GPS_LOCATION_4G):
            kind = "gps"
        else:
            kind = "other"
        return kind, ok, protocol_number


def _as_float(value: Any) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None
