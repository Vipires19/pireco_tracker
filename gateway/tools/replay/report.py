"""Relatórios e Diff Engine do Replay Lab."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any, Literal


@dataclass(frozen=True)
class ByteDifference:
    position: int
    expected: str
    obtained: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "position": self.position,
            "expected": self.expected,
            "obtained": self.obtained,
            "byte": self.position,
        }


@dataclass
class TxComparison:
    index: int
    status: Literal["MATCH", "DIFFERENT"]
    expected_hex: str
    obtained_hex: str
    differences: list[ByteDifference] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "index": self.index,
            "status": self.status,
            "expected_hex": self.expected_hex,
            "obtained_hex": self.obtained_hex,
            "differences": [d.to_dict() for d in self.differences],
        }


def diff_bytes(expected: bytes, obtained: bytes) -> list[ByteDifference]:
    """Compara TX esperado vs gerado byte a byte."""
    differences: list[ByteDifference] = []
    length = max(len(expected), len(obtained))
    for position in range(length):
        exp = expected[position] if position < len(expected) else None
        got = obtained[position] if position < len(obtained) else None
        if exp != got:
            differences.append(
                ByteDifference(
                    position=position,
                    expected=f"{exp:02x}" if exp is not None else "<missing>",
                    obtained=f"{got:02x}" if got is not None else "<missing>",
                )
            )
    return differences


def compare_tx(expected: bytes, obtained: bytes, *, index: int) -> TxComparison:
    differences = diff_bytes(expected, obtained)
    status: Literal["MATCH", "DIFFERENT"] = "MATCH" if not differences else "DIFFERENT"
    return TxComparison(
        index=index,
        status=status,
        expected_hex=expected.hex(),
        obtained_hex=obtained.hex(),
        differences=differences,
    )


ResultKind = Literal["MATCH", "DIFFERENT", "ERROR"]


@dataclass
class ReplayReport:
    replay_id: str
    parser: str
    packets_total: int
    packets_valid: int
    packets_invalid: int
    duration_ms: float
    differences: list[TxComparison] = field(default_factory=list)
    result: ResultKind = "MATCH"
    session_id: str | None = None
    protocol_detected: str | None = None
    notes: list[str] = field(default_factory=list)
    generated_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())

    @property
    def difference_count(self) -> int:
        return sum(1 for item in self.differences if item.status == "DIFFERENT")

    def to_dict(self) -> dict[str, Any]:
        return {
            "replay_id": self.replay_id,
            "session_id": self.session_id,
            "parser": self.parser,
            "protocol_detected": self.protocol_detected,
            "packets_total": self.packets_total,
            "packets_valid": self.packets_valid,
            "packets_invalid": self.packets_invalid,
            "duration_ms": self.duration_ms,
            "differences_found": self.difference_count,
            "differences": [item.to_dict() for item in self.differences],
            "result": self.result,
            "notes": list(self.notes),
            "generated_at": self.generated_at,
        }

    def to_json(self, *, indent: int = 2) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=indent)

    def summary_lines(self) -> list[str]:
        lines = [
            f"Replay ID: {self.replay_id}",
            f"Parser: {self.parser}",
            f"Session: {self.session_id or '-'}",
            f"Packets: total={self.packets_total} valid={self.packets_valid} invalid={self.packets_invalid}",
            f"Duration: {self.duration_ms:.3f} ms",
            f"Differences: {self.difference_count}",
            f"Result: {self.result}",
        ]
        for note in self.notes:
            lines.append(f"Note: {note}")
        for item in self.differences:
            if item.status == "MATCH":
                continue
            lines.append(f"TX[{item.index}] DIFFERENT expected={item.expected_hex} obtained={item.obtained_hex}")
            for diff in item.differences[:10]:
                lines.append(
                    f"  byte@{diff.position}: expected={diff.expected} obtained={diff.obtained}"
                )
            if len(item.differences) > 10:
                lines.append(f"  ... +{len(item.differences) - 10} mais")
        return lines
