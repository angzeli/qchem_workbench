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


def test_co2rr_molecular_example_validates_and_pathways_match():
    species = load_species_registry(Path("examples/co2rr_molecular/species.yaml"))

    assert {item.name for item in species} == {"co2", "co", "formate"}
    for path in (
        Path("examples/pathways/co2rr/co_pathway.yaml"),
        Path("examples/pathways/co2rr/formate_pathway.yaml"),
    ):
        pathway = load_pathway(path, species_registry=species)
        assert pathway.reactions


def test_co2rr_molecular_tutorial_parse_reaction_table_and_report(tmp_path):
    results_path = tmp_path / "co2rr_results.json"
    reaction_table_path = tmp_path / "co2rr_reaction_table.csv"
    report_path = tmp_path / "co2rr_report.md"

    parse_exit = main(
        [
            "parse-gaussian",
            "examples/co2rr_molecular/outputs",
            "--out",
            str(results_path),
        ]
    )
    reaction_exit = main(
        [
            "reaction-table",
            "examples/pathways/co2rr/co_pathway.yaml",
            str(results_path),
            "--quantity",
            "electronic",
            "--out",
            str(reaction_table_path),
        ]
    )
    report_exit = main(
        [
            "report",
            str(results_path),
            "--species",
            "examples/co2rr_molecular/species.yaml",
            "--out",
            str(report_path),
        ]
    )

    reaction_table = reaction_table_path.read_text(encoding="utf-8")
    report = report_path.read_text(encoding="utf-8")
    assert parse_exit == 0
    assert reaction_exit == 0
    assert report_exit == 0
    assert "co2_to_co_bookkeeping" in reaction_table
    assert "co2" in report
