from __future__ import annotations

import pytest

from qchem_workbench.analysis.adsorption import load_adsorption_workflow


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
