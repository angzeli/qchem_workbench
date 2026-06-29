from __future__ import annotations

import csv

from qchem_workbench.active_learning.datasets import (
    build_active_learning_dataset,
    load_active_learning_campaign,
)
from qchem_workbench.cli import main
from qchem_workbench.core.result import CalculationResult
from qchem_workbench.results.store import save_result_collection


def test_dataset_from_calculation_results(tmp_path):
    campaign_path = _write_campaign(tmp_path, sources=_result_source())
    _write_candidates(tmp_path)
    save_result_collection(
        tmp_path / "results.json",
        [
            CalculationResult(
                species_name="CO",
                backend="gaussian",
                method="B3LYP",
                basis="def2-SVP",
                task="single_point",
                success=True,
                electronic_energy_hartree=-113.0,
            )
        ],
    )

    dataset = build_active_learning_dataset(load_active_learning_campaign(campaign_path))

    row = dataset.rows[0]
    assert row["results_electronic_energy_hartree"] == -113.0
    assert row["results_backend"] == "gaussian"
    assert row["quality_error_count"] == 0


def test_dataset_from_adsorption_table(tmp_path):
    campaign_path = _write_campaign(tmp_path, sources=_adsorption_source())
    _write_candidates(tmp_path, system="co_on_surface")
    _write_csv(
        tmp_path / "adsorption.csv",
        ["system_id", "adsorption_eV", "complete"],
        [{"system_id": "co_on_surface", "adsorption_eV": "-0.4", "complete": "True"}],
    )

    dataset = build_active_learning_dataset(load_active_learning_campaign(campaign_path))

    assert dataset.rows[0]["ads_adsorption_eV"] == "-0.4"


def test_dataset_from_che_table(tmp_path):
    campaign_path = _write_campaign(tmp_path, sources=_che_source())
    _write_candidates(tmp_path, candidate_id="step_1", pathway="step_1")
    _write_csv(
        tmp_path / "che.csv",
        ["reaction_id", "corrected_delta_g_ev", "complete"],
        [{"reaction_id": "step_1", "corrected_delta_g_ev": "0.2", "complete": "True"}],
    )

    dataset = build_active_learning_dataset(load_active_learning_campaign(campaign_path))

    assert dataset.rows[0]["che_corrected_delta_g_ev"] == "0.2"


def test_missing_candidate_descriptors_are_visible(tmp_path):
    campaign_path = _write_campaign(tmp_path, sources=_result_source())
    _write_candidates(tmp_path, species="missing")
    save_result_collection(tmp_path / "results.json", [])

    dataset = build_active_learning_dataset(load_active_learning_campaign(campaign_path))

    assert dataset.rows[0]["missing_results_reason"] == "missing_result"


def test_quality_flag_propagation(tmp_path):
    campaign_path = _write_campaign(tmp_path, sources=_result_source())
    _write_candidates(tmp_path)
    save_result_collection(
        tmp_path / "results.json",
        [
            CalculationResult(
                species_name="CO",
                backend="gaussian",
                method=None,
                basis=None,
                task="single_point",
                success=True,
                electronic_energy_hartree=-113.0,
                warnings=["synthetic parser warning"],
            )
        ],
    )

    dataset = build_active_learning_dataset(load_active_learning_campaign(campaign_path))

    row = dataset.rows[0]
    assert row["quality_warning_count"] >= 1
    assert "parser_warning" in row["quality_flags"]


def test_active_learning_build_dataset_cli(tmp_path, capsys):
    campaign_path = _write_campaign(tmp_path, sources=_result_source())
    _write_candidates(tmp_path)
    save_result_collection(
        tmp_path / "results.json",
        [
            CalculationResult(
                species_name="CO",
                backend="gaussian",
                method="B3LYP",
                basis="def2-SVP",
                task="single_point",
                success=True,
                electronic_energy_hartree=-113.0,
            )
        ],
    )
    out_path = tmp_path / "dataset.csv"

    exit_code = main(
        [
            "active-learning",
            "build-dataset",
            str(campaign_path),
            "--out",
            str(out_path),
        ]
    )

    captured = capsys.readouterr()
    assert exit_code == 0
    assert "active-learning dataset" in captured.out
    with out_path.open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    assert rows[0]["candidate_id"] == "cand_001"


def _write_candidates(
    tmp_path,
    *,
    candidate_id: str = "cand_001",
    species: str = "CO",
    system: str | None = None,
    pathway: str | None = None,
):
    system_line = f"    system: {system}\n" if system else ""
    pathway_line = f"    pathway: {pathway}\n" if pathway else ""
    path = tmp_path / "candidates.yaml"
    path.write_text(
        "schema_version: 1\n"
        "candidates:\n"
        f"  - id: {candidate_id}\n"
        "    type: molecule\n"
        f"    species: {species}\n"
        f"{system_line}"
        f"{pathway_line}",
        encoding="utf-8",
    )
    return path


def _write_campaign(tmp_path, *, sources: str):
    path = tmp_path / "campaign.yaml"
    path.write_text(
        "schema_version: 1\n"
        "active_learning_campaign:\n"
        "  name: synthetic active-learning campaign\n"
        "  candidates: candidates.yaml\n"
        "  descriptor_sources:\n"
        f"{sources}",
        encoding="utf-8",
    )
    return path


def _result_source():
    return (
        "    - id: results\n"
        "      type: result_store\n"
        "      path: results.json\n"
    )


def _adsorption_source():
    return (
        "    - id: ads\n"
        "      type: adsorption_table\n"
        "      path: adsorption.csv\n"
    )


def _che_source():
    return (
        "    - id: che\n"
        "      type: che_table\n"
        "      path: che.csv\n"
    )


def _write_csv(path, headers, rows):
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=headers)
        writer.writeheader()
        writer.writerows(rows)
