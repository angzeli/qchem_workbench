from __future__ import annotations

from qchem_workbench.analysis.adsorption import AdsorptionEnergyRow
from qchem_workbench.analysis.quality_checks import QualityCheck
from qchem_workbench.analysis.reactions import ReactionEnergyRow
from qchem_workbench.core.properties import (
    AtomicCharge,
    CalculationProperties,
    DipoleMoment,
    ElectronicExcitation,
    MolecularOrbital,
    OrbitalTable,
    PopulationAnalysis,
    VibrationalMode,
)
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
    assert "## Adsorption energy/free-energy table" in report
    assert "Adsorption energy/free energy (eV)" in report
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


def test_markdown_report_includes_vibrational_property_sections():
    results = [
        CalculationResult(
            species_name="water",
            backend="gaussian",
            method="wb97xd",
            basis="6-31g",
            task="freq",
            success=True,
            properties=CalculationProperties(
                vibrational_modes=(
                    VibrationalMode(
                        frequency_cm1=-50.0,
                        ir_intensity_km_mol=12.0,
                        raman_activity_angstrom4_amu=1.5,
                        is_imaginary=True,
                    ),
                    VibrationalMode(
                        frequency_cm1=1600.0,
                        ir_intensity_km_mol=45.0,
                    ),
                )
            ),
        )
    ]

    report = generate_markdown_report(results)

    assert "## Vibrational summary" in report
    assert "Min frequency (cm^-1)" in report
    assert "Modes with IR intensity (km/mol)" in report
    assert "Modes with Raman activity (angstrom^4/amu)" in report
    assert "## Imaginary-frequency summary" in report
    assert "Most negative frequency (cm^-1)" in report
    assert "| water | 2 | -50 | 1600 | 1 | 2 | 1 |" in report


def test_markdown_report_includes_dipole_and_charge_sections(tmp_path):
    results = [
        CalculationResult(
            species_name="water",
            backend="gaussian",
            method="wb97xd",
            basis="6-31g",
            task="pop",
            success=True,
            source_path=tmp_path / "water.log",
            properties=CalculationProperties(
                dipole_moment=DipoleMoment(
                    x_debye=0.1,
                    y_debye=-0.2,
                    z_debye=1.5,
                    total_debye=1.5166,
                    source_backend="gaussian",
                    source_section_label="Dipole moment (Debye)",
                ),
                population_analyses=(
                    PopulationAnalysis(
                        scheme="Mulliken",
                        atomic_charges=(
                            AtomicCharge(
                                atom_index=1,
                                symbol="O",
                                charge_e=-0.834,
                                scheme="Mulliken",
                            ),
                            AtomicCharge(
                                atom_index=2,
                                symbol="H",
                                charge_e=0.417,
                                scheme="Mulliken",
                            ),
                        ),
                        warnings=("charge count checked",),
                        source_backend="gaussian",
                        source_section_label="Mulliken charges",
                    ),
                ),
            ),
        )
    ]

    report = generate_markdown_report(results)

    assert "## Dipole moment summary" in report
    assert "Total (Debye)" in report
    assert "| water | gaussian | Dipole moment (Debye) | 0.1 | -0.2 | 1.5 | 1.5166 |" in report
    assert "## Population analysis summary" in report
    assert "Charge scheme" in report
    assert "Min charge (e)" in report
    assert "charge count checked" in report


def test_markdown_report_includes_excitation_orbital_and_plot_sections():
    results = [
        CalculationResult(
            species_name="water",
            backend="orca",
            method="b3lyp",
            basis="def2-svp",
            task="tddft",
            success=True,
            homo_ev=-6.1,
            lumo_ev=-1.2,
            gap_ev=4.9,
            metadata={"spectrum_plots": {"ir": "reports/water_ir.png"}},
            properties=CalculationProperties(
                excitations=(
                    ElectronicExcitation(
                        energy_ev=4.0,
                        wavelength_nm=309.960496,
                        oscillator_strength=0.123,
                        state_index=1,
                        transition_description="20 -> 21 0.7",
                        state_label="Singlet-A",
                    ),
                )
            ),
        )
    ]

    report = generate_markdown_report(results)

    assert "## Excitation summary" in report
    assert "Excitation energy (eV)" in report
    assert "Wavelength (nm)" in report
    assert "| water | Singlet-A | 4 | 309.960496 | 0.123 |" in report
    assert "Transition description" in report
    assert "20 -> 21 0.7" in report
    assert "## Orbital summary" in report
    assert "| water | -6.1 | -1.2 | 4.9 |" in report
    assert "## Property plot links" in report
    assert "| water | ir | reports/water_ir.png |" in report


def test_markdown_report_includes_orbital_table_provenance():
    results = [
        CalculationResult(
            species_name="water",
            backend="orca",
            method="b3lyp",
            basis="def2-svp",
            task="single_point",
            success=True,
            homo_ev=-8.0,
            lumo_ev=2.0,
            gap_ev=10.0,
            properties=CalculationProperties(
                orbital_table=OrbitalTable(
                    backend="orca",
                    orbitals=(
                        MolecularOrbital(index=1, energy_ev=-8.0, occupation=2.0),
                        MolecularOrbital(index=2, energy_ev=2.0, occupation=0.0),
                    ),
                    homo_index=1,
                    lumo_index=2,
                    warnings=("synthetic partial table",),
                    source_section_label="Orbital energies",
                )
            ),
        )
    ]

    report = generate_markdown_report(results)

    assert "## Orbital summary" in report
    assert "Orbitals" in report
    assert "Orbital energies" in report
    assert "synthetic partial table" in report


def test_markdown_report_without_properties_remains_clean():
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

    report = generate_markdown_report(results)

    assert "## Vibrational summary" not in report
    assert "## Imaginary-frequency summary" not in report
    assert "## Dipole moment summary" not in report
    assert "## Population analysis summary" not in report
    assert "## Excitation summary" not in report
    assert "## Orbital summary" not in report
    assert "## Property plot links" not in report
