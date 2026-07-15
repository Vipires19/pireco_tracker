"""TAC Database — identificação por 8 primeiros dígitos do IMEI."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass
class TacRecord:
    tac: str
    manufacturer_ids: list[str] = field(default_factory=list)
    family_candidates: list[str] = field(default_factory=list)
    model_candidates: list[str] = field(default_factory=list)
    notes: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class TacLookupResult:
    imei: str
    tac: str
    manufacturers: list[str]
    families: list[str]
    models: list[str]
    ambiguous: bool
    notes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


DEFAULT_TAC_RECORDS: list[TacRecord] = [
    TacRecord(
        tac="86768603",
        manufacturer_ids=["concox", "jimi"],
        family_candidates=["GT06"],
        model_candidates=["GT06N"],
        notes="TAC comum em dispositivos Concox/Jimi GT06",
    ),
    TacRecord(
        tac="86655708",
        manufacturer_ids=["concox"],
        family_candidates=["GT06"],
        model_candidates=["GT06N", "GT06E"],
        notes="Possíveis fabricantes Concox; família GT06",
    ),
    TacRecord(
        tac="86833403",
        manufacturer_ids=["jimi"],
        family_candidates=["J16"],
        model_candidates=["J16 Ultra"],
    ),
    TacRecord(
        tac="86833404",
        manufacturer_ids=["jimi"],
        family_candidates=["J16"],
        model_candidates=["J16 Pro"],
    ),
]


def extract_tac(imei: str) -> str:
    digits = "".join(ch for ch in imei if ch.isdigit())
    if len(digits) < 8:
        raise ValueError(f"IMEI inválido para TAC (mínimo 8 dígitos): {imei!r}")
    return digits[:8]


class TacDatabase:
    def __init__(self, records: list[TacRecord] | None = None) -> None:
        self._records: dict[str, TacRecord] = {}
        for record in records or DEFAULT_TAC_RECORDS:
            self.register(record)

    def register(self, record: TacRecord) -> None:
        self._records[record.tac] = record

    def get(self, tac: str) -> TacRecord | None:
        return self._records.get(tac)

    def lookup_imei(self, imei: str) -> TacLookupResult:
        tac = extract_tac(imei)
        record = self._records.get(tac)
        if record is None:
            return TacLookupResult(
                imei=imei,
                tac=tac,
                manufacturers=[],
                families=[],
                models=[],
                ambiguous=False,
                notes=["TAC não encontrado na DKB"],
            )

        manufacturers = list(record.manufacturer_ids)
        families = list(record.family_candidates)
        models = list(record.model_candidates)
        ambiguous = len(manufacturers) > 1 or len(families) > 1 or len(models) > 1
        notes = []
        if record.notes:
            notes.append(record.notes)
        if ambiguous:
            notes.append("Múltiplas possibilidades — requer desambiguação")
        return TacLookupResult(
            imei=imei,
            tac=tac,
            manufacturers=manufacturers,
            families=families,
            models=models,
            ambiguous=ambiguous,
            notes=notes,
        )

    def list(self) -> list[TacRecord]:
        return list(self._records.values())
