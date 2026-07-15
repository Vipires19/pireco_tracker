"""Session Loader — carrega sessões JSON/JSONL do Learning Mode."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


class SessionLoadError(ValueError):
    """Sessão ausente, corrompida ou estruturalmente inválida."""


@dataclass
class SessionEvent:
    event: str
    raw: dict[str, Any] = field(default_factory=dict)

    @property
    def hex_payload(self) -> str | None:
        value = self.raw.get("hex")
        return str(value) if value is not None else None

    def payload_bytes(self) -> bytes:
        hex_value = self.hex_payload
        if not hex_value:
            return b""
        try:
            return bytes.fromhex(hex_value)
        except ValueError as exc:
            raise SessionLoadError(f"Evento {self.event} com hex inválido: {hex_value!r}") from exc


@dataclass
class SessionRecord:
    session_id: str
    protocol_detected: str
    events: list[SessionEvent]
    raw: dict[str, Any] = field(default_factory=dict)

    @property
    def rx_events(self) -> list[SessionEvent]:
        return [e for e in self.events if e.event == "RX"]

    @property
    def tx_events(self) -> list[SessionEvent]:
        return [e for e in self.events if e.event == "TX"]


class SessionLoader:
    """Carrega sessões gravadas em JSONL (Learning Mode) ou JSON único."""

    def __init__(self, data_dir: str | Path | None = None) -> None:
        if data_dir is None:
            # gateway/data/sessions relativo à raiz do pacote gateway
            data_dir = Path(__file__).resolve().parents[2] / "data" / "sessions"
        self.data_dir = Path(data_dir)

    def load(self, source: str | Path | dict[str, Any]) -> SessionRecord:
        if isinstance(source, dict):
            return self._from_dict(source)

        path = Path(source)
        if not path.exists():
            # Permitir caminho relativo ao data_dir
            candidate = self.data_dir / path
            if candidate.exists():
                path = candidate
            else:
                raise SessionLoadError(f"Arquivo de sessão não encontrado: {source}")

        if path.suffix.lower() == ".jsonl":
            sessions = self.load_jsonl(path)
            if not sessions:
                raise SessionLoadError(f"Arquivo JSONL vazio: {path}")
            return sessions[-1]

        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise SessionLoadError(f"JSON inválido em {path}: {exc}") from exc

        if isinstance(payload, list):
            if not payload:
                raise SessionLoadError(f"Lista de sessões vazia em {path}")
            return self._from_dict(payload[-1])
        if not isinstance(payload, dict):
            raise SessionLoadError(f"Formato de sessão não suportado em {path}")
        return self._from_dict(payload)

    def load_jsonl(self, path: str | Path) -> list[SessionRecord]:
        path = Path(path)
        if not path.exists():
            raise SessionLoadError(f"Arquivo JSONL não encontrado: {path}")

        sessions: list[SessionRecord] = []
        for line_no, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
            text = line.strip()
            if not text:
                continue
            try:
                payload = json.loads(text)
            except json.JSONDecodeError as exc:
                raise SessionLoadError(f"JSONL inválido em {path}:{line_no}: {exc}") from exc
            sessions.append(self._from_dict(payload))
        return sessions

    def load_latest(self) -> SessionRecord:
        if not self.data_dir.exists():
            raise SessionLoadError(f"Diretório de sessões inexistente: {self.data_dir}")

        files = sorted(
            self.data_dir.glob("*.jsonl"),
            key=lambda p: p.stat().st_mtime,
        )
        if not files:
            raise SessionLoadError(f"Nenhum arquivo JSONL em {self.data_dir}")

        sessions = self.load_jsonl(files[-1])
        if not sessions:
            raise SessionLoadError(f"Último JSONL está vazio: {files[-1]}")
        return sessions[-1]

    def _from_dict(self, payload: dict[str, Any]) -> SessionRecord:
        if not isinstance(payload, dict):
            raise SessionLoadError("Sessão deve ser um objeto JSON")

        session_id = payload.get("session_id")
        if not session_id:
            raise SessionLoadError("Sessão inválida: session_id ausente")

        events_raw = payload.get("events")
        if events_raw is None:
            raise SessionLoadError("Sessão inválida: events ausente")
        if not isinstance(events_raw, list):
            raise SessionLoadError("Sessão inválida: events deve ser uma lista")

        events: list[SessionEvent] = []
        for item in events_raw:
            if not isinstance(item, dict) or "event" not in item:
                raise SessionLoadError("Sessão inválida: evento malformado")
            events.append(SessionEvent(event=str(item["event"]), raw=item))

        protocol = str(payload.get("protocol_detected") or "unknown")
        return SessionRecord(
            session_id=str(session_id),
            protocol_detected=protocol,
            events=events,
            raw=payload,
        )
