from __future__ import annotations

import pytest

from qchem_workbench.projects.manifest import load_project_manifest


def test_load_valid_project_manifest(tmp_path):
    species_path = tmp_path / "species.yaml"
    species_path.write_text("schema_version: 1\nspecies: []\n", encoding="utf-8")
    pathway_path = tmp_path / "pathway.yaml"
    pathway_path.write_text("schema_version: 1\nreactions: []\n", encoding="utf-8")
    manifest_path = tmp_path / "qchem_project.yaml"
    manifest_path.write_text(
        "schema_version: 1\n"
        "project:\n"
        "  name: demo\n"
        "  species: species.yaml\n"
        "  results: results/results.json\n"
        "  reports: reports/report.md\n"
        "  reaction_table: results/reaction_table.csv\n"
        "  reaction_quantity: electronic\n"
        "  inputs: gaussian_inputs\n"
        "  outputs: outputs\n"
        "  pathways:\n"
        "    - pathway.yaml\n"
        "  backend_mode: gaussian\n"
        "  calculation:\n"
        "    backend: gaussian\n"
        "    method: wb97xd\n"
        "    basis: 6-31g\n"
        "    task: single_point\n"
        "    solvent: water\n"
        "    route_keywords: [nosymm]\n"
        "  steps: [render_gaussian, report]\n",
        encoding="utf-8",
    )

    manifest = load_project_manifest(manifest_path)
    spec = manifest.calculation.to_spec(default_backend=manifest.backend_mode)

    assert manifest.name == "demo"
    assert manifest.species_path == species_path
    assert manifest.results_path == tmp_path / "results" / "results.json"
    assert manifest.report_path == tmp_path / "reports" / "report.md"
    assert manifest.reaction_table_path == tmp_path / "results" / "reaction_table.csv"
    assert manifest.reaction_quantity == "electronic"
    assert manifest.inputs_dir == tmp_path / "gaussian_inputs"
    assert manifest.outputs_dir == tmp_path / "outputs"
    assert manifest.pathway_paths == (pathway_path,)
    assert manifest.steps == ("render_gaussian", "report")
    assert manifest.calculation.route_keywords == ("nosymm",)
    assert spec.backend == "gaussian"
    assert spec.method == "wb97xd"
    assert spec.basis == "6-31g"
    assert spec.task == "single_point"
    assert spec.solvent == "water"


def test_manifest_missing_referenced_species_file(tmp_path):
    manifest_path = tmp_path / "qchem_project.yaml"
    manifest_path.write_text(
        "schema_version: 1\n"
        "project:\n"
        "  name: demo\n"
        "  species: missing_species.yaml\n",
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="referenced species file does not exist"):
        load_project_manifest(manifest_path)


def test_manifest_missing_referenced_pathway_file(tmp_path):
    species_path = tmp_path / "species.yaml"
    species_path.write_text("schema_version: 1\nspecies: []\n", encoding="utf-8")
    manifest_path = tmp_path / "qchem_project.yaml"
    manifest_path.write_text(
        "schema_version: 1\n"
        "project:\n"
        "  name: demo\n"
        "  species: species.yaml\n"
        "  pathways: [missing_pathway.yaml]\n",
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="referenced pathways file does not exist"):
        load_project_manifest(manifest_path)


def test_manifest_unsupported_schema_version(tmp_path):
    manifest_path = tmp_path / "qchem_project.yaml"
    manifest_path.write_text(
        "schema_version: 99\n"
        "project:\n"
        "  name: demo\n"
        "  species: species.yaml\n",
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="unsupported schema_version"):
        load_project_manifest(manifest_path)
