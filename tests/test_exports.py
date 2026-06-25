from __future__ import annotations

import csv
from io import StringIO

from qchem_workbench.analysis.reactions import ReactionEnergyRow
from qchem_workbench.core.result import CalculationResult
from qchem_workbench.core.species import Species
from qchem_workbench.reports.exports import (
    latex_escape,
    reaction_rows_to_csv,
    reaction_rows_to_latex_tabular,
    results_to_csv,
    results_to_latex_tabular,
    species_to_csv,
)


def test_results_csv_includes_units_and_missing_values():
    csv_text = results_to_csv(
        [
            CalculationResult(
                species_name="water",
                backend="gaussian",
                method=None,
                basis="6-31g",
                task="single_point",
                success=True,
            )
        ]
    )

    rows = list(csv.DictReader(StringIO(csv_text)))
    assert "Electronic energy (Hartree)" in rows[0]
    assert rows[0]["Method"] == ""
    assert rows[0]["Electronic energy (Hartree)"] == ""


def test_species_csv_preserves_special_characters(tmp_path):
    csv_text = species_to_csv(
        [
            Species(
                name="A&B_1",
                formula="C#H",
                charge=-1,
                multiplicity=2,
                geometry_path=tmp_path / "a.xyz",
                tags=("synthetic", "demo"),
                notes="fixture, not data",
            )
        ]
    )

    rows = list(csv.DictReader(StringIO(csv_text)))
    assert rows[0]["Name"] == "A&B_1"
    assert rows[0]["Formula"] == "C#H"
    assert rows[0]["Tags"] == "synthetic;demo"


def test_latex_escape_special_characters():
    assert latex_escape(r"A&B_1%$#{}~^\path") == (
        r"A\&B\_1\%\$\#\{\}\textasciitilde{}\textasciicircum{}"
        r"\textbackslash{}path"
    )


def test_results_latex_tabular_escapes_and_marks_missing():
    latex = results_to_latex_tabular(
        [
            CalculationResult(
                species_name="A&B_1",
                backend="gaussian",
                method="wb97xd",
                basis=None,
                task="single_point",
                success=True,
                electronic_energy_hartree=-1.25,
            )
        ]
    )

    assert r"A\&B\_1" in latex
    assert "Electronic energy (Hartree)" in latex
    assert "N/A" in latex


def test_reaction_exports_are_stable():
    rows = [
        ReactionEnergyRow(
            reaction_id="r_1",
            label="A&B to B",
            quantity="delta_e_electronic",
            delta_hartree=0.5,
            delta_ev=13.6057,
            delta_kj_mol=1312.7498,
            complete=True,
            missing_species=(),
            notes="Sign convention: products minus reactants.",
        )
    ]

    csv_text = reaction_rows_to_csv(rows)
    latex = reaction_rows_to_latex_tabular(rows)

    assert csv_text.splitlines()[0] == (
        "Reaction ID,Label,Quantity,Complete,Delta (Hartree),Delta (eV),"
        "Delta (kJ/mol),Missing species,Notes"
    )
    assert "r_1,A&B to B,delta_e_electronic,True,0.5,13.6057" in csv_text
    assert r"r\_1" in latex
    assert r"A\&B to B" in latex
    assert "Delta (kJ/mol)" in latex
