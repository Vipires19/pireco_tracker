"""Persistência JSON Lines de sessões capturadas em Learning Mode."""

from __future__ import annotations

import json
import threading
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from app.core.observability import get_logger

logger = get_logger(__name__)

_lock = threading.Lock()
_store: SessionStore | None = None


class SessionStore:
    """Grava cada sessão completa como uma linha em YYYY-MM-DD.jsonl."""

    def __init__(self, data_dir: str | Path) -> None:
        self._data_dir = Path(data_dir)

    def ensure_dir(self) -> Path:
        self._data_dir.mkdir(parents=True, exist_ok=True)
        return self._data_dir

    def append(self, session: dict[str, Any]) -> Path:
        self.ensure_dir()
        day = datetime.now(UTC).strftime("%Y-%m-%d")
        path = self._data_dir / f"{day}.jsonl"
        line = json.dumps(session, ensure_ascii=False, default=str)
        with _lock:
            with path.open("a", encoding="utf-8") as fh:
                fh.write(line)
                fh.write("\n")
        logger.info(
            "Learning session persisted session_id=%s path=%s",
            session.get("session_id"),
            path,
        )
        return path


def get_session_store() -> SessionStore:
    global _store
    if _store is None:
        from app.config import get_settings

        settings = get_settings()
        _store = SessionStore(settings.sessions_data_dir)
    return _store
