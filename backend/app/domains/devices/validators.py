import re

_IMEI_PATTERN = re.compile(r"^\d{15}$")
_ICCID_PATTERN = re.compile(r"^\d{19,20}$")
_SIM_IMEI_PATTERN = re.compile(r"^\d{15}$")


class DeviceValidationError(ValueError):
    pass


def digits_only(value: str) -> str:
    return re.sub(r"\D", "", value)


def validate_imei(imei: str) -> str:
    cleaned = digits_only(imei)
    if len(cleaned) != 15 or not _IMEI_PATTERN.match(cleaned):
        raise DeviceValidationError("invalid_imei")
    if cleaned == cleaned[0] * 15:
        raise DeviceValidationError("invalid_imei")
    return cleaned


def validate_iccid(iccid: str | None) -> str | None:
    if not iccid:
        return None
    cleaned = digits_only(iccid)
    if len(cleaned) < 19 or len(cleaned) > 20 or not _ICCID_PATTERN.match(cleaned):
        raise DeviceValidationError("invalid_iccid")
    return cleaned


def validate_sim_imei(sim_imei: str | None) -> str | None:
    if not sim_imei:
        return None
    cleaned = digits_only(sim_imei)
    if len(cleaned) != 15 or not _SIM_IMEI_PATTERN.match(cleaned):
        raise DeviceValidationError("invalid_sim_imei")
    return cleaned


def validate_tracker_phone(phone: str | None) -> str | None:
    if not phone:
        return None
    cleaned = digits_only(phone)
    if len(cleaned) < 10 or len(cleaned) > 11:
        raise DeviceValidationError("invalid_tracker_phone")
    return cleaned


def validate_firmware(firmware: str | None) -> str | None:
    if not firmware:
        return None
    normalized = firmware.strip()
    if not normalized or len(normalized) > 100:
        raise DeviceValidationError("invalid_firmware")
    return normalized


def validate_model(model: str | None) -> str | None:
    if not model:
        return None
    normalized = model.strip()
    if not normalized or len(normalized) > 100:
        raise DeviceValidationError("invalid_model")
    return normalized


def validate_manufacturer(manufacturer: str | None) -> str | None:
    if not manufacturer:
        return None
    normalized = manufacturer.strip()
    if not normalized or len(normalized) > 100:
        raise DeviceValidationError("invalid_manufacturer")
    return normalized


def validate_serial_number(serial_number: str | None) -> str | None:
    if not serial_number:
        return None
    normalized = serial_number.strip()
    if not normalized or len(normalized) > 100:
        raise DeviceValidationError("invalid_serial_number")
    return normalized
