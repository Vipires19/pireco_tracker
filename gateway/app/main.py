import asyncio
import json
import sys
from http.server import BaseHTTPRequestHandler, HTTPServer
from threading import Thread

from app.config import get_settings
from app.core.logging import get_logger, setup_logging
from app.core.observability import log_with_fields
from app.observability.metrics import metrics_payload
from app.publisher.redis_publisher import event_publisher
from app.server import GatewayTcpServer
from app.sessions.manager import session_manager

logger = get_logger(__name__)


class HealthHandler(BaseHTTPRequestHandler):
    def _json(self, code: int, payload: dict) -> None:
        body = json.dumps(payload).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:
        if self.path == "/metrics":
            self.send_response(200)
            self.send_header("Content-Type", "text/plain; version=0.0.4; charset=utf-8")
            self.end_headers()
            self.wfile.write(metrics_payload())
            return

        if self.path == "/live":
            self._json(200, {"status": "alive", "service": "gateway"})
            return

        if self.path == "/ready":
            redis_ok = self._check_redis()
            code = 200 if redis_ok else 503
            self._json(
                code,
                {
                    "status": "ready" if redis_ok else "not_ready",
                    "service": "gateway",
                    "checks": {"redis": "healthy" if redis_ok else "unhealthy"},
                },
            )
            return

        if self.path == "/health":
            redis_ok = self._check_redis()
            status = "healthy" if redis_ok else "degraded"
            code = 200 if redis_ok else 503
            self._json(
                code,
                {
                    "status": status,
                    "service": "gateway",
                    "active_connections": session_manager.active_count,
                    "checks": {"redis": "healthy" if redis_ok else "unhealthy"},
                },
            )
            return

        self.send_response(404)
        self.end_headers()

    def _check_redis(self) -> bool:
        try:
            loop = asyncio.new_event_loop()
            ok = loop.run_until_complete(event_publisher.ping())
            loop.close()
            return ok
        except Exception:
            return False

    def log_message(self, format: str, *args) -> None:
        return


def start_health_server() -> HTTPServer:
    settings = get_settings()
    server = HTTPServer((settings.health_host, settings.health_port), HealthHandler)
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    log_with_fields(
        logger,
        20,
        "Health server listening",
        host=settings.health_host,
        port=settings.health_port,
    )
    return server


async def run_gateway() -> None:
    setup_logging()
    settings = get_settings()
    logger.info("Starting gateway env=%s", settings.app_env)

    await event_publisher.connect()
    tcp_server = GatewayTcpServer()
    health_server = start_health_server()

    await tcp_server.start()

    try:
        await asyncio.Event().wait()
    finally:
        health_server.shutdown()
        await tcp_server.stop()
        await event_publisher.close()


def main() -> None:
    setup_logging()
    if sys.platform != "win32":
        try:
            import uvloop

            asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())
        except ImportError:
            pass
    asyncio.run(run_gateway())


if __name__ == "__main__":
    main()
