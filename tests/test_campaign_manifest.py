from __future__ import annotations

import pytest

from qchem_workbench.campaigns import load_campaign_manifest


def test_load_valid_campaign_manifest(tmp_path):
    manifest_path = tmp_path / "campaign.yaml"
    manifest_path.write_text(
        "schema_version: 1\n"
        "campaign:\n"
        "  name: demo screening\n"
        "  backend_mode: gaussian\n"
        "  results:\n"
        "    - results/results.json\n"
        "  candidates:\n"
        "    - id: water\n"
        "      species: water\n"
        "      tags: [demo]\n"
        "    - id: slab_a\n"
        "      structure: structures/slab_a.xyz\n"
        "  calculation_templates:\n"
        "    - id: sp\n"
        "      method: wb97xd\n"
        "      basis: 6-31g\n"
        "      task: single_point\n"
        "  descriptors:\n"
        "    - name: electronic_energy_hartree\n"
        "      source: result\n"
        "      field: electronic_energy_hartree\n"
        "    - name: gap_ev\n"
        "      source: result\n"
        "      field: gap_ev\n"
        "  ranking:\n"
        "    rules:\n"
        "      - descriptor: gap_ev\n"
        "        direction: maximize\n"
        "        weight: 1.5\n",
        encoding="utf-8",
    )

    campaign = load_campaign_manifest(manifest_path)
    spec = campaign.calculation_templates[0].to_spec(
        default_backend=campaign.backend_mode
    )

    assert campaign.name == "demo screening"
    assert campaign.backend_mode == "gaussian"
    assert campaign.result_paths == (tmp_path / "results" / "results.json",)
    assert campaign.candidates[0].id == "water"
    assert campaign.candidates[0].species_name == "water"
    assert campaign.candidates[0].tags == ("demo",)
    assert campaign.candidates[1].structure_path == tmp_path / "structures" / "slab_a.xyz"
    assert campaign.descriptors[0].field == "electronic_energy_hartree"
    assert campaign.ranking_rules[0].descriptor == "gap_ev"
    assert campaign.ranking_rules[0].direction == "maximize"
    assert campaign.ranking_rules[0].weight == 1.5
    assert spec.backend == "gaussian"
    assert spec.method == "wb97xd"
    assert spec.basis == "6-31g"
    assert spec.task == "single_point"


def test_campaign_duplicate_candidate_ids_are_errors(tmp_path):
    manifest_path = tmp_path / "campaign.yaml"
    manifest_path.write_text(
        "schema_version: 1\n"
        "campaign:\n"
        "  name: demo\n"
        "  results: results/results.json\n"
        "  candidates:\n"
        "    - id: water\n"
        "      species: water\n"
        "    - id: water\n"
        "      species: other_water\n",
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="duplicate candidate id"):
        load_campaign_manifest(manifest_path)


def test_campaign_result_path_is_required(tmp_path):
    manifest_path = tmp_path / "campaign.yaml"
    manifest_path.write_text(
        "schema_version: 1\n"
        "campaign:\n"
        "  name: demo\n"
        "  candidates:\n"
        "    - id: water\n"
        "      species: water\n",
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="campaign.results must list"):
        load_campaign_manifest(manifest_path)


def test_campaign_missing_schema_version(tmp_path):
    manifest_path = tmp_path / "campaign.yaml"
    manifest_path.write_text(
        "campaign:\n"
        "  name: demo\n"
        "  results: results/results.json\n",
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="missing schema_version"):
        load_campaign_manifest(manifest_path)


def test_campaign_unsupported_schema_version(tmp_path):
    manifest_path = tmp_path / "campaign.yaml"
    manifest_path.write_text(
        "schema_version: 99\n"
        "campaign:\n"
        "  name: demo\n"
        "  results: results/results.json\n",
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="unsupported schema_version"):
        load_campaign_manifest(manifest_path)
