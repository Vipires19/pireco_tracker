from datetime import UTC, datetime

from app.contracts.messages import SCHEMA_VERSION
from app.contracts.messages import parse_stream_fields


def test_parse_position_message() -> None:
    fields = {
        "schema_version": str(SCHEMA_VERSION),
        "trace_id": "trace-abc",
        "message_type": "position",
        "tracker_imei": "867686031234567",
        "connection_id": "c1",
        "remote_ip": "127.0.0.1",
        "received_at": datetime.now(UTC).isoformat(),
        "published_at": datetime.now(UTC).isoformat(),
        "source_protocol": "gt06",
        "latitude": "-23.550520",
        "longitude": "-46.633308",
        "speed_kmh": "45.0",
        "course_degrees": "180",
        "gps_time": datetime.now(UTC).isoformat(),
        "serial_number": "3",
        "payload_hash": "abc123",
    }
    msg = parse_stream_fields(fields)
    assert msg is not None
    assert msg.message_type.value == "position"
    assert msg.trace_id == "trace-abc"
    assert msg.latitude == -23.550520


def test_parse_invalid_message_returns_none() -> None:
    assert parse_stream_fields({}) is None
