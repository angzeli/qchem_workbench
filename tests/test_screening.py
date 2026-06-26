from __future__ import annotations

import csv

from qchem_workbench.analysis.adsorption import AdsorptionEnergyRow
from qchem_workbench.analysis.quality_checks import QualityCheck
from qchem_workbench.analysis.reactions import ReactionEnergyRow
from qchem_workbench.analysis.screening import (
    build_descriptor_table,
    write_descriptor_table_csv,
)
from qchem_workbench.campaigns import load_campaign_manifest
from qchem_workbench.core.result import CalculationResult


def test_descriptor_table_with_complete_result_data(tmp_path):
    campaign = _campaign(
        tmp_path,
        descriptors=(
            "    - name: electronic_energy_hartree\n"
            "      source: result\n"
            "      field: electronic_energy_hartree\n"
            "    - name: gibbs_free_energy_hartree\n"
            "      source: result\n"
            "      field: gibbs_free_energy_hartree\n"
            "    - name: homo_ev\n"
            "      source: result\n"
            "      field: homo_ev\n"
            "    - name: lumo_ev\n"
            "      source: result\n"
            "      field: lumo_ev\n"
            "    - name: gap_ev\n"
            "      source: result\n"
            "      field: gap_ev\n"
        ),
    )
    results = [
        CalculationResult(
            species_name="water",
            backend="gaussian",
            method="wb97xd",
            basis="6-31g",
            task="single_point",
            success=True,
            electronic_energy_hartree=-76.0,
            gibbs_free_energy_hartree=-75.9,
            homo_ev=-6.0,
            lumo_ev=-1.0,
            gap_ev=5.0,
        )
    ]

    table = build_descriptor_table(campaign, results)

    assert table.headers == (
        "candidate_id",
        "species_name",
        "structure_path",
        "electronic_energy_hartree",
        "gibbs_free_energy_hartree",
        "homo_ev",
        "lumo_ev",
        "gap_ev",
        "quality_error_count",
        "quality_warning_count",
        "quality_info_count",
        "quality_flags",
    )
    assert table.rows[0]["candidate_id"] == "water"
    assert table.rows[0]["electronic_energy_hartree"] == -76.0
    assert table.rows[0]["gibbs_free_energy_hartree"] == -75.9
    assert table.rows[0]["gap_ev"] == 5.0
    assert table.rows[0]["quality_flags"] == ""


def test_descriptor_table_keeps_missing_values_missing(tmp_path):
    campaign = _campaign(
        tmp_path,
        descriptors=(
            "    - name: electronic_energy_hartree\n"
            "      source: result\n"
            "      field: electronic_energy_hartree\n"
            "    - name: gap_ev\n"
            "      source: result\n"
            "      field: gap_ev\n"
        ),
    )
    results = [
        CalculationResult(
            species_name="water",
            backend="gaussian",
            method="wb97xd",
            basis="6-31g",
            task="single_point",
            success=True,
            electronic_energy_hartree=-76.0,
        )
    ]

    table = build_descriptor_table(campaign, results)

    assert table.rows[0]["electronic_energy_hartree"] == -76.0
    assert table.rows[0]["gap_ev"] is None


def test_descriptor_table_includes_quality_flags(tmp_path):
    campaign = _campaign(
        tmp_path,
        descriptors=(
            "    - name: electronic_energy_hartree\n"
            "      source: result\n"
            "      field: electronic_energy_hartree\n"
        ),
    )
    results = [
        CalculationResult(
            species_name="water",
            backend="gaussian",
            method="wb97xd",
            basis="6-31g",
            task="single_point",
            success=True,
            warnings=["Synthetic parser warning."],
        )
    ]
    checks = [
        QualityCheck(
            code="missing_electronic_energy",
            severity="warning",
            message="Electronic energy is missing.",
            result_identifier="water",
        ),
        QualityCheck(
            code="unmatched_result",
            severity="info",
            message="No registry species matched result.",
            result_identifier="water",
        ),
    ]

    table = build_descriptor_table(campaign, results, quality_checks=checks)

    assert table.rows[0]["quality_error_count"] == 0
    assert table.rows[0]["quality_warning_count"] == 2
    assert table.rows[0]["quality_info_count"] == 1
    assert table.rows[0]["quality_flags"] == (
        "missing_electronic_energy;unmatched_result;parser_warning"
    )


def test_descriptor_table_can_include_selected_reaction_and_adsorption_values(tmp_path):
    campaign = _campaign(
        tmp_path,
        descriptors=(
            "    - name: reaction_delta_ev\n"
            "      source: reaction\n"
            "      reference: r1\n"
            "      field: delta_ev\n"
            "    - name: adsorption_energy_ev\n"
            "      source: adsorption\n"
            "      reference: co_on_surface\n"
            "      field: adsorption_ev\n"
        ),
    )
    reaction_rows = [
        ReactionEnergyRow(
            reaction_id="r1",
            label="A to B",
            quantity="delta_e_electronic",
            delta_hartree=0.1,
            delta_ev=2.721,
            delta_kj_mol=262.55,
            complete=True,
            missing_species=(),
        )
    ]
    adsorption_rows = [
        AdsorptionEnergyRow(
            system_id="co_on_surface",
            quantity="adsorption_electronic_energy",
            slab_result="slab",
            adsorbate_result="co",
            combined_result="slab_co",
            adsorption_hartree=-0.01,
            adsorption_ev=-0.272,
            adsorption_kj_mol=-26.25,
            complete=True,
            missing=(),
            warnings=(),
        )
    ]

    table = build_descriptor_table(
        campaign,
        [],
        reaction_rows=reaction_rows,
        adsorption_rows=adsorption_rows,
    )

    assert table.rows[0]["reaction_delta_ev"] == 2.721
    assert table.rows[0]["adsorption_energy_ev"] == -0.272


def test_descriptor_table_csv_output(tmp_path):
    campaign = _campaign(
        tmp_path,
        descriptors=(
            "    - name: electronic_energy_hartree\n"
            "      source: result\n"
            "      field: electronic_energy_hartree\n"
        ),
    )
    results = [
        CalculationResult(
            species_name="water",
            backend="gaussian",
            method="wb97xd",
            basis="6-31g",
            task="single_point",
            success=True,
            electronic_energy_hartree=-76.0,
        )
    ]
    table = build_descriptor_table(campaign, results)
    out_path = tmp_path / "descriptors.csv"

    write_descriptor_table_csv(out_path, table)

    with out_path.open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    assert rows[0]["candidate_id"] == "water"
    assert rows[0]["electronic_energy_hartree"] == "-76.0"


def _campaign(tmp_path, *, descriptors: str):
    manifest_path = tmp_path / "campaign.yaml"
    manifest_path.write_text(
        "schema_version: 1\n"
        "campaign:\n"
        "  name: demo\n"
        "  results: results/results.json\n"
        "  candidates:\n"
        "    - id: water\n"
        "      species: water\n"
        "  descriptors:\n"
        f"{descriptors}",
        encoding="utf-8",
    )
    return load_campaign_manifest(manifest_path)
