import pytest

from app.domains.devices.validators import (
    DeviceValidationError,
    validate_firmware,
    validate_iccid,
    validate_imei,
    validate_model,
    validate_sim_imei,
    validate_tracker_phone,
)


def test_validate_imei() -> None:
    assert validate_imei("867686031234567") == "867686031234567"


def test_validate_imei_rejects_invalid() -> None:
    with pytest.raises(DeviceValidationError):
        validate_imei("12345")


def test_validate_iccid() -> None:
    assert validate_iccid("89555012345678901234") == "89555012345678901234"


def test_validate_sim_imei() -> None:
    assert validate_sim_imei("867686039876543") == "867686039876543"


def test_validate_tracker_phone() -> None:
    assert validate_tracker_phone("(11) 98765-4321") == "11987654321"


def test_validate_firmware_and_model() -> None:
    assert validate_firmware(" v1.0 ") == "v1.0"
    assert validate_model(" GT06 ") == "GT06"

    with pytest.raises(DeviceValidationError):
        validate_firmware("x" * 101)
