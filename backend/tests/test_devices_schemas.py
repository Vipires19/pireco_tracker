import pytest
from pydantic import ValidationError

from app.domains.devices.schemas import TrackerCreate


def test_tracker_create_normalizes_fields() -> None:
    payload = TrackerCreate(
        imei="867686031234567",
        model=" GT06N ",
        manufacturer=" Concox ",
        firmware=" v1.2.3 ",
        tracker_phone_number="(11) 98765-4321",
        sim_iccid="8955 5012 3456 7890 1234",
        sim_imei="867686039876543",
        serial_number=" SN-001 ",
    )
    assert payload.imei == "867686031234567"
    assert payload.model == "GT06N"
    assert payload.manufacturer == "Concox"
    assert payload.firmware == "v1.2.3"
    assert payload.tracker_phone_number == "11987654321"
    assert payload.sim_iccid == "89555012345678901234"
    assert payload.sim_imei == "867686039876543"
    assert payload.serial_number == "SN-001"


def test_tracker_create_requires_valid_imei() -> None:
    with pytest.raises(ValidationError):
        TrackerCreate(imei="123")
