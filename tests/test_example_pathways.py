from __future__ import annotations

from pathlib import Path

from qchem_workbench.cli import main
from qchem_workbench.analysis.reactions import load_pathway
from qchem_workbench.core.registry import load_species_registry


def test_example_pathways_validate():
    example_paths = [
        Path("examples/pathways/basic_isomerisation.yaml"),
        Path("examples/pathways/co2rr/co_pathway.yaml"),
        Path("examples/pathways/co2rr/formate_pathway.yaml"),
    ]

    for path in example_paths:
        pathway = load_pathway(path)
        assert pathway.reactions


def test_basic_molecules_example_validates():
    species = load_species_registry(Path("examples/basic_molecules/species.yaml"))

    assert {item.name for item in species} == {
        "water",
        "carbon_dioxide",
        "carbon_monoxide",
    }


def test_basic_molecules_tutorial_parse_and_report(tmp_path):
    results_path = tmp_path / "basic_results.json"
    report_path = tmp_path / "basic_report.md"

    parse_exit = main(
        [
            "parse-gaussian",
            "examples/basic_molecules/outputs",
            "--out",
            str(results_path),
        ]
    )
    report_exit = main(
        [
            "report",
            str(results_path),
            "--species",
            "examples/basic_molecules/species.yaml",
            "--out",
            str(report_path),
        ]
    )

    report = report_path.read_text(encoding="utf-8")
    assert parse_exit == 0
    assert report_exit == 0
    assert "water" in report
    assert "Electronic energy (Hartree)" in report
