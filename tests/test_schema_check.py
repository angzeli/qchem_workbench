from __future__ import annotations

from qchem_workbench.core.result import CalculationResult
from qchem_workbench.results.store import save_result_collection
from qchem_workbench.schema import check_schema_file


def test_schema_check_detects_supported_file_types(tmp_path):
    paths = _schema_files(tmp_path)

    reports = {name: check_schema_file(path) for name, path in paths.items()}

    assert reports["species"].file_type == "species_registry"
    assert reports["result_store"].file_type == "result_store"
    assert reports["pathway"].file_type == "pathway"
    assert reports["project_manifest"].file_type == "project_manifest"
    assert reports["campaign"].file_type == "campaign"
    assert reports["microkinetic_model"].file_type == "microkinetic_model"
    assert all(report.schema_version == 1 for report in reports.values())
    assert all(report.valid for report in reports.values())


def test_schema_check_reports_unsupported_version(tmp_path):
    path = tmp_path / "species.yaml"
    path.write_text("schema_version: 99\nspecies: []\n", encoding="utf-8")

    report = check_schema_file(path)

    assert report.file_type == "species_registry"
    assert report.schema_version == 99
    assert report.valid is False
    assert "unsupported schema_version 99" in report.problems[0]
    assert report.migration.required is True
    assert report.migration.available is False


def test_schema_check_dry_run_migration_does_not_rewrite_file(tmp_path):
    paths = _schema_files(tmp_path)
    species_path = paths["species"]
    before = species_path.read_text(encoding="utf-8")

    report = check_schema_file(species_path, write=False)
    after_dry_run = species_path.read_text(encoding="utf-8")
    write_report = check_schema_file(species_path, write=True)
    after_write = species_path.read_text(encoding="utf-8")

    assert report.migration.message == "No migration required."
    assert report.migration.changed is False
    assert after_dry_run == before
    assert write_report.migration.message == (
        "No migration required; no file changes written."
    )
    assert write_report.migration.changed is False
    assert after_write == before


def _schema_files(tmp_path):
    xyz_path = tmp_path / "water.xyz"
    xyz_path.write_text(
        "3\n"
        "synthetic schema-check fixture\n"
        "O 0 0 0\n"
        "H 0 0 1\n"
        "H 0 1 0\n",
        encoding="utf-8",
    )
    species_path = tmp_path / "species.yaml"
    species_path.write_text(
        "schema_version: 1\n"
        "species:\n"
        "  - name: water\n"
        "    formula: H2O\n"
        "    charge: 0\n"
        "    multiplicity: 1\n"
        "    geometry_path: water.xyz\n",
        encoding="utf-8",
    )
    result_path = tmp_path / "results.json"
    save_result_collection(
        result_path,
        [
            CalculationResult(
                species_name="water",
                backend="gaussian",
                method="wb97xd",
                basis="6-31g",
                task="single_point",
                success=True,
            )
        ],
    )
    pathway_path = tmp_path / "pathway.yaml"
    pathway_path.write_text("schema_version: 1\nreactions: []\n", encoding="utf-8")
    project_path = tmp_path / "qchem_project.yaml"
    project_path.write_text(
        "schema_version: 1\n"
        "project:\n"
        "  name: demo\n"
        "  species: species.yaml\n",
        encoding="utf-8",
    )
    campaign_path = tmp_path / "campaign.yaml"
    campaign_path.write_text(
        "schema_version: 1\n"
        "campaign:\n"
        "  name: demo\n"
        "  results: results.json\n",
        encoding="utf-8",
    )
    microkinetic_path = tmp_path / "microkinetic_model.yaml"
    microkinetic_path.write_text(
        "schema_version: 1\n"
        "microkinetic_model:\n"
        "  name: synthetic schema-check model\n"
        "  site_types:\n"
        "    - id: star\n"
        "      total_sites: 1.0\n"
        "      unit: fraction\n"
        "  species:\n"
        "    gas:\n"
        "      CO_g:\n"
        "        phase: gas\n"
        "        formula: CO\n"
        "    surface:\n"
        "      CO_star:\n"
        "        phase: surface\n"
        "        formula: CO\n"
        "        site_type: star\n"
        "  steps:\n"
        "    - id: co_ads\n"
        "      reversible: true\n"
        "      reactants:\n"
        "        CO_g: 1\n"
        "        star: 1\n"
        "      products:\n"
        "        CO_star: 1\n"
        "      rate_constant_forward: k_co_ads_f\n"
        "      rate_constant_reverse: k_co_ads_r\n"
        "  rate_parameters:\n"
        "    - k_co_ads_f\n"
        "    - k_co_ads_r\n",
        encoding="utf-8",
    )
    return {
        "species": species_path,
        "result_store": result_path,
        "pathway": pathway_path,
        "project_manifest": project_path,
        "campaign": campaign_path,
        "microkinetic_model": microkinetic_path,
    }
