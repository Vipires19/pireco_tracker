import re
from datetime import UTC, datetime

from app.domains.fleet.models import VehicleCategory, VehicleFuel

_PLATE_PATTERN = re.compile(r"^[A-Z]{3}[0-9][A-Z0-9][0-9]{2}$")
_CHASSIS_PATTERN = re.compile(r"^[A-HJ-NPR-Z0-9]{17}$")


class VehicleValidationError(ValueError):
    pass


def normalize_plate(plate: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9]", "", plate).upper()
    if len(cleaned) != 7 or not _PLATE_PATTERN.match(cleaned):
        raise VehicleValidationError("invalid_plate")
    return cleaned


def validate_renavam(renavam: str | None) -> str | None:
    if not renavam:
        return None
    cleaned = re.sub(r"\D", "", renavam)
    if len(cleaned) != 11:
        raise VehicleValidationError("invalid_renavam")
    return cleaned


def validate_chassis(chassis: str | None) -> str | None:
    if not chassis:
        return None
    cleaned = re.sub(r"[^A-Za-z0-9]", "", chassis).upper()
    if len(cleaned) != 17 or not _CHASSIS_PATTERN.match(cleaned):
        raise VehicleValidationError("invalid_chassis")
    return cleaned


def validate_year(year: int | None, *, field_name: str) -> int | None:
    if year is None:
        return None
    current_year = datetime.now(UTC).year + 1
    if year < 1900 or year > current_year:
        raise VehicleValidationError(f"invalid_{field_name}")
    return year


def validate_odometer(odometer: int | None) -> int | None:
    if odometer is None:
        return None
    if odometer < 0:
        raise VehicleValidationError("invalid_odometer")
    return odometer


def validate_cover_image(url: str | None) -> str | None:
    if not url:
        return None
    normalized = url.strip()
    if not normalized.startswith(("http://", "https://")):
        raise VehicleValidationError("invalid_cover_image")
    return normalized


def validate_category(category: VehicleCategory | str | None) -> VehicleCategory | None:
    if category is None:
        return None
    return VehicleCategory(category)


def validate_fuel(fuel: VehicleFuel | str | None) -> VehicleFuel | None:
    if fuel is None:
        return None
    return VehicleFuel(fuel)
