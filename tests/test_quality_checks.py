from __future__ import annotations

from pathlib import Path

from qchem_workbench.analysis.quality_checks import run_quality_checks
from qchem_workbench.core.result import CalculationResult


def _result(**overrides) -> CalculationResult:
    values = {
        "species_name": "water",
        "backend": "gaussian",
        "method": "wb97xd",
        "basis": "6-31g",
        "task": "single_point",
        "success": True,
        "electronic_energy_hartree": -76.0,
        "metadata": {},
        "source_path": Path("outputs/water.log"),
    }
    values.update(overrides)
    return CalculationResult(**values)


def _codes(results):
    return [check.code for check in results]


def test_clean_result_has_no_checks():
    checks = run_quality_checks([_result()])

    assert checks == []


def test_unsuccessful_calculation_check():
    checks = run_quality_checks([_result(success=False)])

    assert "unsuccessful_calculation" in _codes(checks)
    assert (
        next(
            check for check in checks if check.code == "unsuccessful_calculation"
        ).severity
        == "error"
    )


def test_missing_electronic_energy_check():
    checks = run_quality_checks([_result(electronic_energy_hartree=None)])

    assert "missing_electronic_energy" in _codes(checks)


def test_missing_method_and_basis_checks():
    checks = run_quality_checks([_result(method=None, basis=None)])

    assert "missing_method" in _codes(checks)
    assert "missing_basis" in _codes(checks)


def test_imaginary_frequencies_check():
    checks = run_quality_checks(
        [_result(metadata={"negative_frequency_count": 1})]
    )

    assert "imaginary_frequencies_present" in _codes(checks)


def test_missing_thermochemistry_for_frequency_task():
    checks = run_quality_checks([_result(task="freq")])

    assert "missing_frequency_thermochemistry" in _codes(checks)


def test_possible_spin_contamination_when_expected_spin_available():
    checks = run_quality_checks(
        [_result(metadata={"s2_after_annihilation": 2.0})],
        expected_multiplicities={"water": 1},
    )

    assert "possible_spin_contamination" in _codes(checks)


def test_qe_relaxation_not_converged_warning():
    checks = run_quality_checks(
        [
            _result(
                backend="qe",
                method=None,
                basis=None,
                metadata={
                    "relaxation_trajectory": {"relaxation_converged": False}
                },
            )
        ]
    )

    assert "qe_relaxation_not_converged" in _codes(checks)


def test_mixed_method_warning():
    checks = run_quality_checks(
        [
            _result(species_name="water", method="wb97xd"),
            _result(species_name="co2", method="b3lyp", source_path=Path("co2.log")),
        ]
    )

    assert "mixed_backend_method_basis" in _codes(checks)
