"""Métricas Prometheus do Worker."""

from prometheus_client import Counter, Histogram, generate_latest

EVENTS_CONSUMED = Counter("worker_events_consumed_total", "Eventos consumidos", ["message_type"])
EVENTS_PERSISTED = Counter("worker_events_persisted_total", "Eventos persistidos", ["message_type"])
EVENTS_FAILED = Counter("worker_events_failed_total", "Falhas de processamento")
EVENTS_RETRIED = Counter("worker_events_retried_total", "Tentativas de retry")
EVENTS_DLQ = Counter("worker_events_dlq_total", "Eventos enviados à DLQ")
EVENTS_DUPLICATE = Counter("worker_events_duplicate_total", "Eventos duplicados ignorados")
PIPELINE_LATENCY = Histogram(
    "worker_pipeline_latency_seconds",
    "Latência gateway→worker",
    buckets=(0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0),
)
DB_LATENCY = Histogram(
    "worker_db_latency_seconds",
    "Latência de persistência no banco",
    buckets=(0.001, 0.005, 0.01, 0.05, 0.1, 0.5, 1.0),
)
THROUGHPUT = Counter("worker_throughput_total", "Total de mensagens processadas com sucesso")


def metrics_payload() -> bytes:
    return generate_latest()
