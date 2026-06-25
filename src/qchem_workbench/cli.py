"""Command-line interface for qchem-workbench."""

from __future__ import annotations

import argparse

from qchem_workbench import __version__


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="qchemwb",
        description="Manage backend-agnostic quantum-chemistry workflows.",
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"qchemwb {__version__}",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    parser.parse_args(argv)
    return 0
