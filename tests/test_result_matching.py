from __future__ import annotations

from pathlib import Path

from qchem_workbench.analysis.result_matching import match_results_to_species
from qchem_workbench.core.result import CalculationResult
from qchem_workbench.core.species import Species


def _species(name: str) -> Species:
    return Species(
        name=name,
        formula=None,
        charge=0,
        multiplicity=1,
        geometry_path=Path(f"xyz/{name}.xyz"),
    )


def _result(
    species_name: str,
    source_path: str | None = None,
) -> CalculationResult:
    return CalculationResult(
        species_name=species_name,
        backend="gaussian",
        method=None,
        basis=None,
        task=None,
        success=True,
        source_path=Path(source_path) if source_path else None,
    )


def test_exact_match_by_species_name():
    report = match_results_to_species([_species("water")], [_result("water")])

    assert report.matches[0].species.name == "water"
    assert report.matches[0].strategy == "species_name"
    assert report.unmatched_species == ()
    assert report.unmatched_results == ()


def test_fallback_match_by_filename_stem():
    report = match_results_to_species(
        [_species("water")],
        [_result("parsed-output", source_path="outputs/water.log")],
    )

    assert report.matches[0].species.name == "water"
    assert report.matches[0].strategy == "filename_stem"


def test_unmatched_species():
    report = match_results_to_species([_species("water")], [])

    assert report.unmatched_species == ("water",)


def test_unmatched_result():
    result = _result("co2", source_path="outputs/co2.log")

    report = match_results_to_species([_species("water")], [result])

    assert report.unmatched_results == (result,)


def test_ambiguous_match_requires_attention():
    report = match_results_to_species(
        [_species("water")],
        [
            _result("water", source_path="outputs/water_first.log"),
            _result("water", source_path="outputs/water_second.log"),
        ],
    )

    assert report.matches == ()
    assert report.ambiguous_matches[0].species_name == "water"
    assert report.unmatched_species == ()
