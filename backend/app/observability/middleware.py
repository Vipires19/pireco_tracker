import time

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint

from app.observability.metrics import HTTP_ERRORS, HTTP_LATENCY, HTTP_REQUESTS


class MetricsMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        if request.url.path == "/metrics":
            return await call_next(request)

        start = time.perf_counter()
        response = await call_next(request)
        elapsed = time.perf_counter() - start

        endpoint = request.url.path
        HTTP_REQUESTS.labels(
            method=request.method, endpoint=endpoint, status=str(response.status_code)
        ).inc()
        HTTP_LATENCY.labels(method=request.method, endpoint=endpoint).observe(elapsed)

        if response.status_code >= 400:
            HTTP_ERRORS.labels(status=str(response.status_code)).inc()

        return response
