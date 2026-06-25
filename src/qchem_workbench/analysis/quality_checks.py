"""Generic calculation quality checks."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Literal

from qchem_workbench.core.result import CalculationResult
from qchem_workbench.results.store import result_identity


Severity = Literal["info", "warning", "error"]


@dataclass(frozen=True)
class QualityCheck:
    code: str
    severity: Severity
    message: str
    result_identifier: str

    def to_dict(self) -> dict[str, str]:
        return {
            "code": self.code,
            "severity": self.severity,
            "message": self.message,
            "result_identifier": self.result_identifier,
        }


def run_quality_checks(
    results: list[CalculationResult],
    expected_multiplicities: dict[str, int] | None = None,
) -> list[QualityCheck]:
    checks: list[QualityCheck] = []
    expected_multiplicities = expected_multiplicities or {}

    for result in results:
        checks.extend(_check_single_result(result, expected_multiplicities))

    checks.extend(_check_result_set_consistency(results))
    return checks


def _check_single_result(
    result: CalculationResult,
    expected_multiplicities: dict[str, int],
) -> list[QualityCheck]:
    checks: list[QualityCheck] = []
    identifier = _result_identifier(result)

    if not result.success:
        checks.append(
            QualityCheck(
                code="unsuccessful_calculation",
                severity="error",
                message="Calculation did not report successful completion.",
                result_identifier=identifier,
            )
        )
    if result.electronic_energy_hartree is None:
        checks.append(
            QualityCheck(
                code="missing_electronic_energy",
                severity="warning",
                message="Electronic energy is missing.",
                result_identifier=identifier,
            )
        )
    if result.method is None:
        checks.append(
            QualityCheck(
                code="missing_method",
                severity="warning",
                message="Calculation method is missing.",
                result_identifier=identifier,
            )
        )
    if result.basis is None:
        checks.append(
            QualityCheck(
                code="missing_basis",
                severity="warning",
                message="Basis set is missing.",
                result_identifier=identifier,
            )
        )

    negative_count = result.metadata.get("negative_frequency_count")
    if isinstance(negative_count, int) and negative_count > 0:
        checks.append(
            QualityCheck(
                code="imaginary_frequencies_present",
                severity="warning",
                message=(
                    f"{negative_count} negative frequency value(s) were parsed; "
                    "no transition-state identity is inferred."
                ),
                result_identifier=identifier,
            )
        )

    if _is_frequency_style_result(result) and not _has_thermochemistry(result):
        checks.append(
            QualityCheck(
                code="missing_frequency_thermochemistry",
                severity="warning",
                message="Frequency-style result is missing thermochemistry values.",
                result_identifier=identifier,
            )
        )

    spin_check = _spin_contamination_check(result, expected_multiplicities)
    if spin_check is not None:
        checks.append(spin_check)

    return checks


def _check_result_set_consistency(results: list[CalculationResult]) -> list[QualityCheck]:
    if len(results) < 2:
        return []

    methods = {(result.backend, result.method, result.basis) for result in results}
    if len(methods) <= 1:
        return []

    return [
        QualityCheck(
            code="mixed_backend_method_basis",
            severity="warning",
            message="Result set contains mixed backend/method/basis combinations.",
            result_identifier="result-set",
        )
    ]


def _spin_contamination_check(
    result: CalculationResult,
    expected_multiplicities: dict[str, int],
) -> QualityCheck | None:
    expected_multiplicity = expected_multiplicities.get(result.species_name)
    if expected_multiplicity is None:
        expected_multiplicity = result.metadata.get("expected_multiplicity")
    if not isinstance(expected_multiplicity, int) or expected_multiplicity <= 0:
        return None

    observed_s2 = result.metadata.get("s2_after_annihilation")
    if observed_s2 is None:
        observed_s2 = result.metadata.get("s2_before_annihilation")
    if not isinstance(observed_s2, (int, float)):
        return None

    spin = (expected_multiplicity - 1) / 2
    expected_s2 = spin * (spin + 1)
    if abs(float(observed_s2) - expected_s2) <= 0.5:
        return None

    return QualityCheck(
        code="possible_spin_contamination",
        severity="warning",
        message=(
            f"Observed S**2={observed_s2:.4g} differs from expected "
            f"S(S+1)={expected_s2:.4g} for multiplicity {expected_multiplicity}."
        ),
        result_identifier=_result_identifier(result),
    )


def _is_frequency_style_result(result: CalculationResult) -> bool:
    if result.task in {"freq", "opt_freq"}:
        return True
    route = result.metadata.get("route")
    if not isinstance(route, str):
        return False
    return bool(re.search(r"(^|[\s#])(?:opt\s+)?freq([\s=(),]|$)", route.lower()))


def _has_thermochemistry(result: CalculationResult) -> bool:
    return any(
        value is not None
        for value in (
            result.zero_point_correction_hartree,
            result.thermal_correction_energy_hartree,
            result.thermal_correction_enthalpy_hartree,
            result.thermal_correction_gibbs_hartree,
            result.sum_electronic_zero_point_energy_hartree,
            result.sum_electronic_thermal_free_energy_hartree,
        )
    )


def _result_identifier(result: CalculationResult) -> str:
    return "|".join(
        "" if value is None else str(value) for value in result_identity(result)
    )
