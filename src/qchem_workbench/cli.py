"""Command-line interface for qchem-workbench."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

from qchem_workbench import __version__
from qchem_workbench.backends.gaussian_input import (
    GAUSSIAN_TASK_PRESETS,
    GaussianInputOptions,
    gaussian_route_from_spec,
    render_gaussian_input,
)
from qchem_workbench.backends.pyscf_backend import (
    MissingOptionalDependencyError,
    PySCFBackend,
)
from qchem_workbench.core.calculation import CalculationSpec
from qchem_workbench.core.registry import load_species_registry
from qchem_workbench.core.result import CalculationResult
from qchem_workbench.core.species import Species
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

    run_pyscf_parser = subparsers.add_parser(
        "run-pyscf", help="run PySCF single-point calculations"
    )
    run_pyscf_parser.add_argument("registry", type=Path)
    run_pyscf_parser.add_argument("--method", required=True)
    run_pyscf_parser.add_argument("--basis", required=True)
    run_pyscf_parser.add_argument("--out", required=True, type=Path)
    run_pyscf_parser.set_defaults(func=_run_pyscf_command)

    render_gaussian_parser = subparsers.add_parser(
        "render-gaussian", help="render Gaussian input files without running Gaussian"
    )
    render_gaussian_parser.add_argument("registry", type=Path)
    render_gaussian_parser.add_argument("--method", required=True)
    render_gaussian_parser.add_argument("--basis", required=True)
    render_gaussian_parser.add_argument(
        "--task", required=True, choices=tuple(GAUSSIAN_TASK_PRESETS)
    )
    render_gaussian_parser.add_argument("--solvent")
    render_gaussian_parser.add_argument(
        "--route-keyword",
        action="append",
        default=[],
        help="additional explicit Gaussian route keyword; may be repeated",
    )
    render_gaussian_parser.add_argument("--out", required=True, type=Path)
    render_gaussian_parser.add_argument(
        "--force", action="store_true", help="overwrite existing .gjf files"
    )
    render_gaussian_parser.set_defaults(func=_render_gaussian_command)
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


def _run_pyscf_command(args: argparse.Namespace) -> int:
    try:
        species_list = load_species_registry(args.registry)
    except (OSError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    backend = PySCFBackend()
    spec = CalculationSpec(
        backend="pyscf",
        method=args.method,
        basis=args.basis,
        task="single_point",
    )
    results: list[CalculationResult] = []

    for species in species_list:
        try:
            result = backend.run(species, spec)
        except MissingOptionalDependencyError as exc:
            print(f"error: {exc}", file=sys.stderr)
            return 1
        except Exception as exc:
            result = _exception_result(species, spec, exc)
        results.append(result)

    _write_result_collection(args.out, spec, results)
    _print_result_summary(results)
    return 0 if all(result.success for result in results) else 1


def _render_gaussian_command(args: argparse.Namespace) -> int:
    try:
        species_list = load_species_registry(args.registry)
        spec = CalculationSpec(
            backend="gaussian",
            method=args.method,
            basis=args.basis,
            task=args.task,
            solvent=args.solvent,
        )
        generated = _render_gaussian_files(
            species_list=species_list,
            spec=spec,
            out_dir=args.out,
            additional_keywords=tuple(args.route_keyword),
            force=args.force,
        )
    except (OSError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    print("species\tfile")
    for species_name, path in generated:
        print(f"{species_name}\t{path}")
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


def _write_result_collection(
    path: Path, spec: CalculationSpec, results: list[CalculationResult]
) -> None:
    payload = {
        "schema_version": 1,
        "calculation": spec.to_dict(),
        "results": [result.to_dict() for result in results],
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )


def _print_result_summary(results: list[CalculationResult]) -> None:
    print("species\tsuccess\telectronic_energy_hartree\twarnings")
    for result in results:
        energy = (
            ""
            if result.electronic_energy_hartree is None
            else f"{result.electronic_energy_hartree:.12g}"
        )
        print(
            f"{result.species_name}\t{result.success}\t{energy}\t"
            f"{len(result.warnings)}"
        )


def _exception_result(
    species: Species, spec: CalculationSpec, exc: Exception
) -> CalculationResult:
    return CalculationResult(
        species_name=species.name,
        backend="pyscf",
        method=spec.method,
        basis=spec.basis,
        task=spec.task,
        success=False,
        warnings=[f"Backend raised exception: {exc}"],
        metadata={"exception_type": type(exc).__name__},
        source_path=species.geometry_path,
    )


def _render_gaussian_files(
    species_list: list[Species],
    spec: CalculationSpec,
    out_dir: Path,
    additional_keywords: tuple[str, ...],
    force: bool,
) -> list[tuple[str, Path]]:
    output_dir = Path(out_dir)
    route = gaussian_route_from_spec(spec, additional_keywords=additional_keywords)
    targets = [
        (species, output_dir / f"{_safe_filename(species.name)}.gjf")
        for species in species_list
    ]
    conflicts = [path for _, path in targets if path.exists()]
    if conflicts and not force:
        conflict_list = ", ".join(str(path) for path in conflicts)
        raise ValueError(f"refusing to overwrite existing file(s): {conflict_list}")

    output_dir.mkdir(parents=True, exist_ok=True)
    generated: list[tuple[str, Path]] = []
    for species, path in targets:
        content = render_gaussian_input(
            species,
            spec,
            GaussianInputOptions(
                route=route,
                title=f"{species.name} {spec.task} Gaussian input",
            ),
        )
        path.write_text(content, encoding="utf-8")
        generated.append((species.name, path))
    return generated


def _safe_filename(value: str) -> str:
    filename = re.sub(r"[^A-Za-z0-9._-]+", "_", value.strip()).strip("._")
    return filename or "species"
