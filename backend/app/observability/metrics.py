"""Métricas Prometheus do Backend."""

from prometheus_client import Counter, Histogram, generate_latest

HTTP_REQUESTS = Counter(
    "backend_http_requests_total", "Total de requisições HTTP", ["method", "endpoint", "status"]
)
HTTP_LATENCY = Histogram(
    "backend_http_request_duration_seconds",
    "Duração das requisições HTTP",
    ["method", "endpoint"],
    buckets=(0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0),
)
DB_QUERIES = Counter("backend_db_queries_total", "Consultas ao banco", ["operation"])
HTTP_ERRORS = Counter("backend_http_errors_total", "Erros HTTP", ["status"])


def metrics_payload() -> bytes:
    return generate_latest()
