from __future__ import annotations

import pytest

from qchem_workbench.analysis.adsorption import (
    adsorption_electronic_energy_table,
    adsorption_gibbs_free_energy_table,
    load_adsorption_workflow,
)
from qchem_workbench.core.result import CalculationResult
from qchem_workbench.core.units import HARTREE_TO_EV


def _result(
    name: str,
    electronic: float | None,
    *,
    gibbs: float | None = None,
    method: str = "pbe",
) -> CalculationResult:
    return CalculationResult(
        species_name=name,
        backend="qe",
        method=method,
        basis="ecutwfc=40",
        task="scf",
        success=True,
        electronic_energy_hartree=electronic,
        gibbs_free_energy_hartree=gibbs,
    )


def _workflow(tmp_path):
    path = tmp_path / "adsorption.yaml"
    path.write_text(
        "schema_version: 1\n"
        "adsorption_systems:\n"
        "  - id: co_on_surface\n"
        "    slab_result: slab_clean\n"
        "    adsorbate_result: co_gas\n"
        "    combined_result: slab_co\n",
        encoding="utf-8",
    )
    return load_adsorption_workflow(path)


def test_load_valid_adsorption_system(tmp_path):
    path = tmp_path / "adsorption.yaml"
    path.write_text(
        "schema_version: 1\n"
        "clean_slabs:\n"
        "  - id: slab_clean\n"
        "isolated_adsorbates:\n"
        "  - id: co_gas\n"
        "slab_adsorbates:\n"
        "  - id: slab_co\n"
        "adsorption_systems:\n"
        "  - id: co_on_surface\n"
        "    slab_result: slab_clean\n"
        "    adsorbate_result: co_gas\n"
        "    combined_result: slab_co\n"
        "    notes: Example only\n",
        encoding="utf-8",
    )

    workflow = load_adsorption_workflow(path)

    system = workflow.adsorption_systems[0]
    assert system.id == "co_on_surface"
    assert system.slab_result == "slab_clean"
    assert system.adsorbate_result == "co_gas"
    assert system.combined_result == "slab_co"
    assert system.notes == "Example only"


def test_adsorption_missing_result_reference_is_error(tmp_path):
    path = tmp_path / "adsorption.yaml"
    path.write_text(
        "schema_version: 1\n"
        "clean_slabs:\n"
        "  - id: slab_clean\n"
        "isolated_adsorbates:\n"
        "  - id: co_gas\n"
        "slab_adsorbates:\n"
        "  - id: slab_co\n"
        "adsorption_systems:\n"
        "  - id: co_on_surface\n"
        "    slab_result: missing_slab\n"
        "    adsorbate_result: co_gas\n"
        "    combined_result: slab_co\n",
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="missing.*slab_result"):
        load_adsorption_workflow(path)


def test_adsorption_duplicate_ids_are_errors(tmp_path):
    path = tmp_path / "adsorption.yaml"
    path.write_text(
        "schema_version: 1\n"
        "adsorption_systems:\n"
        "  - id: co_on_surface\n"
        "    slab_result: slab_clean\n"
        "    adsorbate_result: co_gas\n"
        "    combined_result: slab_co\n"
        "  - id: co_on_surface\n"
        "    slab_result: slab_clean\n"
        "    adsorbate_result: co_gas\n"
        "    combined_result: slab_co\n",
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="duplicate adsorption system id"):
        load_adsorption_workflow(path)


def test_adsorption_missing_schema_version_is_error(tmp_path):
    path = tmp_path / "adsorption.yaml"
    path.write_text("adsorption_systems: []\n", encoding="utf-8")

    with pytest.raises(ValueError, match="missing schema_version"):
        load_adsorption_workflow(path)


def test_adsorption_unsupported_schema_version_is_error(tmp_path):
    path = tmp_path / "adsorption.yaml"
    path.write_text(
        "schema_version: 99\nadsorption_systems: []\n",
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="unsupported schema_version"):
        load_adsorption_workflow(path)


def test_adsorption_electronic_energy(tmp_path):
    row = adsorption_electronic_energy_table(
        _workflow(tmp_path),
        [
            _result("slab_clean", -100.0),
            _result("co_gas", -10.0),
            _result("slab_co", -111.0),
        ],
    )[0]

    assert row.complete is True
    assert row.quantity == "adsorption_electronic_energy"
    assert row.adsorption_hartree == pytest.approx(-1.0)
    assert row.adsorption_ev == pytest.approx(-1.0 * HARTREE_TO_EV)
    assert row.missing == ()


def test_adsorption_energy_missing_component(tmp_path):
    row = adsorption_electronic_energy_table(
        _workflow(tmp_path),
        [
            _result("slab_clean", -100.0),
            _result("co_gas", -10.0),
        ],
    )[0]

    assert row.complete is False
    assert row.adsorption_hartree is None
    assert row.missing == ("missing_result:combined:slab_co",)


def test_adsorption_energy_mixed_method_warning(tmp_path):
    row = adsorption_electronic_energy_table(
        _workflow(tmp_path),
        [
            _result("slab_clean", -100.0, method="pbe"),
            _result("co_gas", -10.0, method="pbe0"),
            _result("slab_co", -111.0, method="pbe"),
        ],
    )[0]

    assert row.complete is True
    assert any("mixed backend/method" in warning for warning in row.warnings)


def test_adsorption_gibbs_missing_value_is_incomplete(tmp_path):
    row = adsorption_gibbs_free_energy_table(
        _workflow(tmp_path),
        [
            _result("slab_clean", -100.0, gibbs=-100.1),
            _result("co_gas", -10.0, gibbs=-10.1),
            _result("slab_co", -111.0, gibbs=None),
        ],
    )[0]

    assert row.quantity == "adsorption_gibbs_free_energy"
    assert row.complete is False
    assert row.missing == ("missing_energy:combined:slab_co",)
