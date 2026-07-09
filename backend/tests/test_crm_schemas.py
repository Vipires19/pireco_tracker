import pytest
from pydantic import ValidationError

from app.domains.crm.models import DocumentType
from app.domains.crm.schemas import CustomerCreate


def test_customer_create_normalizes_fields() -> None:
    payload = CustomerCreate(
        full_name="João Silva",
        document="529.982.247-25",
        document_type=DocumentType.CPF,
        phone="(11) 98765-4321",
        email="joao@example.com",
        zip_code="01310-100",
        state="sp",
        city="São Paulo",
    )
    assert payload.document == "52998224725"
    assert payload.phone == "11987654321"
    assert payload.zip_code == "01310100"
    assert payload.state == "SP"


def test_customer_create_requires_full_name() -> None:
    with pytest.raises(ValidationError):
        CustomerCreate(
            full_name="A",
            document="52998224725",
            document_type=DocumentType.CPF,
            phone="11987654321",
        )
