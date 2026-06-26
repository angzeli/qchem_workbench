from __future__ import annotations

import csv

import pytest

from qchem_workbench.analysis.active_learning import (
    ProposedCandidate,
    candidate_handoff_table,
    objective_handoff_table,
    read_proposed_candidates_csv,
    validate_proposed_candidates,
    write_handoff_table_csv,
    write_proposed_candidates_csv,
)
from qchem_workbench.campaigns import load_campaign_manifest


def test_candidate_handoff_export(tmp_path):
    campaign = _campaign(tmp_path)
    table = candidate_handoff_table(campaign)
    out_path = tmp_path / "candidates.csv"

    write_handoff_table_csv(out_path, table)

    with out_path.open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    assert rows[0]["candidate_id"] == "water"
    assert rows[0]["species_name"] == "water"
    assert rows[0]["tags"] == "demo"
    assert rows[1]["candidate_id"] == "slab_a"
    assert rows[1]["structure_path"].endswith("structures/slab_a.xyz")


def test_objective_handoff_export(tmp_path):
    descriptor_rows = [
        {
            "candidate_id": "water",
            "gap_ev": "5.0",
            "adsorption_energy_ev": "",
            "quality_flags": "",
        }
    ]
    table = objective_handoff_table(
        descriptor_rows,
        objective_columns=("gap_ev", "adsorption_energy_ev"),
    )
    out_path = tmp_path / "objectives.csv"

    write_handoff_table_csv(out_path, table)

    with out_path.open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    assert rows[0] == {
        "candidate_id": "water",
        "gap_ev": "5.0",
        "adsorption_energy_ev": "",
    }


def test_import_and_validate_proposed_candidates(tmp_path):
    campaign = _campaign(tmp_path)
    proposed_path = tmp_path / "proposed.csv"
    proposed_path.write_text(
        "candidate_id,reason\n"
        "water,external optimiser proposal\n",
        encoding="utf-8",
    )

    proposed = read_proposed_candidates_csv(proposed_path)
    validate_proposed_candidates(campaign, proposed)

    assert proposed == [
        ProposedCandidate(
            candidate_id="water",
            metadata={"reason": "external optimiser proposal"},
        )
    ]


def test_invalid_proposed_candidate_id(tmp_path):
    campaign = _campaign(tmp_path)
    proposed = [ProposedCandidate(candidate_id="missing", metadata={})]

    with pytest.raises(ValueError, match="not present in campaign or registry"):
        validate_proposed_candidates(campaign, proposed)


def test_proposed_candidate_csv_round_trip(tmp_path):
    proposed = [
        ProposedCandidate(
            candidate_id="water",
            metadata={"priority": "1", "note": "synthetic handoff fixture"},
        )
    ]
    path = tmp_path / "proposed.csv"

    write_proposed_candidates_csv(path, proposed)
    reloaded = read_proposed_candidates_csv(path)

    assert reloaded == proposed


def _campaign(tmp_path):
    manifest_path = tmp_path / "campaign.yaml"
    manifest_path.write_text(
        "schema_version: 1\n"
        "campaign:\n"
        "  name: demo\n"
        "  results: results/results.json\n"
        "  candidates:\n"
        "    - id: water\n"
        "      species: water\n"
        "      tags: [demo]\n"
        "    - id: slab_a\n"
        "      structure: structures/slab_a.xyz\n",
        encoding="utf-8",
    )
    return load_campaign_manifest(manifest_path)
