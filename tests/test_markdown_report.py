from __future__ import annotations

from qchem_workbench.analysis.quality_checks import QualityCheck
from qchem_workbench.analysis.reactions import ReactionEnergyRow
from qchem_workbench.core.result import CalculationResult
from qchem_workbench.core.species import Species
from qchem_workbench.reports.markdown import generate_markdown_report


def test_markdown_report_generation(tmp_path):
    species = [
        Species(
            name="water",
            formula="H2O",
            charge=0,
            multiplicity=1,
            geometry_path=tmp_path / "water.xyz",
        )
    ]
    results = [
        CalculationResult(
            species_name="water",
            backend="gaussian",
            method="wb97xd",
            basis="6-31g",
            task="single_point",
            success=True,
            electronic_energy_hartree=-76.0,
            gibbs_free_energy_hartree=-75.9,
            source_path=tmp_path / "water.log",
        )
    ]

    report = generate_markdown_report(results, species=species)

    assert "## Project summary" in report
    assert "## Species table" in report
    assert "## Calculation result table" in report
    assert "Electronic energy (Hartree)" in report
    assert "Gibbs free energy (Hartree)" in report
    assert "| water | H2O | 0 | 1 |" in report


def test_markdown_report_shows_missing_values():
    results = [
        CalculationResult(
            species_name="water",
            backend="gaussian",
            method=None,
            basis=None,
            task="single_point",
            success=True,
        )
    ]

    report = generate_markdown_report(results)

    assert "N/A" in report
    assert "| water | gaussian | N/A | N/A | single_point |" in report


def test_markdown_report_includes_warnings_section():
    results = [
        CalculationResult(
            species_name="water",
            backend="gaussian",
            method="wb97xd",
            basis="6-31g",
            task="single_point",
            success=True,
        )
    ]
    checks = [
        QualityCheck(
            code="missing_electronic_energy",
            severity="warning",
            message="No electronic energy was parsed.",
            result_identifier="water",
        )
    ]

    report = generate_markdown_report(results, quality_checks=checks)

    assert "## Quality-check summary" in report
    assert "| warning | missing_electronic_energy | water |" in report
    assert "No electronic energy was parsed." in report


def test_markdown_report_includes_reaction_table_with_units():
    results = [
        CalculationResult(
            species_name="A",
            backend="gaussian",
            method="wb97xd",
            basis="6-31g",
            task="single_point",
            success=True,
            electronic_energy_hartree=-1.0,
        )
    ]
    rows = [
        ReactionEnergyRow(
            reaction_id="r1",
            label="A to B",
            quantity="delta_e_electronic",
            delta_hartree=None,
            delta_ev=None,
            delta_kj_mol=None,
            complete=False,
            missing_species=("B",),
            notes="Sign convention: products minus reactants.",
        )
    ]

    report = generate_markdown_report(results, reaction_rows=rows)

    assert "## Reaction energy table" in report
    assert "Delta (eV)" in report
    assert "| r1 | A to B | delta_e_electronic | False | N/A | N/A | N/A | B |" in report
