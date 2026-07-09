import re
from enum import StrEnum

from app.domains.crm.models import DocumentType


class CustomerValidationError(ValueError):
    pass


def digits_only(value: str) -> str:
    return re.sub(r"\D", "", value)


def validate_document(document: str, document_type: DocumentType | str) -> str:
    cleaned = digits_only(document)
    doc_type = DocumentType(document_type)

    if doc_type == DocumentType.CPF:
        if len(cleaned) != 11:
            raise CustomerValidationError("invalid_cpf")
        if cleaned == cleaned[0] * 11:
            raise CustomerValidationError("invalid_cpf")
        return cleaned

    if len(cleaned) != 14:
        raise CustomerValidationError("invalid_cnpj")
    if cleaned == cleaned[0] * 14:
        raise CustomerValidationError("invalid_cnpj")
    return cleaned


def validate_phone(phone: str, *, required: bool = True) -> str | None:
    if not phone or not phone.strip():
        if required:
            raise CustomerValidationError("invalid_phone")
        return None
    cleaned = digits_only(phone)
    if len(cleaned) < 10 or len(cleaned) > 11:
        raise CustomerValidationError("invalid_phone")
    return cleaned


def validate_zip_code(zip_code: str | None) -> str | None:
    if not zip_code:
        return None
    cleaned = digits_only(zip_code)
    if len(cleaned) != 8:
        raise CustomerValidationError("invalid_zip_code")
    return cleaned


def validate_state(state: str | None) -> str | None:
    if not state:
        return None
    normalized = state.strip().upper()
    if len(normalized) != 2:
        raise CustomerValidationError("invalid_state")
    return normalized
