from datetime import UTC, datetime

from app.contracts.messages import SCHEMA_VERSION, DevicePosition


def test_schema_version_defaults() -> None:
    pos = DevicePosition(
        schema_version=SCHEMA_VERSION,
        trace_id="t1",
        tracker_imei="867686031234567",
        received_at=datetime.now(UTC),
        connection_id="c1",
        remote_ip="127.0.0.1",
        latitude=-23.5,
        longitude=-46.6,
        serial_number=1,
        payload_hash="abc",
        gps_time=datetime.now(UTC),
    )
    assert pos.schema_version == 1
    key1 = pos.dedup_key()
    key2 = pos.dedup_key()
    assert key1 == key2
    assert len(key1) == 64


def test_dedup_key_differs_by_serial() -> None:
    common = dict(
        schema_version=SCHEMA_VERSION,
        trace_id="t1",
        tracker_imei="867686031234567",
        received_at=datetime.now(UTC),
        connection_id="c1",
        remote_ip="127.0.0.1",
        latitude=-23.5,
        longitude=-46.6,
        payload_hash="abc",
        gps_time=datetime.now(UTC),
    )
    a = DevicePosition(**common, serial_number=1)
    b = DevicePosition(**common, serial_number=2)
    assert a.dedup_key() != b.dedup_key()
