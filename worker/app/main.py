import asyncio
import json
import signal
import sys
from http.server import BaseHTTPRequestHandler, HTTPServer
from threading import Thread

import redis.asyncio as redis

from app.config import get_settings
from app.consumer.dlq import DeadLetterQueue
from app.consumer.stream_consumer import StreamConsumer
from app.core.database import db_manager
from app.core.logging import setup_logging
from app.handlers.message_handler import MessageHandler
from app.observability.metrics import metrics_payload
from app.services.persistence import PersistenceService
from app.core.observability import get_logger, log_with_fields

logger = get_logger(__name__)


class WorkerHealthHandler(BaseHTTPRequestHandler):
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
            self._json(200, {"status": "alive", "service": "worker"})
            return
        if self.path == "/ready":
            ok = self._check_deps()
            self._json(
                200 if ok else 503,
                {"status": "ready" if ok else "not_ready", "service": "worker"},
            )
            return
        if self.path == "/health":
            ok = self._check_deps()
            self._json(
                200 if ok else 503,
                {"status": "healthy" if ok else "degraded", "service": "worker"},
            )
            return
        self.send_response(404)
        self.end_headers()

    def _check_deps(self) -> bool:
        try:
            loop = asyncio.new_event_loop()
            settings = get_settings()
            r = redis.from_url(settings.redis_url, decode_responses=True)
            ok = loop.run_until_complete(r.ping())
            loop.run_until_complete(r.aclose())
            loop.close()
            return ok
        except Exception:
            return False

    def log_message(self, format: str, *args) -> None:
        return


def start_health_server() -> HTTPServer:
    settings = get_settings()
    server = HTTPServer((settings.health_host, settings.health_port), WorkerHealthHandler)
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return server


async def run_worker() -> None:
    setup_logging()
    settings = get_settings()
    log_with_fields(logger, 20, "Starting worker", env=settings.app_env)

    db_manager.init()
    redis_client = redis.from_url(settings.redis_url, encoding="utf-8", decode_responses=True)
    await redis_client.ping()

    persistence = PersistenceService(redis_client)
    handler = MessageHandler(persistence)
    dlq = DeadLetterQueue(redis_client)
    consumer = StreamConsumer(redis_client, handler, dlq)
    health_server = start_health_server()

    stop_event = asyncio.Event()

    def _shutdown() -> None:
        stop_event.set()

    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(sig, _shutdown)
        except NotImplementedError:
            pass

    consumer_task = asyncio.create_task(consumer.run())
    await stop_event.wait()
    await consumer.stop()
    consumer_task.cancel()
    health_server.shutdown()
    await redis_client.aclose()
    await db_manager.close()


def main() -> None:
    try:
        asyncio.run(run_worker())
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
