"""Explicit correction-term bookkeeping for free-energy analysis."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable


CORRECTION_TARGET_TYPES = ("species", "reaction", "adsorption_system")


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
        if isinstance(self.value_eV, bool) or not isinstance(self.value_eV, (int, float)):
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
