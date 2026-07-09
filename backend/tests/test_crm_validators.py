import pytest

from app.domains.crm.models import DocumentType
from app.domains.crm.validators import (
    CustomerValidationError,
    validate_document,
    validate_phone,
    validate_state,
    validate_zip_code,
)


def test_validate_cpf_strips_mask() -> None:
    assert validate_document("529.982.247-25", DocumentType.CPF) == "52998224725"


def test_validate_cpf_invalid_length() -> None:
    with pytest.raises(CustomerValidationError, match="invalid_cpf"):
        validate_document("123", DocumentType.CPF)


def test_validate_cnpj_strips_mask() -> None:
    assert validate_document("12.345.678/0001-95", DocumentType.CNPJ) == "12345678000195"


def test_validate_cnpj_invalid_length() -> None:
    with pytest.raises(CustomerValidationError, match="invalid_cnpj"):
        validate_document("123456789", DocumentType.CNPJ)


def test_validate_phone() -> None:
    assert validate_phone("(11) 98765-4321") == "11987654321"


def test_validate_phone_invalid() -> None:
    with pytest.raises(CustomerValidationError, match="invalid_phone"):
        validate_phone("123")


def test_validate_zip_code() -> None:
    assert validate_zip_code("01310-100") == "01310100"


def test_validate_state() -> None:
    assert validate_state("sp") == "SP"
