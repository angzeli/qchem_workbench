from __future__ import annotations

import json
from pathlib import Path

from qchem_workbench.core.calculation import CalculationSpec
from qchem_workbench.core.result import CalculationResult


def test_calculation_spec_construction():
    spec = CalculationSpec(
        backend="example",
        method="b3lyp",
        basis="sto-3g",
        task="single_point",
        solvent=None,
        charge=0,
        multiplicity=1,
        keywords={"max_cycle": 50},
    )

    assert spec.to_dict()["backend"] == "example"
    assert spec.to_dict()["keywords"] == {"max_cycle": 50}


def test_result_serialisation():
    result = CalculationResult(
        species_name="water",
        backend="example",
        method="b3lyp",
        basis="sto-3g",
        task="single_point",
        success=True,
        electronic_energy_hartree=-1.0,
        metadata={"n_atoms": 3},
        source_path=Path("outputs/water.out"),
    )

    payload = result.to_dict()
    json.dumps(payload)

    assert payload["electronic_energy_hartree"] == -1.0
    assert payload["gibbs_free_energy_hartree"] is None
    assert payload["source_path"] == "outputs/water.out"


def test_warnings_default_to_empty_list():
    first = CalculationResult(
        species_name="a",
        backend="example",
        method="b3lyp",
        basis=None,
        task="single_point",
        success=True,
    )
    second = CalculationResult(
        species_name="b",
        backend="example",
        method="b3lyp",
        basis=None,
        task="single_point",
        success=True,
    )

    first.warnings.append("synthetic warning")

    assert second.warnings == []
