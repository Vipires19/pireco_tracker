"""Métricas Prometheus do Gateway."""

from prometheus_client import Counter, Gauge, Histogram, generate_latest

# --- Métricas existentes (não remover) ---
TCP_CONNECTIONS_ACTIVE = Gauge("gateway_tcp_connections_active", "Conexões TCP ativas")
TCP_CONNECTIONS_CLOSED = Counter("gateway_tcp_connections_closed_total", "Conexões encerradas")
PACKETS_RECEIVED = Counter("gateway_packets_received_total", "Pacotes recebidos")
PACKETS_INVALID = Counter("gateway_packets_invalid_total", "Pacotes inválidos")
ACKS_SENT = Counter("gateway_acks_sent_total", "ACKs enviados")
BYTES_RECEIVED = Counter("gateway_bytes_received_total", "Bytes recebidos")
BYTES_SENT = Counter("gateway_bytes_sent_total", "Bytes enviados")
EVENTS_PUBLISHED = Counter(
    "gateway_events_published_total", "Eventos publicados", ["message_type"]
)
PUBLISH_LATENCY = Histogram(
    "gateway_publish_latency_seconds", "Latência de publicação Redis", buckets=(0.001, 0.01, 0.05, 0.1, 0.5)
)

# --- Métricas Fase 0 (observabilidade de sessão) ---
CONNECTIONS_TOTAL = Counter("gateway_connections_total", "Total de conexões TCP aceitas")
CONNECTIONS_ACTIVE = Gauge("gateway_connections_active", "Conexões TCP ativas (sessão)")
RX_BYTES_TOTAL = Counter("gateway_rx_bytes_total", "Total de bytes recebidos (RX)")
TX_BYTES_TOTAL = Counter("gateway_tx_bytes_total", "Total de bytes enviados (TX)")
SESSIONS_CLOSED_TOTAL = Counter(
    "gateway_sessions_closed_total",
    "Sessões TCP encerradas",
    ["reason"],
)
EXCEPTIONS_TOTAL = Counter("gateway_exceptions_total", "Exceções em sessões TCP")


def metrics_payload() -> bytes:
    return generate_latest()
