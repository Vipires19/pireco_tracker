"""Replay Runner — reproduz sessões usando parsers de produção."""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any

from app.protocol import extract_packets
from app.protocols.base import BaseProtocol
from app.protocols.registry import UNKNOWN_PROTOCOL_NAME, create_default_registry
from tools.replay.loader import SessionLoadError, SessionRecord
from tools.replay.report import ReplayReport, TxComparison, compare_tx


def normalize_protocol_name(name: str | None) -> str:
    if not name:
        return UNKNOWN_PROTOCOL_NAME
    cleaned = name.strip().lower().replace("-", "_")
    aliases = {
        "gt06": "gt06",
        "gt-06": "gt06",
        "gt06_v2": "gt06_v2",
        "gt06v2": "gt06_v2",
        "unknown": "unknown",
    }
    return aliases.get(cleaned, cleaned)


@dataclass
class InjectResult:
    protocol: str
    input_hex: str
    valid: bool
    frames: int = 0
    acks: list[str] = field(default_factory=list)
    error: str | None = None
    packet_types: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "protocol": self.protocol,
            "input_hex": self.input_hex,
            "valid": self.valid,
            "frames": self.frames,
            "acks": list(self.acks),
            "packet_types": list(self.packet_types),
            "error": self.error,
        }


class ReplayRunner:
    """
    Executor do Replay Lab.

    Utiliza exatamente as mesmas instâncias BaseProtocol / parsers do Gateway.
    Não publica em Redis e não abre sockets reais.
    """

    def __init__(self, registry=None) -> None:
        self._registry = registry or create_default_registry()

    def get_protocol(self, name: str) -> BaseProtocol:
        normalized = normalize_protocol_name(name)
        protocol = self._registry.get(normalized)
        if protocol is None:
            raise SessionLoadError(f"Protocolo não registrado: {name}")
        if normalized != UNKNOWN_PROTOCOL_NAME and not protocol.has_parser:
            # Placeholder (ex.: gt06_v2) — same decision as production Registry.resolve
            unknown = self._registry.get(UNKNOWN_PROTOCOL_NAME)
            if unknown is None:
                raise SessionLoadError("UnknownProtocol não registrado")
            return unknown
        return protocol

    def inject(self, *, protocol: str, hex: str) -> InjectResult:
        """Injeta um pacote hex diretamente no parser de produção."""
        hex_clean = hex.strip().replace(" ", "").lower()
        try:
            data = bytes.fromhex(hex_clean)
        except ValueError as exc:
            return InjectResult(
                protocol=normalize_protocol_name(protocol),
                input_hex=hex_clean,
                valid=False,
                error=f"Hex inválido: {exc}",
            )

        proto = self.get_protocol(protocol)
        if proto.name == UNKNOWN_PROTOCOL_NAME or not proto.has_parser:
            return InjectResult(
                protocol=proto.name,
                input_hex=hex_clean,
                valid=False,
                frames=0,
                error="Protocolo sem parser (Learning Mode / placeholder)",
            )

        frames, _ = self._extract_frames(proto, data)
        acks: list[str] = []
        packet_types: list[str] = []
        valid_count = 0

        for frame in frames:
            try:
                packet = proto.parse_packet(frame)
            except Exception as exc:  # noqa: BLE001 — lab tool
                return InjectResult(
                    protocol=proto.name,
                    input_hex=hex_clean,
                    valid=False,
                    frames=len(frames),
                    error=f"Parser exception: {exc}",
                )

            if packet is None:
                continue

            valid_count += 1
            protocol_number = getattr(packet, "protocol_number", None)
            serial_number = getattr(packet, "serial_number", 0)
            if protocol_number is not None:
                packet_types.append(f"0x{int(protocol_number):02X}")
                ack = proto.build_ack(int(protocol_number), int(serial_number))
                acks.append(ack.hex())

        return InjectResult(
            protocol=proto.name,
            input_hex=hex_clean,
            valid=valid_count > 0,
            frames=len(frames),
            acks=acks,
            packet_types=packet_types,
            error=None if valid_count > 0 else "Nenhum pacote válido",
        )

    def replay(
        self,
        session: SessionRecord,
        *,
        protocol: str | None = None,
    ) -> ReplayReport:
        started = time.perf_counter()
        replay_id = str(uuid.uuid4())
        notes: list[str] = []

        protocol_name = normalize_protocol_name(protocol or session.protocol_detected)
        try:
            proto = self.get_protocol(protocol_name)
        except SessionLoadError as exc:
            return ReplayReport(
                replay_id=replay_id,
                parser=protocol_name,
                packets_total=0,
                packets_valid=0,
                packets_invalid=0,
                duration_ms=0.0,
                result="ERROR",
                session_id=session.session_id,
                protocol_detected=session.protocol_detected,
                notes=[str(exc)],
            )

        if protocol and normalize_protocol_name(protocol) != normalize_protocol_name(
            session.protocol_detected
        ):
            notes.append(
                f"Override de protocolo: session={session.protocol_detected} → {proto.name}"
            )

        generated_txs: list[bytes] = []
        expected_txs: list[bytes] = []
        packets_total = 0
        packets_valid = 0
        packets_invalid = 0
        buffer = bytearray()

        for event in session.events:
            kind = event.event.upper()

            if kind == "CONNECT":
                notes.append("CONNECT simulado")
                continue

            if kind == "RX":
                data = event.payload_bytes()
                if proto.name == UNKNOWN_PROTOCOL_NAME or not proto.has_parser:
                    # Learning Mode: captura apenas — sem gerar TX.
                    packets_total += 1
                    continue

                buffer.extend(data)
                frames, remaining = self._extract_frames(proto, bytes(buffer))
                buffer = bytearray(remaining)

                for frame in frames:
                    packets_total += 1
                    try:
                        packet = proto.parse_packet(frame)
                    except Exception:
                        packets_invalid += 1
                        continue

                    if packet is None:
                        packets_invalid += 1
                        continue

                    packets_valid += 1
                    protocol_number = getattr(packet, "protocol_number", None)
                    serial_number = getattr(packet, "serial_number", 0)
                    if protocol_number is None:
                        packets_invalid += 1
                        continue
                    ack = proto.build_ack(int(protocol_number), int(serial_number))
                    generated_txs.append(ack)
                continue

            if kind == "TX":
                expected_txs.append(event.payload_bytes())
                continue

            if kind in {"CLOSE", "TIMEOUT", "EXCEPTION"}:
                continue

        comparisons: list[TxComparison] = []
        pair_count = max(len(expected_txs), len(generated_txs))
        for index in range(pair_count):
            expected = expected_txs[index] if index < len(expected_txs) else b""
            obtained = generated_txs[index] if index < len(generated_txs) else b""
            comparisons.append(compare_tx(expected, obtained, index=index))

        # Sessão unknown sem TX esperado: sucesso se nada divergir.
        if not expected_txs and not generated_txs:
            notes.append("Nenhum TX para comparar")
            result = "MATCH"
        elif any(item.status == "DIFFERENT" for item in comparisons):
            result = "DIFFERENT"
        else:
            result = "MATCH"

        if len(expected_txs) != len(generated_txs):
            notes.append(
                f"Quantidade de TX diverge: esperado={len(expected_txs)} gerado={len(generated_txs)}"
            )
            if result == "MATCH" and (expected_txs or generated_txs):
                result = "DIFFERENT"

        duration_ms = round((time.perf_counter() - started) * 1000, 3)
        return ReplayReport(
            replay_id=replay_id,
            parser=proto.name,
            packets_total=packets_total,
            packets_valid=packets_valid,
            packets_invalid=packets_invalid,
            duration_ms=duration_ms,
            differences=comparisons,
            result=result,
            session_id=session.session_id,
            protocol_detected=session.protocol_detected,
            notes=notes,
        )

    def _extract_frames(self, protocol: BaseProtocol, data: bytes) -> tuple[list[bytes], bytes]:
        """
        Extrai frames usando a mesma rotina de produção quando disponível.

        Para GT06: app.protocol.extract_packets (parser de produção).
        Demais: trata o buffer integral como um frame candidato.
        """
        if protocol.name == "gt06":
            frames, remaining = extract_packets(bytearray(data))
            return frames, bytes(remaining)

        if not data:
            return [], b""
        return [data], b""
