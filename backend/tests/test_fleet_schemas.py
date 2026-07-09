import pytest
from pydantic import ValidationError

from app.domains.fleet.models import VehicleCategory, VehicleFuel
from app.domains.fleet.schemas import VehicleCreate


def test_vehicle_create_normalizes_fields() -> None:
    payload = VehicleCreate(
        customer_id=1,
        plate="abc-1d23",
        nickname="Hilux Fazenda",
        brand="Toyota",
        model="Hilux",
        year_model=2024,
        year_manufacture=2023,
        fuel=VehicleFuel.DIESEL,
        category=VehicleCategory.TRUCK,
        chassis="9BWZZZ377VT004251",
        renavam="12345678901",
        cover_image="https://cdn.example.com/vehicles/hilux.jpg",
        odometer=15000,
    )
    assert payload.plate == "ABC1D23"
    assert payload.chassis == "9BWZZZ377VT004251"
    assert payload.renavam == "12345678901"
    assert payload.cover_image == "https://cdn.example.com/vehicles/hilux.jpg"


def test_vehicle_create_requires_valid_plate() -> None:
    with pytest.raises(ValidationError):
        VehicleCreate(
            customer_id=1,
            plate="INVALID",
        )
