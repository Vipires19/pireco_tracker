from contextvars import ContextVar
from uuid import uuid4

trace_id_var: ContextVar[str | None] = ContextVar("trace_id", default=None)
connection_id_var: ContextVar[str | None] = ContextVar("connection_id", default=None)
imei_var: ContextVar[str | None] = ContextVar("imei", default=None)
remote_ip_var: ContextVar[str | None] = ContextVar("remote_ip", default=None)
packet_type_var: ContextVar[str | None] = ContextVar("packet_type", default=None)
event_type_var: ContextVar[str | None] = ContextVar("event_type", default=None)
latency_ms_var: ContextVar[float | None] = ContextVar("latency_ms", default=None)


def new_trace_id() -> str:
    return str(uuid4())


def bind_context(
    *,
    trace_id: str | None = None,
    connection_id: str | None = None,
    imei: str | None = None,
    remote_ip: str | None = None,
    packet_type: str | None = None,
    event_type: str | None = None,
    latency_ms: float | None = None,
) -> None:
    if trace_id is not None:
        trace_id_var.set(trace_id)
    if connection_id is not None:
        connection_id_var.set(connection_id)
    if imei is not None:
        imei_var.set(imei)
    if remote_ip is not None:
        remote_ip_var.set(remote_ip)
    if packet_type is not None:
        packet_type_var.set(packet_type)
    if event_type is not None:
        event_type_var.set(event_type)
    if latency_ms is not None:
        latency_ms_var.set(latency_ms)


def get_log_context() -> dict[str, str | float | None]:
    return {
        "trace_id": trace_id_var.get(),
        "connection_id": connection_id_var.get(),
        "imei": imei_var.get(),
        "remote_ip": remote_ip_var.get(),
        "packet_type": packet_type_var.get(),
        "event_type": event_type_var.get(),
        "latency_ms": latency_ms_var.get(),
    }
