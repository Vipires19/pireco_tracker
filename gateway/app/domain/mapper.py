"""Conversão GT06 → contratos compartilhados versionados."""

from datetime import UTC, datetime

from app.contracts.messages import SCHEMA_VERSION
from app.contracts.messages import (
    DeviceConnection,
    DeviceEvent,
    DeviceHeartbeat,
    DevicePosition,
    DomainMessage,
    compute_payload_hash,
)
from app.core.observability import new_trace_id

from app.protocol.constants import ProtocolNumber
from app.protocol.packets import (
    Gt06Packet,
    decode_gps_coordinates,
    decode_gps_course,
    decode_gps_datetime,
    decode_gps_speed,
)


class Gt06DomainMapper:
    def map_packet(
        self,
        packet: Gt06Packet,
        *,
        tracker_imei: str | None,
        connection_id: str,
        remote_ip: str,
        trace_id: str | None = None,
    ) -> DomainMessage | None:
        received_at = datetime.now(UTC)
        imei = packet.imei or tracker_imei
        tid = trace_id or new_trace_id()
        payload_hash = compute_payload_hash(packet.raw)

        base = {
            "schema_version": SCHEMA_VERSION,
            "trace_id": tid,
            "received_at": received_at,
            "connection_id": connection_id,
            "remote_ip": remote_ip,
            "source_protocol": "gt06",
            "serial_number": packet.serial_number,
            "payload_hash": payload_hash,
        }

        if packet.protocol_number == ProtocolNumber.LOGIN:
            if not imei:
                return None
            return DeviceConnection(tracker_imei=imei, action="login", **base)

        if not imei:
            return None

        base["tracker_imei"] = imei

        if packet.protocol_number in (ProtocolNumber.GPS_LOCATION, ProtocolNumber.GPS_LOCATION_4G):
            lat, lon = decode_gps_coordinates(packet.payload)
            return DevicePosition(
                **base,
                latitude=lat,
                longitude=lon,
                speed_kmh=decode_gps_speed(packet.payload),
                course_degrees=decode_gps_course(packet.payload),
                gps_time=decode_gps_datetime(packet.payload),
            )

        if packet.protocol_number == ProtocolNumber.HEARTBEAT:
            terminal_info = voltage_level = None
            gsm_signal = None
            if len(packet.payload) >= 1:
                terminal_info = f"0x{packet.payload[0]:02x}"
            if len(packet.payload) >= 2:
                voltage_level = f"0x{packet.payload[1]:02x}"
            if len(packet.payload) >= 3:
                gsm_signal = packet.payload[2]
            return DeviceHeartbeat(
                **base,
                terminal_info=terminal_info,
                voltage_level=voltage_level,
                gsm_signal=gsm_signal,
            )

        if packet.protocol_number == ProtocolNumber.ALARM:
            code = f"alarm_{packet.payload[0]:02x}" if packet.payload else "alarm_unknown"
            return DeviceEvent(
                **base,
                event_code=code,
                event_category="alarm",
            )

        return None


gt06_domain_mapper = Gt06DomainMapper()
