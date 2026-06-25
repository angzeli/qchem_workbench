#!/usr/bin/env python
"""Validate committed qchem-workbench examples without external engines."""

from __future__ import annotations

import sys
import tempfile
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_PATH = REPO_ROOT / "src"
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

from qchem_workbench.cli import main  # noqa: E402


def run_cli(args: list[str]) -> None:
    exit_code = main(args)
    if exit_code != 0:
        raise SystemExit(f"command failed with exit code {exit_code}: qchemwb {' '.join(args)}")


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


def main_script() -> int:
    with tempfile.TemporaryDirectory(prefix="qchemwb-examples-") as temp_dir:
        work_dir = Path(temp_dir)
        validate_basic_molecules(work_dir)
        validate_co2rr_molecular(work_dir)
    print("Example validation completed successfully.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main_script())
