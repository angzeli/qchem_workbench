"""Command-line interface for qchem-workbench."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from qchem_workbench import __version__
from qchem_workbench.core.registry import load_species_registry
from qchem_workbench.templates.project import (
    PROJECT_DIRECTORIES,
    TEMPLATE_NAMES,
    get_template_files,
)


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
    subparsers = parser.add_subparsers(dest="command")

    init_parser = subparsers.add_parser("init", help="create a workflow directory")
    init_parser.add_argument("path", type=Path)
    init_parser.add_argument(
        "--template",
        choices=TEMPLATE_NAMES,
        default="blank",
        help="starter template to create",
    )
    init_parser.add_argument(
        "--force",
        action="store_true",
        help="overwrite files created by the selected template",
    )
    init_parser.set_defaults(func=_init_command)

    validate_parser = subparsers.add_parser(
        "validate", help="validate a species registry"
    )
    validate_parser.add_argument("registry", type=Path)
    validate_parser.set_defaults(func=_validate_command)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    command = getattr(args, "func", None)
    if command is None:
        parser.print_help()
        return 0
    return command(args)


def _init_command(args: argparse.Namespace) -> int:
    try:
        _initialize_project(args.path, args.template, args.force)
    except (OSError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    print(f"Initialized {args.path} with template {args.template!r}.")
    return 0


def _validate_command(args: argparse.Namespace) -> int:
    try:
        species = load_species_registry(args.registry)
    except (OSError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    print(f"Validated {len(species)} species in {args.registry}.")
    return 0


def _initialize_project(path: Path, template: str, force: bool) -> None:
    target = Path(path)
    if target.exists() and not target.is_dir():
        raise ValueError(f"{target} exists and is not a directory")

    files = get_template_files(template)
    conflicts = [
        target / relative_path
        for relative_path in files
        if (target / relative_path).exists()
    ]
    if conflicts and not force:
        conflict_list = ", ".join(str(path) for path in conflicts)
        raise ValueError(f"refusing to overwrite existing file(s): {conflict_list}")

    target.mkdir(parents=True, exist_ok=True)
    for directory in PROJECT_DIRECTORIES:
        (target / directory).mkdir(exist_ok=True)

    for relative_path, content in files.items():
        destination = target / relative_path
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(content, encoding="utf-8")
