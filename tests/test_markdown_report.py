from __future__ import annotations

from qchem_workbench.analysis.adsorption import AdsorptionEnergyRow
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


def test_method_provenance_consistent_results_include_sources(tmp_path):
    results = [
        CalculationResult(
            species_name="water",
            backend="gaussian",
            method="wb97xd",
            basis="6-31g",
            task="single_point",
            success=True,
            metadata={"solvent": "water"},
            source_path=tmp_path / "water.log",
        )
    ]

    report = generate_markdown_report(results)

    assert "No method/provenance consistency warnings." in report
    assert "Solvent" in report
    assert "water.log" in report


def test_method_provenance_warns_on_mixed_backend():
    results = [
        CalculationResult(
            species_name="A",
            backend="gaussian",
            method="wb97xd",
            basis="6-31g",
            task="single_point",
            success=True,
        ),
        CalculationResult(
            species_name="B",
            backend="pyscf",
            method="wb97xd",
            basis="6-31g",
            task="single_point",
            success=True,
        ),
    ]

    report = generate_markdown_report(results)

    assert "Multiple backends are present in the result set." in report


def test_method_provenance_warns_on_mixed_basis():
    results = [
        CalculationResult(
            species_name="A",
            backend="gaussian",
            method="wb97xd",
            basis="6-31g",
            task="single_point",
            success=True,
        ),
        CalculationResult(
            species_name="B",
            backend="gaussian",
            method="wb97xd",
            basis="def2-svp",
            task="single_point",
            success=True,
        ),
    ]

    report = generate_markdown_report(results)

    assert "Multiple basis sets are present in the result set." in report


def test_reaction_report_warns_when_results_are_mixed():
    results = [
        CalculationResult(
            species_name="A",
            backend="gaussian",
            method="wb97xd",
            basis="6-31g",
            task="single_point",
            success=True,
        ),
        CalculationResult(
            species_name="B",
            backend="pyscf",
            method="b3lyp",
            basis="sto-3g",
            task="single_point",
            success=True,
        ),
    ]
    rows = [
        ReactionEnergyRow(
            reaction_id="r1",
            label=None,
            quantity="delta_e_electronic",
            delta_hartree=0.1,
            delta_ev=2.7,
            delta_kj_mol=262.5,
            complete=True,
            missing_species=(),
        )
    ]

    report = generate_markdown_report(results, reaction_rows=rows)

    assert "Reaction rows are shown with mixed backend/method/basis results" in report


def test_markdown_report_includes_adsorption_table(tmp_path):
    results = [
        CalculationResult(
            species_name="slab_clean",
            backend="qe",
            method="pbe",
            basis="ecutwfc=40",
            task="scf",
            success=True,
            source_path=tmp_path / "slab.out",
        ),
        CalculationResult(
            species_name="co_gas",
            backend="qe",
            method="pbe",
            basis="ecutwfc=40",
            task="scf",
            success=True,
            source_path=tmp_path / "co.out",
        ),
        CalculationResult(
            species_name="slab_co",
            backend="qe",
            method="pbe",
            basis="ecutwfc=40",
            task="scf",
            success=True,
            source_path=tmp_path / "slab_co.out",
        ),
    ]
    rows = [
        AdsorptionEnergyRow(
            system_id="co_on_surface",
            quantity="adsorption_electronic_energy",
            slab_result="slab_clean",
            adsorbate_result="co_gas",
            combined_result="slab_co",
            adsorption_hartree=-0.01,
            adsorption_ev=-0.272,
            adsorption_kj_mol=-26.25,
            complete=True,
            missing=(),
            warnings=(),
            notes="No correction terms applied.",
        )
    ]

    report = generate_markdown_report(results, adsorption_rows=rows)

    assert "## Adsorption system summary" in report
    assert "## Adsorption energy table" in report
    assert "Adsorption energy (eV)" in report
    assert "slab_co.out" in report
    assert "| co_on_surface | adsorption_electronic_energy | True |" in report


def test_adsorption_report_shows_incomplete_rows():
    rows = [
        AdsorptionEnergyRow(
            system_id="co_on_surface",
            quantity="adsorption_gibbs_free_energy",
            slab_result="slab_clean",
            adsorbate_result="co_gas",
            combined_result="slab_co",
            adsorption_hartree=None,
            adsorption_ev=None,
            adsorption_kj_mol=None,
            complete=False,
            missing=("missing_energy:combined:slab_co",),
            warnings=(),
        )
    ]

    report = generate_markdown_report([], adsorption_rows=rows)

    assert "missing_energy:combined:slab_co" in report
    assert "| co_on_surface | adsorption_gibbs_free_energy | False | N/A |" in report


def test_adsorption_report_includes_mixed_method_warning():
    rows = [
        AdsorptionEnergyRow(
            system_id="h_on_surface",
            quantity="adsorption_electronic_energy",
            slab_result="slab_clean",
            adsorbate_result="h_gas",
            combined_result="slab_h",
            adsorption_hartree=-0.02,
            adsorption_ev=-0.544,
            adsorption_kj_mol=-52.51,
            complete=True,
            missing=(),
            warnings=(
                "Adsorption components use mixed backend/method/basis/task/solvent settings.",
            ),
        )
    ]

    report = generate_markdown_report([], adsorption_rows=rows)

    assert "Adsorption row h_on_surface" in report
    assert "mixed backend/method/basis/task/solvent" in report
