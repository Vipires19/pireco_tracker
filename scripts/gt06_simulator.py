"""Simulador GT06 — Login, Heartbeat e GPS sem equipamento físico."""

import argparse
import asyncio
import sys
from pathlib import Path

# Permite importar encoder do gateway sem instalar como pacote
GATEWAY_ROOT = Path(__file__).resolve().parents[1] / "gateway"
sys.path.insert(0, str(GATEWAY_ROOT))

from app.protocol.encoder import (  # noqa: E402
    build_gps_packet,
    build_heartbeat_packet,
    build_login_packet,
)


async def run_simulator(host: str, port: int, imei: str, latitude: float, longitude: float) -> None:
    print(f"Conectando a {host}:{port} como IMEI {imei}...")

    reader, writer = await asyncio.open_connection(host, port)

    async def send_and_wait_ack(packet: bytes, label: str) -> None:
        writer.write(packet)
        await writer.drain()
        ack = await asyncio.wait_for(reader.read(1024), timeout=5.0)
        print(f"  [{label}] enviado ({len(packet)} bytes) | ACK ({len(ack)} bytes): {ack.hex()}")

    login = build_login_packet(imei, serial_number=1)
    await send_and_wait_ack(login, "LOGIN")

    await asyncio.sleep(0.5)

    heartbeat = build_heartbeat_packet(serial_number=2)
    await send_and_wait_ack(heartbeat, "HEARTBEAT")

    await asyncio.sleep(0.5)

    gps = build_gps_packet(latitude=latitude, longitude=longitude, speed_kmh=45.0, course=180)
    await send_and_wait_ack(gps, "GPS")

    print("Simulação concluída. Aguardando 1s antes de desconectar...")
    await asyncio.sleep(1)

    writer.close()
    await writer.wait_closed()
    print("Desconectado.")


def main() -> None:
    parser = argparse.ArgumentParser(description="Simulador GT06 (J16 compatível)")
    parser.add_argument("--host", default="localhost", help="Host do gateway TCP")
    parser.add_argument("--port", type=int, default=5023, help="Porta do gateway TCP")
    parser.add_argument("--imei", default="867686031234567", help="IMEI do rastreador")
    parser.add_argument("--lat", type=float, default=-23.550520, help="Latitude GPS")
    parser.add_argument("--lon", type=float, default=-46.633308, help="Longitude GPS")
    args = parser.parse_args()

    asyncio.run(run_simulator(args.host, args.port, args.imei, args.lat, args.lon))


if __name__ == "__main__":
    main()
