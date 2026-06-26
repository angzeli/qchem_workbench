from __future__ import annotations

from pathlib import Path

from qchem_workbench.analysis.conformers import select_lowest_energy_conformers
from qchem_workbench.core.result import CalculationResult


def _result(
    conformer_id: str | None,
    electronic: float | None = None,
    gibbs: float | None = None,
    *,
    species_name: str = "ethanol",
    method: str = "b3lyp",
    success: bool = True,
) -> CalculationResult:
    return CalculationResult(
        species_name=species_name,
        backend="gaussian",
        method=method,
        basis="def2-svp",
        task="single_point",
        success=success,
        electronic_energy_hartree=electronic,
        gibbs_free_energy_hartree=gibbs,
        source_path=Path(f"outputs/{conformer_id or 'unknown'}.log"),
        conformer_id=conformer_id,
    )


def test_select_lowest_electronic_energy_conformer():
    report = select_lowest_energy_conformers(
        [
            _result("conf_001", electronic=-10.0),
            _result("conf_002", electronic=-10.2),
        ],
        "electronic",
    )

    selection = report.selections[0]
    assert selection.selected_conformer_id == "conf_002"
    assert selection.selected_energy_hartree == -10.2


def test_select_lowest_gibbs_energy_without_electronic_fallback():
    report = select_lowest_energy_conformers(
        [
            _result("conf_001", electronic=-20.0, gibbs=-9.9),
            _result("conf_002", electronic=-10.0, gibbs=-10.1),
        ],
        "gibbs",
    )

    selection = report.selections[0]
    assert selection.selected_conformer_id == "conf_002"
    assert selection.selected_energy_hartree == -10.1


def test_missing_energy_is_reported_as_incomplete():
    report = select_lowest_energy_conformers(
        [_result("conf_001", electronic=None)],
        "electronic",
    )

    selection = report.selections[0]
    assert selection.selected_conformer_id is None
    assert selection.incomplete_results[0].reason == "missing_electronic_energy"


def test_mixed_method_warns_and_does_not_select_without_allow_mixed():
    report = select_lowest_energy_conformers(
        [
            _result("conf_001", electronic=-10.0, method="b3lyp"),
            _result("conf_002", electronic=-10.2, method="pbe0"),
        ],
        "electronic",
    )

    selection = report.selections[0]
    assert selection.selected_conformer_id is None
    assert any("mixed backend/method/basis/task" in item for item in selection.warnings)


def test_mixed_method_can_be_allowed_explicitly():
    report = select_lowest_energy_conformers(
        [
            _result("conf_001", electronic=-10.0, method="b3lyp"),
            _result("conf_002", electronic=-10.2, method="pbe0"),
        ],
        "electronic",
        allow_mixed=True,
    )

    selection = report.selections[0]
    assert selection.selected_conformer_id == "conf_002"
    assert any("allow_mixed is enabled" in item for item in selection.warnings)
