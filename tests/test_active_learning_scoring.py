from __future__ import annotations

import csv

import pytest

from qchem_workbench.active_learning.objectives import load_objective_spec
from qchem_workbench.active_learning.scoring import score_dataset_rows
from qchem_workbench.cli import main


def test_minimise_transformation(tmp_path):
    spec = load_objective_spec(_write_objectives(tmp_path))
    scored = score_dataset_rows(
        [{"candidate_id": "a", "adsorption_energy_eV": "-0.4", "quality_error_count": "0"}],
        ["candidate_id", "adsorption_energy_eV", "quality_error_count"],
        spec,
    )

    row = scored.rows[0]
    assert row["objective_minimise_adsorption_energy_value"] == 0.4
    assert row["objective_minimise_adsorption_energy_transformation"] == "negate"


def test_target_transformation(tmp_path):
    spec = load_objective_spec(
        _write_objectives(
            tmp_path,
            objectives=(
                "  - id: target_adsorption_energy\n"
                "    source_column: adsorption_energy_eV\n"
                "    direction: target\n"
                "    target: -0.5\n"
            ),
            constraints="",
        )
    )

    scored = score_dataset_rows(
        [{"candidate_id": "a", "adsorption_energy_eV": "-0.4"}],
        ["candidate_id", "adsorption_energy_eV"],
        spec,
    )

    assert scored.rows[0]["objective_target_adsorption_energy_value"] == pytest.approx(-0.1)


def test_weighted_scoring_and_rank(tmp_path):
    spec = load_objective_spec(_write_objectives(tmp_path))
    scored = score_dataset_rows(
        [
            {"candidate_id": "a", "adsorption_energy_eV": "-0.4", "quality_error_count": "0"},
            {"candidate_id": "b", "adsorption_energy_eV": "-0.2", "quality_error_count": "0"},
        ],
        ["candidate_id", "adsorption_energy_eV", "quality_error_count"],
        spec,
    )

    ranks = {row["candidate_id"]: row["al_rank"] for row in scored.rows}
    assert ranks["a"] == 1
    assert ranks["b"] == 2


def test_failed_constraints_exclude_candidate(tmp_path):
    spec = load_objective_spec(_write_objectives(tmp_path))
    scored = score_dataset_rows(
        [{"candidate_id": "a", "adsorption_energy_eV": "-0.4", "quality_error_count": "1"}],
        ["candidate_id", "adsorption_energy_eV", "quality_error_count"],
        spec,
    )

    assert scored.rows[0]["al_status"] == "excluded"
    assert "constraint_failed" in scored.rows[0]["al_reasons"]


def test_missing_descriptor_handling(tmp_path):
    spec = load_objective_spec(_write_objectives(tmp_path))
    scored = score_dataset_rows(
        [{"candidate_id": "a", "adsorption_energy_eV": "", "quality_error_count": "0"}],
        ["candidate_id", "adsorption_energy_eV", "quality_error_count"],
        spec,
    )

    assert scored.rows[0]["al_status"] == "excluded"
    assert "missing_descriptor:adsorption_energy_eV" in scored.rows[0]["al_reasons"]


def test_score_dataset_cli(tmp_path, capsys):
    dataset_path = tmp_path / "dataset.csv"
    dataset_path.write_text(
        "candidate_id,adsorption_energy_eV,quality_error_count\n"
        "a,-0.4,0\n"
        "b,-0.2,0\n",
        encoding="utf-8",
    )
    objectives_path = _write_objectives(tmp_path)
    out_path = tmp_path / "scored.csv"

    exit_code = main(
        [
            "active-learning",
            "score-dataset",
            str(dataset_path),
            str(objectives_path),
            "--out",
            str(out_path),
        ]
    )

    captured = capsys.readouterr()
    assert exit_code == 0
    assert "scored dataset" in captured.out
    with out_path.open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    assert rows[0]["al_rank"] == "1"


def _write_objectives(
    tmp_path,
    *,
    objectives: str = (
        "  - id: minimise_adsorption_energy\n"
        "    source_column: adsorption_energy_eV\n"
        "    direction: minimise\n"
        "    weight: 1.0\n"
    ),
    constraints: str = (
        "  - id: require_no_quality_errors\n"
        "    source_column: quality_error_count\n"
        "    op: equals\n"
        "    value: 0\n"
    ),
):
    path = tmp_path / "objectives.yaml"
    path.write_text(
        "schema_version: 1\n"
        "objectives:\n"
        f"{objectives}"
        "constraints:\n"
        f"{constraints}",
        encoding="utf-8",
    )
    return path
