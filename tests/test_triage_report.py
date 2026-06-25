from __future__ import annotations

from qchem_workbench.core.result import CalculationResult
from qchem_workbench.reports.triage import (
    classify_triage_results,
    generate_failed_jobs_markdown,
)


def test_triage_classifies_complete_result():
    result = CalculationResult(
        species_name="water",
        backend="gaussian",
        method="wb97xd",
        basis="6-31g",
        task="single_point",
        success=True,
        electronic_energy_hartree=-76.0,
        metadata={"normal_termination": True},
    )

    classified = classify_triage_results([result])

    assert classified["complete"] == [result]
    assert classified["missing_energy"] == []


def test_triage_classifies_incomplete_no_normal_termination():
    result = CalculationResult(
        species_name="failed",
        backend="gaussian",
        method="wb97xd",
        basis="6-31g",
        task="single_point",
        success=False,
        electronic_energy_hartree=-1.0,
        metadata={"normal_termination": False},
    )

    classified = classify_triage_results([result])

    assert classified["incomplete_no_normal_termination"] == [result]
    assert classified["complete"] == []


def test_triage_classifies_missing_energy():
    result = CalculationResult(
        species_name="missing-energy",
        backend="gaussian",
        method="wb97xd",
        basis="6-31g",
        task="single_point",
        success=True,
    )

    classified = classify_triage_results([result])

    assert classified["missing_energy"] == [result]


def test_triage_classifies_imaginary_frequencies():
    result = CalculationResult(
        species_name="freq",
        backend="gaussian",
        method="wb97xd",
        basis="6-31g",
        task="freq",
        success=True,
        electronic_energy_hartree=-1.0,
        metadata={"negative_frequency_count": 2},
    )

    classified = classify_triage_results([result])

    assert classified["imaginary_frequencies"] == [result]


def test_triage_classifies_spin_warning():
    result = CalculationResult(
        species_name="open-shell",
        backend="gaussian",
        method="ub3lyp",
        basis="6-31g",
        task="single_point",
        success=True,
        electronic_energy_hartree=-1.0,
        warnings=["Possible spin contamination from S**2 metadata."],
    )

    classified = classify_triage_results([result])

    assert classified["spin_warning"] == [result]
    assert classified["parser_warning"] == [result]


def test_triage_classifies_parser_warning():
    result = CalculationResult(
        species_name="warned",
        backend="gaussian",
        method="wb97xd",
        basis="6-31g",
        task="single_point",
        success=True,
        electronic_energy_hartree=-1.0,
        warnings=["Parser raised exception for one field."],
    )

    classified = classify_triage_results([result])

    assert classified["parser_warning"] == [result]
    assert classified["complete"] == []


def test_failed_jobs_markdown_is_conservative():
    report = generate_failed_jobs_markdown(
        [
            CalculationResult(
                species_name="missing-energy",
                backend="gaussian",
                method="wb97xd",
                basis="6-31g",
                task="single_point",
                success=True,
            )
        ]
    )

    assert "# Failed job triage" in report
    assert "Do not substitute or estimate missing energy values." in report
    assert "does not infer missing scientific quantities" in report
    assert "Electronic energy (Hartree)" in report
