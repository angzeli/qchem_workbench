"""Conformer result selection utilities."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from typing import Literal

from qchem_workbench.core.result import CalculationResult


ConformerQuantity = Literal["electronic", "gibbs"]


@dataclass(frozen=True)
class IncompleteConformerResult:
    species_name: str
    conformer_id: str | None
    reason: str
    source_path: str | None

    def to_dict(self) -> dict[str, str | None]:
        return {
            "species_name": self.species_name,
            "conformer_id": self.conformer_id,
            "reason": self.reason,
            "source_path": self.source_path,
        }


@dataclass(frozen=True)
class ConformerSelection:
    species_name: str
    quantity: ConformerQuantity
    selected_conformer_id: str | None
    selected_energy_hartree: float | None
    backend: str | None
    method: str | None
    basis: str | None
    task: str | None
    source_path: str | None
    warnings: tuple[str, ...]
    incomplete_results: tuple[IncompleteConformerResult, ...]

    def to_dict(self) -> dict[str, object]:
        return {
            "species_name": self.species_name,
            "quantity": self.quantity,
            "selected_conformer_id": self.selected_conformer_id,
            "selected_energy_hartree": self.selected_energy_hartree,
            "backend": self.backend,
            "method": self.method,
            "basis": self.basis,
            "task": self.task,
            "source_path": self.source_path,
            "warnings": list(self.warnings),
            "incomplete_results": [
                result.to_dict() for result in self.incomplete_results
            ],
        }


@dataclass(frozen=True)
class ConformerSelectionReport:
    quantity: ConformerQuantity
    allow_mixed: bool
    selections: tuple[ConformerSelection, ...]

    def to_dict(self) -> dict[str, object]:
        return {
            "schema_version": 1,
            "quantity": self.quantity,
            "allow_mixed": self.allow_mixed,
            "selections": [selection.to_dict() for selection in self.selections],
        }


def select_lowest_energy_conformers(
    results: list[CalculationResult],
    quantity: ConformerQuantity,
    *,
    allow_mixed: bool = False,
) -> ConformerSelectionReport:
    energy_field = _energy_field(quantity)
    grouped: dict[str, list[CalculationResult]] = defaultdict(list)
    for result in results:
        grouped[result.species_name].append(result)

    selections = tuple(
        _select_species_conformer(
            species_name,
            grouped[species_name],
            quantity,
            energy_field,
            allow_mixed=allow_mixed,
        )
        for species_name in sorted(grouped)
    )
    return ConformerSelectionReport(
        quantity=quantity,
        allow_mixed=allow_mixed,
        selections=selections,
    )


def _select_species_conformer(
    species_name: str,
    results: list[CalculationResult],
    quantity: ConformerQuantity,
    energy_field: str,
    *,
    allow_mixed: bool,
) -> ConformerSelection:
    candidates: list[CalculationResult] = []
    incomplete: list[IncompleteConformerResult] = []
    for result in results:
        reason = _incomplete_reason(result, energy_field, quantity)
        if reason is None:
            candidates.append(result)
        else:
            incomplete.append(
                IncompleteConformerResult(
                    species_name=result.species_name,
                    conformer_id=result.conformer_id,
                    reason=reason,
                    source_path=_source_path(result),
                )
            )

    warnings: list[str] = []
    settings = {
        (result.backend, result.method, result.basis, result.task)
        for result in candidates
    }
    if len(settings) > 1:
        message = (
            "Candidate conformer results have mixed backend/method/basis/task "
            "settings."
        )
        warnings.append(
            f"{message} Use --allow-mixed to compare them."
            if not allow_mixed
            else f"{message} They were compared because allow_mixed is enabled."
        )
        if not allow_mixed:
            return _empty_selection(species_name, quantity, warnings, incomplete)

    if not candidates:
        warnings.append("No complete conformer results were available for selection.")
        return _empty_selection(species_name, quantity, warnings, incomplete)

    selected = min(
        candidates,
        key=lambda result: (
            getattr(result, energy_field),
            result.conformer_id or "",
            _source_path(result) or "",
        ),
    )
    return ConformerSelection(
        species_name=species_name,
        quantity=quantity,
        selected_conformer_id=selected.conformer_id,
        selected_energy_hartree=getattr(selected, energy_field),
        backend=selected.backend,
        method=selected.method,
        basis=selected.basis,
        task=selected.task,
        source_path=_source_path(selected),
        warnings=tuple(warnings),
        incomplete_results=tuple(incomplete),
    )


def _incomplete_reason(
    result: CalculationResult, energy_field: str, quantity: ConformerQuantity
) -> str | None:
    if result.conformer_id is None:
        return "missing_conformer_id"
    if not result.success:
        return "unsuccessful_result"
    if getattr(result, energy_field) is None:
        return f"missing_{quantity}_energy"
    return None


def _empty_selection(
    species_name: str,
    quantity: ConformerQuantity,
    warnings: list[str],
    incomplete: list[IncompleteConformerResult],
) -> ConformerSelection:
    return ConformerSelection(
        species_name=species_name,
        quantity=quantity,
        selected_conformer_id=None,
        selected_energy_hartree=None,
        backend=None,
        method=None,
        basis=None,
        task=None,
        source_path=None,
        warnings=tuple(warnings),
        incomplete_results=tuple(incomplete),
    )


def _energy_field(quantity: ConformerQuantity) -> str:
    if quantity == "electronic":
        return "electronic_energy_hartree"
    if quantity == "gibbs":
        return "gibbs_free_energy_hartree"
    raise ValueError(f"unsupported conformer selection quantity {quantity!r}")


def _source_path(result: CalculationResult) -> str | None:
    return str(result.source_path) if result.source_path else None
