"""Simulador de carga GT06 — testes de escala."""

import argparse
import asyncio
import json
import os
import sys
import time
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path

try:
    import psutil
except ImportError:
    psutil = None

GATEWAY_ROOT = Path(__file__).resolve().parents[1] / "gateway"
sys.path.insert(0, str(GATEWAY_ROOT))

from app.protocol.encoder import (  # noqa: E402
    build_gps_packet,
    build_heartbeat_packet,
    build_login_packet,
)


@dataclass
class TrackerSim:
    imei: str
    serial: int = 1
    latitude: float = -23.55
    longitude: float = -46.63


@dataclass
class LoadReport:
    trackers: int = 0
    connections_ok: int = 0
    connections_failed: int = 0
    packets_sent: int = 0
    acks_received: int = 0
    errors: int = 0
    duration_s: float = 0.0
    cpu_percent: float = 0.0
    memory_mb: float = 0.0
    events_per_second: float = 0.0
    start_time: str = ""
    end_time: str = ""


async def simulate_tracker(
    host: str,
    port: int,
    tracker: TrackerSim,
    duration_s: int,
    interval_s: float,
    report: LoadReport,
) -> None:
    try:
        reader, writer = await asyncio.open_connection(host, port)
        report.connections_ok += 1

        async def send(pkt: bytes) -> None:
            writer.write(pkt)
            await writer.drain()
            report.packets_sent += 1
            ack = await asyncio.wait_for(reader.read(1024), timeout=5.0)
            if ack:
                report.acks_received += 1

        await send(build_login_packet(tracker.imei, tracker.serial))
        tracker.serial += 1
        await asyncio.sleep(0.2)

        deadline = time.monotonic() + duration_s
        while time.monotonic() < deadline:
            await send(build_heartbeat_packet(serial_number=tracker.serial))
            tracker.serial += 1
            await asyncio.sleep(0.1)
            tracker.latitude += 0.0001
            await send(
                build_gps_packet(
                    latitude=tracker.latitude,
                    longitude=tracker.longitude,
                    serial_number=tracker.serial,
                )
            )
            tracker.serial += 1
            await asyncio.sleep(interval_s)

        writer.close()
        await writer.wait_closed()
    except Exception:
        report.errors += 1
        report.connections_failed += 1


async def run_load_test(
    host: str,
    port: int,
    num_trackers: int,
    duration_s: int,
    interval_s: float,
) -> LoadReport:
    report = LoadReport(trackers=num_trackers)
    report.start_time = datetime.now(UTC).isoformat()

    if psutil:
        psutil.cpu_percent(interval=None)

    base_imei = 867686030000000
    trackers = [
        TrackerSim(imei=str(base_imei + i), latitude=-23.55 + i * 0.001, longitude=-46.63 + i * 0.001)
        for i in range(num_trackers)
    ]

    start = time.monotonic()
    await asyncio.gather(
        *[simulate_tracker(host, port, t, duration_s, interval_s, report) for t in trackers],
        return_exceptions=True,
    )
    report.duration_s = time.monotonic() - start
    report.end_time = datetime.now(UTC).isoformat()

    if report.duration_s > 0:
        report.events_per_second = report.packets_sent / report.duration_s

    if psutil:
        report.cpu_percent = psutil.cpu_percent(interval=0.1)
        report.memory_mb = psutil.Process(os.getpid()).memory_info().rss / 1024 / 1024

    return report


def print_report(report: LoadReport) -> None:
    print("\n" + "=" * 60)
    print("RELATÓRIO DE TESTE DE CARGA GT06")
    print("=" * 60)
    print(f"Rastreadores simulados:     {report.trackers}")
    print(f"Conexões bem-sucedidas:     {report.connections_ok}")
    print(f"Conexões falhadas:          {report.connections_failed}")
    print(f"Pacotes enviados:           {report.packets_sent}")
    print(f"ACKs recebidos:             {report.acks_received}")
    print(f"Erros:                      {report.errors}")
    print(f"Duração (s):                {report.duration_s:.2f}")
    print(f"Eventos/segundo:            {report.events_per_second:.2f}")
    print(f"CPU (%):                    {report.cpu_percent:.1f}")
    print(f"Memória (MB):               {report.memory_mb:.1f}")
    print(f"Início:                     {report.start_time}")
    print(f"Fim:                        {report.end_time}")
    loss = report.packets_sent - report.acks_received
    print(f"Perda estimada (sem ACK):   {max(loss, 0)}")
    print("=" * 60)


def main() -> None:
    parser = argparse.ArgumentParser(description="Teste de carga GT06")
    parser.add_argument("--host", default="localhost")
    parser.add_argument("--port", type=int, default=5023)
    parser.add_argument("--trackers", type=int, default=10)
    parser.add_argument("--duration", type=int, default=30, help="Duração em segundos")
    parser.add_argument("--interval", type=float, default=5.0, help="Intervalo entre GPS")
    parser.add_argument("--output", default="", help="Salvar relatório JSON")
    args = parser.parse_args()

    report = asyncio.run(
        run_load_test(args.host, args.port, args.trackers, args.duration, args.interval)
    )
    print_report(report)

    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            json.dump(report.__dict__, f, indent=2)
        print(f"Relatório salvo em {args.output}")


if __name__ == "__main__":
    main()
