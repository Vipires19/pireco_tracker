import pytest

from app.domains.fleet.validators import (
    VehicleValidationError,
    normalize_plate,
    validate_chassis,
    validate_cover_image,
    validate_renavam,
)


def test_normalize_plate_mercosul() -> None:
    assert normalize_plate("abc-1d23") == "ABC1D23"


def test_normalize_plate_rejects_invalid() -> None:
    with pytest.raises(VehicleValidationError):
        normalize_plate("ABC123")


def test_validate_renavam() -> None:
    assert validate_renavam("123.456.789-01") == "12345678901"


def test_validate_chassis() -> None:
    assert validate_chassis("9bwzzz377vt004251") == "9BWZZZ377VT004251"


def test_validate_cover_image() -> None:
    assert validate_cover_image("https://cdn.example.com/photo.jpg") == (
        "https://cdn.example.com/photo.jpg"
    )

    with pytest.raises(VehicleValidationError):
        validate_cover_image("not-a-url")
