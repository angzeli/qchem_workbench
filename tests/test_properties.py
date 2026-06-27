from __future__ import annotations

from qchem_workbench.core.properties import (
    AtomicCharge,
    CalculationProperties,
    DipoleMoment,
    ElectronicExcitation,
    ExcitedState,
    MolecularOrbital,
    OrbitalTable,
    PopulationAnalysis,
    VibrationalMode,
    wavelength_nm_from_ev,
)
from qchem_workbench.core.result import CalculationResult


def test_property_serialisation_round_trip():
    properties = CalculationProperties(
        vibrational_modes=(
            VibrationalMode(
                frequency_cm1=1600.0,
                ir_intensity_km_mol=12.5,
                raman_activity_angstrom4_amu=3.0,
                is_imaginary=False,
            ),
        ),
        excitations=(
            ElectronicExcitation(
                energy_ev=3.2,
                wavelength_nm=387.5,
                oscillator_strength=0.12,
                state_label="S1",
            ),
        ),
        dipole_moment=DipoleMoment(
            x_debye=0.1,
            y_debye=0.2,
            z_debye=0.3,
            total_debye=0.374,
            source_backend="gaussian",
            source_section_label="Dipole moment",
        ),
        atomic_charges=(
            AtomicCharge(
                atom_index=0,
                symbol="O",
                charge_e=-0.4,
                scheme="synthetic",
            ),
        ),
        population_analyses=(
            PopulationAnalysis(
                scheme="synthetic",
                atomic_charges=(
                    AtomicCharge(
                        atom_index=0,
                        symbol="O",
                        charge_e=-0.4,
                        scheme="synthetic",
                    ),
                ),
                warnings=("synthetic fixture",),
                source_backend="gaussian",
            ),
        ),
        orbital_table=OrbitalTable(
            backend="gaussian",
            orbitals=(
                MolecularOrbital(
                    index=1,
                    energy_hartree=-0.3,
                    energy_ev=-8.1,
                    occupation=2.0,
                    spin_channel="alpha",
                    symmetry_label="A1",
                ),
            ),
            homo_index=1,
        ),
    )

    payload = properties.to_dict()
    restored = CalculationProperties.from_dict(payload)

    assert restored.vibrational_modes[0].frequency_cm1 == 1600.0
    assert restored.excitations[0].state_label == "S1"
    assert restored.dipole_moment is not None
    assert restored.dipole_moment.total_debye == 0.374
    assert restored.dipole_moment.source_backend == "gaussian"
    assert restored.atomic_charges[0].charge_e == -0.4
    assert restored.population_analyses[0].scheme == "synthetic"
    assert restored.population_analyses[0].warnings == ("synthetic fixture",)
    assert restored.orbital_table is not None
    assert restored.orbital_table.orbitals[0].spin_channel == "alpha"


def test_missing_property_values_are_allowed():
    properties = CalculationProperties(
        vibrational_modes=(VibrationalMode(frequency_cm1=None),),
        excitations=(ElectronicExcitation(energy_ev=None),),
        dipole_moment=DipoleMoment(),
        atomic_charges=(AtomicCharge(atom_index=1),),
        population_analyses=(PopulationAnalysis(scheme="Mulliken"),),
        orbital_table=OrbitalTable(backend="orca"),
    )

    payload = properties.to_dict()

    assert payload["vibrational_modes"][0]["frequency_cm1"] is None
    assert payload["excitations"][0]["energy_ev"] is None
    assert payload["dipole_moment"]["total_debye"] is None
    assert payload["atomic_charges"][0]["charge_e"] is None
    assert payload["population_analyses"][0]["atomic_charges"] == []
    assert payload["orbital_table"]["orbitals"] == []


def test_property_unit_labels_are_explicit():
    mode = VibrationalMode(frequency_cm1=100.0)
    excitation = ElectronicExcitation(energy_ev=2.0, wavelength_nm=620.0)
    dipole = DipoleMoment(total_debye=1.0)
    charge = AtomicCharge(atom_index=0, charge_e=0.1)

    assert mode.to_dict()["frequency_unit"] == "cm^-1"
    assert mode.to_dict()["ir_intensity_unit"] == "km/mol"
    assert mode.to_dict()["raman_activity_unit"] == "angstrom^4/amu"
    assert excitation.to_dict()["energy_unit"] == "eV"
    assert excitation.to_dict()["wavelength_unit"] == "nm"
    assert dipole.to_dict()["unit"] == "Debye"
    assert charge.to_dict()["charge_unit"] == "e"
    assert mode.to_dict()["reduced_mass_unit"] == "amu"
    assert mode.to_dict()["force_constant_unit"] == "mDyne/angstrom"


def test_multiple_population_analysis_schemes_round_trip():
    properties = CalculationProperties(
        population_analyses=(
            PopulationAnalysis(
                scheme="Mulliken",
                atomic_charges=(
                    AtomicCharge(
                        atom_index=1,
                        symbol="H",
                        charge_e=0.2,
                        scheme="Mulliken",
                        atom_label="H1",
                    ),
                ),
            ),
            PopulationAnalysis(
                scheme="Lowdin",
                atomic_charges=(
                    AtomicCharge(
                        atom_index=1,
                        symbol="H",
                        charge_e=0.1,
                        scheme="Lowdin",
                    ),
                ),
            ),
        )
    )

    restored = CalculationProperties.from_dict(properties.to_dict())

    assert [analysis.scheme for analysis in restored.population_analyses] == [
        "Mulliken",
        "Lowdin",
    ]
    assert restored.population_analyses[0].atomic_charges[0].atom_label == "H1"


def test_legacy_flat_atomic_charges_create_population_analysis():
    payload = {
        "atomic_charges": [
            {"atom_index": 1, "symbol": "H", "charge_e": 0.2, "method": "Mulliken"},
            {"atom_index": 2, "symbol": "H", "charge_e": 0.1, "method": "Lowdin"},
        ]
    }

    restored = CalculationProperties.from_dict(payload)

    assert [analysis.scheme for analysis in restored.population_analyses] == [
        "Lowdin",
        "Mulliken",
    ]


def test_alpha_beta_orbital_channels_round_trip():
    properties = CalculationProperties(
        orbital_table=OrbitalTable(
            backend="orca",
            orbitals=(
                MolecularOrbital(index=1, occupation=1.0, spin_channel="alpha"),
                MolecularOrbital(index=1, occupation=0.0, spin_channel="beta"),
            ),
            homo_index=1,
            lumo_index=2,
            warnings=("partial table",),
        )
    )

    restored = CalculationProperties.from_dict(properties.to_dict())

    assert restored.orbital_table is not None
    assert [orbital.spin_channel for orbital in restored.orbital_table.orbitals] == [
        "alpha",
        "beta",
    ]
    assert restored.orbital_table.warnings == ("partial table",)


def test_vibrational_mode_with_imaginary_metadata():
    mode = VibrationalMode(
        mode_index=3,
        frequency_cm1=-100.0,
        ir_intensity_km_mol=5.0,
        reduced_mass_amu=1.1,
        force_constant_mdyne_angstrom=0.2,
        is_imaginary=True,
    )

    restored = VibrationalMode.from_dict(mode.to_dict())

    assert restored.mode_index == 3
    assert restored.is_imaginary is True
    assert restored.reduced_mass_amu == 1.1


def test_excited_state_with_missing_oscillator_strength():
    state = ExcitedState(
        state_index=2,
        energy_ev=3.5,
        wavelength_nm=354.0,
        spin_multiplicity_label="Singlet",
        transition_description="HOMO -> LUMO",
        warnings=("oscillator strength missing",),
    )

    restored = ExcitedState.from_dict(state.to_dict())

    assert restored.oscillator_strength is None
    assert restored.state_label == "Singlet"
    assert restored.transition_description == "HOMO -> LUMO"


def test_result_serialises_properties():
    result = CalculationResult(
        species_name="water",
        backend="gaussian",
        method="b3lyp",
        basis="def2-svp",
        task="freq",
        success=True,
        properties=CalculationProperties(
            vibrational_modes=(VibrationalMode(frequency_cm1=3650.0),)
        ),
    )

    restored = CalculationResult.from_dict(result.to_dict())

    assert restored.properties.vibrational_modes[0].frequency_cm1 == 3650.0


def test_excitation_wavelength_conversion():
    assert wavelength_nm_from_ev(2.0) == 619.9209921660013
