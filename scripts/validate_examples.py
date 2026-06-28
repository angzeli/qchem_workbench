#!/usr/bin/env python
"""Validate committed qchem-workbench examples without external engines."""

from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_PATH = REPO_ROOT / "src"
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

from qchem_workbench.cli import main  # noqa: E402
from qchem_workbench.backends.ase_adsorption import (  # noqa: E402
    load_adsorbate_placement_config,
)
from qchem_workbench.backends.qe_pseudos import (  # noqa: E402
    load_pseudopotential_manifest,
)


EXPECTED_EXAMPLE_DIRS = (
    "basic_molecules",
    "gaussian_parsing",
    "orca_parsing",
    "qe_parsing",
    "co2rr_molecular",
    "surface_adsorption",
    "che_analysis",
    "screening_campaign",
)

SYNTHETIC_FIXTURE_EXAMPLE_DIRS = EXPECTED_EXAMPLE_DIRS

SCHEMA_CHECK_FILES = (
    "examples/basic_molecules/species.yaml",
    "examples/co2rr_molecular/species.yaml",
    "examples/pathways/basic_isomerisation.yaml",
    "examples/pathways/co2rr/co_pathway.yaml",
    "examples/pathways/co2rr/formate_pathway.yaml",
    "examples/che_analysis/che_pathway.yaml",
    "examples/che_analysis/results.json",
    "examples/screening_campaign/campaign.yaml",
    "examples/screening_campaign/results.json",
    "examples/surface_adsorption/results.json",
    "examples/qe_parsing/convergence_results.json",
)

STATIC_SYNTHETIC_RESULT_STORES = (
    "examples/che_analysis/results.json",
    "examples/screening_campaign/results.json",
    "examples/surface_adsorption/results.json",
    "examples/qe_parsing/convergence_results.json",
)


def run_cli(args: list[str]) -> None:
    exit_code = main(args)
    if exit_code != 0:
        raise SystemExit(f"command failed with exit code {exit_code}: qchemwb {' '.join(args)}")


def validate_example_layout(_work_dir: Path) -> None:
    for example_dir in EXPECTED_EXAMPLE_DIRS:
        readme = REPO_ROOT / "examples" / example_dir / "README.md"
        if not readme.exists():
            raise SystemExit(f"missing example README: {readme}")

    for example_dir in SYNTHETIC_FIXTURE_EXAMPLE_DIRS:
        readme = REPO_ROOT / "examples" / example_dir / "README.md"
        text = readme.read_text(encoding="utf-8").lower()
        if "synthetic" not in text:
            raise SystemExit(f"example README must label fixtures synthetic: {readme}")


def validate_schema_files(_work_dir: Path) -> None:
    for relative_path in SCHEMA_CHECK_FILES:
        run_cli(["schema-check", str(REPO_ROOT / relative_path)])


def validate_synthetic_result_labels(_work_dir: Path) -> None:
    for relative_path in STATIC_SYNTHETIC_RESULT_STORES:
        path = REPO_ROOT / relative_path
        data = json.loads(path.read_text(encoding="utf-8"))
        for index, result in enumerate(data.get("results", []), start=1):
            metadata = result.get("metadata", {})
            if metadata.get("fixture") != "synthetic":
                raise SystemExit(
                    f"{path}: results[{index}] must label fixture metadata as synthetic"
                )


def validate_basic_molecules(work_dir: Path) -> None:
    example = REPO_ROOT / "examples" / "basic_molecules"
    results_path = work_dir / "basic_results.json"
    report_path = work_dir / "basic_report.md"

    run_cli(["validate", str(example / "species.yaml")])
    run_cli(
        [
            "render-gaussian",
            str(example / "species.yaml"),
            "--method",
            "wb97xd",
            "--basis",
            "6-31g",
            "--task",
            "single_point",
            "--out",
            str(work_dir / "basic_gaussian_inputs"),
        ]
    )
    run_cli(["parse-gaussian", str(example / "outputs"), "--out", str(results_path)])
    run_cli(["schema-check", str(results_path)])
    run_cli(["check-results", str(results_path), "--species", str(example / "species.yaml")])
    run_cli(
        [
            "report",
            str(results_path),
            "--species",
            str(example / "species.yaml"),
            "--out",
            str(report_path),
        ]
    )


def validate_co2rr_molecular(work_dir: Path) -> None:
    example = REPO_ROOT / "examples" / "co2rr_molecular"
    pathways = REPO_ROOT / "examples" / "pathways" / "co2rr"
    results_path = work_dir / "co2rr_results.json"

    run_cli(["validate", str(example / "species.yaml")])
    run_cli(
        [
            "render-gaussian",
            str(example / "species.yaml"),
            "--method",
            "wb97xd",
            "--basis",
            "6-31g",
            "--task",
            "single_point",
            "--out",
            str(work_dir / "co2rr_gaussian_inputs"),
        ]
    )
    run_cli(["parse-gaussian", str(example / "outputs"), "--out", str(results_path)])
    run_cli(["schema-check", str(results_path)])
    run_cli(["check-results", str(results_path), "--species", str(example / "species.yaml")])
    for pathway_name in ("co_pathway.yaml", "formate_pathway.yaml"):
        run_cli(
            [
                "reaction-table",
                str(pathways / pathway_name),
                str(results_path),
                "--quantity",
                "electronic",
                "--out",
                str(work_dir / f"{Path(pathway_name).stem}.csv"),
            ]
        )
    run_cli(
        [
            "report",
            str(results_path),
            "--species",
            str(example / "species.yaml"),
            "--out",
            str(work_dir / "co2rr_report.md"),
        ]
    )


def validate_gaussian_parsing(work_dir: Path) -> None:
    example = REPO_ROOT / "examples" / "gaussian_parsing"
    results_path = work_dir / "gaussian_parsing_results.json"

    run_cli(["parse-gaussian", str(example / "outputs"), "--out", str(results_path)])
    run_cli(["schema-check", str(results_path)])
    run_cli(["check-results", str(results_path)])
    run_cli(["report", str(results_path), "--out", str(work_dir / "gaussian_report.md")])


def validate_orca_parsing(work_dir: Path) -> None:
    example = REPO_ROOT / "examples" / "orca_parsing"
    results_path = work_dir / "orca_parsing_results.json"

    run_cli(["parse-orca", str(example / "outputs"), "--out", str(results_path)])
    run_cli(["schema-check", str(results_path)])
    run_cli(["check-results", str(results_path)])


def validate_qe_parsing(work_dir: Path) -> None:
    example = REPO_ROOT / "examples" / "qe_parsing"
    results_path = work_dir / "qe_parsing_results.json"

    run_cli(["parse-qe", str(example / "outputs"), "--out", str(results_path)])
    run_cli(["schema-check", str(results_path)])
    run_cli(["check-results", str(results_path)])
    load_pseudopotential_manifest(example / "pseudos.yaml")
    run_cli(
        [
            "convergence-table",
            str(example / "convergence.yaml"),
            str(example / "convergence_results.json"),
            "--out",
            str(work_dir / "qe_convergence.csv"),
        ]
    )


def validate_surface_adsorption(work_dir: Path) -> None:
    example = REPO_ROOT / "examples" / "surface_adsorption"

    load_adsorbate_placement_config(example / "placement.yaml")
    run_cli(["inspect-structure", str(example / "slab.xyz")])
    run_cli(["inspect-structure", str(example / "co.xyz")])
    run_cli(
        [
            "adsorption-table",
            str(example / "adsorption.yaml"),
            str(example / "results.json"),
            "--quantity",
            "electronic",
            "--out",
            str(work_dir / "adsorption_table.csv"),
        ]
    )


def validate_che_analysis(work_dir: Path) -> None:
    example = REPO_ROOT / "examples" / "che_analysis"

    run_cli(
        [
            "che-table",
            str(example / "che_pathway.yaml"),
            str(example / "results.json"),
            "--out",
            str(work_dir / "che_table.csv"),
        ]
    )


def validate_screening_campaign(work_dir: Path) -> None:
    example = REPO_ROOT / "examples" / "screening_campaign"
    descriptors_path = work_dir / "descriptors.csv"

    run_cli(
        [
            "descriptor-table",
            str(example / "campaign.yaml"),
            str(example / "results.json"),
            "--out",
            str(descriptors_path),
        ]
    )
    run_cli(
        [
            "rank-candidates",
            str(example / "campaign.yaml"),
            str(descriptors_path),
            "--out",
            str(work_dir / "ranked_candidates.csv"),
        ]
    )


def main_script() -> int:
    with tempfile.TemporaryDirectory(prefix="qchemwb-examples-") as temp_dir:
        work_dir = Path(temp_dir)
        steps = (
            ("example layout", validate_example_layout),
            ("schema files", validate_schema_files),
            ("synthetic result labels", validate_synthetic_result_labels),
            ("basic molecule workflow", validate_basic_molecules),
            ("Gaussian parsing workflow", validate_gaussian_parsing),
            ("ORCA parsing workflow", validate_orca_parsing),
            ("QE parsing workflow", validate_qe_parsing),
            ("CO2RR molecular workflow", validate_co2rr_molecular),
            ("surface adsorption workflow", validate_surface_adsorption),
            ("CHE analysis workflow", validate_che_analysis),
            ("screening campaign workflow", validate_screening_campaign),
        )
        for label, step in steps:
            print(f"[v2 example gate] {label}")
            step(work_dir)
    print("v2 example validation gate completed successfully.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main_script())
