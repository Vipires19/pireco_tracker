"""Exceções de domínio compartilhadas."""


class TrackerError(Exception):
    def __init__(self, message: str, *, details: dict | None = None) -> None:
        super().__init__(message)
        self.details = details or {}


class CRCValidationError(TrackerError):
    pass


class InvalidPacketError(TrackerError):
    pass


class UnknownProtocolError(TrackerError):
    pass


class InvalidIMEIError(TrackerError):
    pass


class ConnectionTimeoutError(TrackerError):
    pass


class PublishEventError(TrackerError):
    pass


class PersistenceError(TrackerError):
    pass


class DuplicateEventError(TrackerError):
    pass


class CommandDeliveryError(TrackerError):
    pass


__all__ = [
    "CRCValidationError",
    "CommandDeliveryError",
    "ConnectionTimeoutError",
    "DuplicateEventError",
    "InvalidIMEIError",
    "InvalidPacketError",
    "PersistenceError",
    "PublishEventError",
    "TrackerError",
    "UnknownProtocolError",
]
