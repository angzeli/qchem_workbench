from __future__ import annotations

from pathlib import Path

from qchem_workbench.analysis.reactions import load_pathway


def test_example_pathways_validate():
    example_paths = [
        Path("examples/pathways/basic_isomerisation.yaml"),
        Path("examples/pathways/co2rr/co_pathway.yaml"),
        Path("examples/pathways/co2rr/formate_pathway.yaml"),
    ]

    for path in example_paths:
        pathway = load_pathway(path)
        assert pathway.reactions
