from __future__ import annotations

from qchem_workbench.core.properties import (
    AtomicCharge,
    CalculationProperties,
    DipoleMoment,
    ElectronicExcitation,
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
        ),
        atomic_charges=(
            AtomicCharge(atom_index=0, symbol="O", charge_e=-0.4, method="synthetic"),
        ),
    )

    payload = properties.to_dict()
    restored = CalculationProperties.from_dict(payload)

    assert restored.vibrational_modes[0].frequency_cm1 == 1600.0
    assert restored.excitations[0].state_label == "S1"
    assert restored.dipole_moment is not None
    assert restored.dipole_moment.total_debye == 0.374
    assert restored.atomic_charges[0].charge_e == -0.4


def test_missing_property_values_are_allowed():
    properties = CalculationProperties(
        vibrational_modes=(VibrationalMode(frequency_cm1=None),),
        excitations=(ElectronicExcitation(energy_ev=None),),
        dipole_moment=DipoleMoment(),
        atomic_charges=(AtomicCharge(atom_index=1),),
    )

    payload = properties.to_dict()

    assert payload["vibrational_modes"][0]["frequency_cm1"] is None
    assert payload["excitations"][0]["energy_ev"] is None
    assert payload["dipole_moment"]["total_debye"] is None
    assert payload["atomic_charges"][0]["charge_e"] is None


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
