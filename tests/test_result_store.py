from __future__ import annotations

from pathlib import Path

from qchem_workbench.core.result import CalculationResult
from qchem_workbench.results.store import (
    append_results,
    deduplicate_results,
    load_result_collection,
    save_result_collection,
)


def _result(
    species_name: str = "water",
    source_path: str | None = "outputs/water.log",
    energy: float | None = -76.0,
) -> CalculationResult:
    return CalculationResult(
        species_name=species_name,
        backend="gaussian",
        method="wb97xd",
        basis="6-31g",
        task="single_point",
        success=True,
        electronic_energy_hartree=energy,
        warnings=["synthetic warning"],
        metadata={"route": "# wb97xd/6-31g", "run_id": "run-1"},
        source_path=Path(source_path) if source_path else None,
    )


def test_save_and_load_result_collection(tmp_path):
    path = tmp_path / "results.json"

    save_result_collection(path, [_result()])
    loaded = load_result_collection(path)

    assert len(loaded) == 1
    assert loaded[0].species_name == "water"
    assert loaded[0].source_path == Path("outputs/water.log")


def test_append_results(tmp_path):
    path = tmp_path / "results.json"
    save_result_collection(path, [_result("water")])

    combined = append_results(path, [_result("co2", "outputs/co2.log")])

    assert [result.species_name for result in combined] == ["water", "co2"]
    assert len(load_result_collection(path)) == 2


def test_deduplicate_results_uses_stable_identity():
    first = _result(energy=-76.0)
    replacement = _result(energy=-76.1)

    deduplicated = deduplicate_results([first, replacement])

    assert len(deduplicated) == 1
    assert deduplicated[0].electronic_energy_hartree == -76.1


def test_deduplicate_uses_run_id_when_source_path_missing():
    first = _result(source_path=None, energy=-1.0)
    replacement = _result(source_path=None, energy=-2.0)

    deduplicated = deduplicate_results([first, replacement])

    assert len(deduplicated) == 1
    assert deduplicated[0].electronic_energy_hartree == -2.0


def test_store_preserves_warnings_and_metadata(tmp_path):
    path = tmp_path / "results.json"
    save_result_collection(path, [_result()])

    loaded = load_result_collection(path)

    assert loaded[0].warnings == ["synthetic warning"]
    assert loaded[0].metadata == {"route": "# wb97xd/6-31g", "run_id": "run-1"}
