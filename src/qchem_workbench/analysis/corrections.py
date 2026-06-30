"""Explicit correction-term bookkeeping for free-energy analysis."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable


CORRECTION_TARGET_TYPES = ("species", "reaction", "adsorption_system")
CORRECTION_LEDGER_CATEGORIES = (
    "zpe",
    "thermal",
    "entropy",
    "solvation",
    "standard_state",
    "pressure",
    "concentration",
    "pH",
    "potential",
    "reference",
    "user",
    "other",
)
CORRECTION_LEDGER_SIGNS = ("positive", "negative")
CORRECTION_LEDGER_SIGN_ALIASES = {
    "+": "positive",
    "add": "positive",
    "positive": "positive",
    "-": "negative",
    "subtract": "negative",
    "negative": "negative",
}


@dataclass(frozen=True)
class CorrectionTerm:
    label: str
    value_eV: float
    sign_convention: str
    source: str | None = None
    note: str | None = None

    def __post_init__(self) -> None:
        if not self.label.strip():
            raise ValueError("correction label cannot be empty")
        if not self.sign_convention.strip():
            raise ValueError("correction sign_convention cannot be empty")
        if isinstance(self.value_eV, bool) or not isinstance(
            self.value_eV, (int, float)
        ):
            raise ValueError("correction value_eV must be numeric")

    @property
    def warnings(self) -> tuple[str, ...]:
        if self.source:
            return ()
        return (
            f"Correction term {self.label!r} has no source; document whether it is "
            "user-provided or derived from an explicit parsed field.",
        )


@dataclass(frozen=True)
class CorrectionLedgerEntry:
    """One visible term in an auditable correction ledger."""

    term_id: str
    label: str
    value: float
    unit: str
    sign: str
    applies_to: str
    source: str | None
    provenance: dict[str, object] = field(default_factory=dict)
    notes: str | None = None
    category: str = "user"

    def __post_init__(self) -> None:
        object.__setattr__(self, "term_id", _required_text(self.term_id, "term_id"))
        object.__setattr__(self, "label", _required_text(self.label, "label"))
        object.__setattr__(self, "unit", _required_text(self.unit, "unit"))
        object.__setattr__(
            self,
            "applies_to",
            _required_text(self.applies_to, "applies_to"),
        )
        if isinstance(self.value, bool) or not isinstance(self.value, (int, float)):
            raise ValueError("correction ledger entry value must be numeric")
        object.__setattr__(self, "value", float(self.value))
        object.__setattr__(self, "sign", _normalise_sign(self.sign))
        if self.category not in CORRECTION_LEDGER_CATEGORIES:
            allowed = ", ".join(CORRECTION_LEDGER_CATEGORIES)
            raise ValueError(f"correction ledger category must be one of: {allowed}")
        object.__setattr__(self, "provenance", dict(self.provenance))

    @property
    def signed_value(self) -> float:
        return self.value if self.sign == "positive" else -self.value

    @property
    def warnings(self) -> tuple[str, ...]:
        if self.source:
            return ()
        return (f"Correction ledger term {self.term_id!r} has no source.",)

    def to_dict(self) -> dict[str, object]:
        return {
            "term_id": self.term_id,
            "label": self.label,
            "value": self.value,
            "unit": self.unit,
            "sign": self.sign,
            "applies_to": self.applies_to,
            "source": self.source,
            "provenance": dict(self.provenance),
            "notes": self.notes,
            "category": self.category,
        }

    @classmethod
    def from_dict(cls, data: dict[str, object]) -> "CorrectionLedgerEntry":
        return cls(
            term_id=str(data.get("term_id", "")),
            label=str(data.get("label", "")),
            value=data.get("value"),
            unit=str(data.get("unit", "")),
            sign=str(data.get("sign", "")),
            applies_to=str(data.get("applies_to", "")),
            source=_optional_text(data.get("source")),
            provenance=dict(data.get("provenance", {})),
            notes=_optional_text(data.get("notes")),
            category=str(data.get("category", "user")),
        )


@dataclass(frozen=True)
class CorrectionLedger:
    """A complete, visible ledger of correction terms."""

    entries: tuple[CorrectionLedgerEntry, ...] = ()

    def __post_init__(self) -> None:
        entries = tuple(self.entries)
        term_ids = [entry.term_id for entry in entries]
        duplicates = sorted(
            term_id for term_id in set(term_ids) if term_ids.count(term_id) > 1
        )
        if duplicates:
            raise ValueError(
                "duplicate correction ledger term_id values: "
                + ", ".join(duplicates)
            )
        object.__setattr__(self, "entries", entries)

    @property
    def warnings(self) -> tuple[str, ...]:
        return tuple(warning for entry in self.entries for warning in entry.warnings)

    def total(self, unit: str | None = None) -> float:
        target_unit = unit or _single_unit(self.entries)
        if target_unit is None:
            return 0.0
        for entry in self.entries:
            if entry.unit != target_unit:
                raise ValueError(
                    f"correction ledger unit mismatch: {entry.term_id} uses "
                    f"{entry.unit!r}, expected {target_unit!r}"
                )
        return sum(entry.signed_value for entry in self.entries)

    def to_dict(self) -> dict[str, object]:
        return {"entries": [entry.to_dict() for entry in self.entries]}

    @classmethod
    def from_dict(cls, data: dict[str, object]) -> "CorrectionLedger":
        entries = data.get("entries", [])
        if not isinstance(entries, list):
            raise ValueError("correction ledger entries must be a list")
        return cls(tuple(CorrectionLedgerEntry.from_dict(entry) for entry in entries))


@dataclass(frozen=True)
class CorrectedLedgerValue:
    """A corrected value with all visible correction terms preserved."""

    base_value: float | None
    unit: str
    correction_total: float
    corrected_value: float | None
    ledger: CorrectionLedger
    warnings: tuple[str, ...]

    def to_dict(self) -> dict[str, object]:
        return {
            "base_value": self.base_value,
            "unit": self.unit,
            "correction_total": self.correction_total,
            "corrected_value": self.corrected_value,
            "ledger": self.ledger.to_dict(),
            "warnings": list(self.warnings),
        }


@dataclass(frozen=True)
class CorrectionAttachment:
    target_type: str
    target_id: str
    terms: tuple[CorrectionTerm, ...]

    def __post_init__(self) -> None:
        if self.target_type not in CORRECTION_TARGET_TYPES:
            allowed = ", ".join(CORRECTION_TARGET_TYPES)
            raise ValueError(f"correction target_type must be one of: {allowed}")
        if not self.target_id.strip():
            raise ValueError("correction target_id cannot be empty")


@dataclass(frozen=True)
class CorrectionTableRow:
    target_type: str
    target_id: str
    label: str
    value_eV: float
    sign_convention: str
    source: str | None
    note: str | None


@dataclass(frozen=True)
class CorrectedEnergy:
    target_type: str
    target_id: str
    base_value_eV: float | None
    correction_terms: tuple[CorrectionTerm, ...]
    corrected_value_eV: float | None
    warnings: tuple[str, ...]

    @property
    def correction_total_eV(self) -> float:
        return sum(term.value_eV for term in self.correction_terms)

    @property
    def correction_table(self) -> tuple[CorrectionTableRow, ...]:
        return tuple(
            CorrectionTableRow(
                target_type=self.target_type,
                target_id=self.target_id,
                label=term.label,
                value_eV=term.value_eV,
                sign_convention=term.sign_convention,
                source=term.source,
                note=term.note,
            )
            for term in self.correction_terms
        )


def attach_corrections(
    target_type: str, target_id: str, terms: Iterable[CorrectionTerm]
) -> CorrectionAttachment:
    return CorrectionAttachment(
        target_type=target_type,
        target_id=target_id,
        terms=tuple(terms),
    )


def apply_corrections(
    base_value_eV: float | None, attachment: CorrectionAttachment
) -> CorrectedEnergy:
    warnings = tuple(
        warning for term in attachment.terms for warning in term.warnings
    )
    if base_value_eV is None:
        return CorrectedEnergy(
            target_type=attachment.target_type,
            target_id=attachment.target_id,
            base_value_eV=None,
            correction_terms=attachment.terms,
            corrected_value_eV=None,
            warnings=warnings,
        )

    if isinstance(base_value_eV, bool) or not isinstance(base_value_eV, (int, float)):
        raise ValueError("base_value_eV must be numeric or None")
    return CorrectedEnergy(
        target_type=attachment.target_type,
        target_id=attachment.target_id,
        base_value_eV=float(base_value_eV),
        correction_terms=attachment.terms,
        corrected_value_eV=float(base_value_eV)
        + sum(term.value_eV for term in attachment.terms),
        warnings=warnings,
    )


def apply_correction_ledger(
    base_value: float | None,
    unit: str,
    ledger: CorrectionLedger,
) -> CorrectedLedgerValue:
    """Apply a visible correction ledger without hidden defaults."""

    target_unit = _required_text(unit, "unit")
    correction_total = ledger.total(target_unit)
    if base_value is None:
        corrected_value = None
        parsed_base = None
    else:
        if isinstance(base_value, bool) or not isinstance(base_value, (int, float)):
            raise ValueError("base_value must be numeric or None")
        parsed_base = float(base_value)
        corrected_value = parsed_base + correction_total
    return CorrectedLedgerValue(
        base_value=parsed_base,
        unit=target_unit,
        correction_total=correction_total,
        corrected_value=corrected_value,
        ledger=ledger,
        warnings=ledger.warnings,
    )


def _required_text(value: str, field_name: str) -> str:
    text = str(value).strip()
    if not text:
        raise ValueError(f"correction ledger {field_name} cannot be empty")
    return text


def _optional_text(value: object) -> str | None:
    if value is None:
        return None
    return str(value)


def _normalise_sign(sign: str) -> str:
    try:
        return CORRECTION_LEDGER_SIGN_ALIASES[str(sign).strip().lower()]
    except KeyError as exc:
        allowed = ", ".join(CORRECTION_LEDGER_SIGNS)
        raise ValueError(f"correction ledger sign must be one of: {allowed}") from exc


def _single_unit(entries: tuple[CorrectionLedgerEntry, ...]) -> str | None:
    units = {entry.unit for entry in entries}
    if not units:
        return None
    if len(units) != 1:
        raise ValueError("correction ledger contains multiple units")
    return next(iter(units))
