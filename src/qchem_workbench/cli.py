"""Command-line interface for qchem-workbench."""

from __future__ import annotations

import argparse
import csv
import json
import re
import sys
from pathlib import Path

import yaml

from qchem_workbench import __version__
from qchem_workbench.active_learning.datasets import (
    build_active_learning_dataset,
    load_active_learning_campaign,
    write_descriptor_dataset_csv,
)
from qchem_workbench.active_learning.bo_forge import export_bo_forge_interchange
from qchem_workbench.active_learning.objectives import load_objective_spec
from qchem_workbench.active_learning.scoring import (
    score_dataset_rows,
    write_scored_dataset_csv,
)
from qchem_workbench.analysis.adsorption import (
    AdsorptionEnergyRow,
    adsorption_electronic_energy_table,
    adsorption_gibbs_free_energy_table,
    load_adsorption_workflow,
)
from qchem_workbench.analysis.che import (
    CHEFreeEnergyRow,
    che_free_energy_table,
    load_che_pathway,
)
from qchem_workbench.analysis.conformers import select_lowest_energy_conformers
from qchem_workbench.analysis.convergence import (
    ConvergenceRow,
    convergence_table,
    load_convergence_study,
)
from qchem_workbench.analysis.quality_checks import QualityCheck, run_quality_checks
from qchem_workbench.analysis.reactions import ReactionEnergyRow
from qchem_workbench.analysis.reactions import load_pathway
from qchem_workbench.analysis.reactions import reaction_electronic_energy_table
from qchem_workbench.analysis.reactions import reaction_gibbs_free_energy_table
from qchem_workbench.analysis.result_matching import match_results_to_species
from qchem_workbench.analysis.screening import (
    build_descriptor_table,
    rank_descriptor_rows,
    write_descriptor_table_csv,
    write_ranked_candidates_csv,
)
from qchem_workbench.backends.ase_adapter import ASEUnavailableError, from_ase_atoms
from qchem_workbench.backends.ase_adsorption import place_adsorbate_from_yaml
from qchem_workbench.backends.ase_surface import (
    SUPPORTED_FCC_FACETS,
    build_fcc_surface,
    write_structure,
)
from qchem_workbench.backends.gaussian_input import (
    GAUSSIAN_TASK_PRESETS,
    GaussianInputOptions,
    gaussian_route_from_spec,
    render_gaussian_input,
)
from qchem_workbench.backends.gaussian_parser import parse_gaussian_output
from qchem_workbench.backends.gaussian_scheduler import (
    SCHEDULER_NAMES,
    render_gaussian_scheduler_script,
)
from qchem_workbench.backends.orca_input import (
    ORCA_TASK_PRESETS,
    ORCAInputOptions,
    render_orca_input,
)
from qchem_workbench.backends.orca_parser import parse_orca_output
from qchem_workbench.backends.pyscf_backend import (
    MissingOptionalDependencyError,
    PySCFBackend,
)
from qchem_workbench.backends.qe_input import (
    QEKPoints,
    QEInputSpec,
    render_qe_pw_input,
)
from qchem_workbench.backends.qe_parser import parse_qe_output
from qchem_workbench.backends.qe_pseudos import load_pseudopotential_manifest
from qchem_workbench.backends.registry import list_backends
from qchem_workbench.core.calculation import CalculationSpec
from qchem_workbench.core.geometry import read_xyz_frames, write_xyz_frames
from qchem_workbench.core.registry import load_species_registry
from qchem_workbench.core.result import CalculationResult
from qchem_workbench.core.species import Species
from qchem_workbench.campaigns import load_campaign_manifest
from qchem_workbench.core.structure import AtomisticStructure
from qchem_workbench.microkinetics.parameters import (
    load_rate_parameter_set,
    rate_parameter_set_from_mapping,
)
from qchem_workbench.microkinetics.plotting import (
    plot_rates_csv as plot_microkinetic_rates_csv,
    plot_sensitivity_csv as plot_microkinetic_sensitivity_csv,
    plot_steady_state_csv as plot_microkinetic_steady_state_csv,
    plot_trajectory_csv as plot_microkinetic_trajectory_csv,
    plot_uncertainty_csv as plot_microkinetic_uncertainty_csv,
)
from qchem_workbench.microkinetics.rates import (
    microkinetic_rate_analysis,
    write_rate_analysis_csv,
)
from qchem_workbench.microkinetics.schema import load_microkinetic_model
from qchem_workbench.microkinetics.sensitivity import (
    microkinetic_sensitivity,
    write_sensitivity_csv,
)
from qchem_workbench.microkinetics.uncertainty import (
    load_parameter_distributions,
    microkinetic_uncertainty_sample,
    parameter_distributions_from_mapping,
    write_uncertainty_csv,
)
from qchem_workbench.microkinetics.simulation import (
    SciPyUnavailableError,
    load_microkinetic_conditions,
    simulate_coverages,
    write_simulation_csv,
)
from qchem_workbench.projects.manifest import ProjectManifest, load_project_manifest
from qchem_workbench.reports.exports import (
    PROPERTY_EXPORT_TYPES,
    property_rows_for_type,
    property_rows_to_csv,
)
from qchem_workbench.reports.markdown import write_markdown_report
from qchem_workbench.reports.plotting import plot_pathway_from_csv
from qchem_workbench.reports.spectrum import SPECTRUM_TYPES, plot_vibrational_spectrum
from qchem_workbench.reports.triage import (
    classify_triage_results,
    write_failed_jobs_report,
)
from qchem_workbench.results.store import (
    RESULT_COLLECTION_SCHEMA_VERSION,
    load_result_collection,
)
from qchem_workbench.schema import check_schema_file
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

    schema_check_parser = subparsers.add_parser(
        "schema-check", help="detect and validate qchem-workbench schema files"
    )
    schema_check_parser.add_argument("path", type=Path)
    schema_check_parser.add_argument(
        "--write",
        action="store_true",
        help="write migrations when a future migration implementation supports it",
    )
    schema_check_parser.set_defaults(func=_schema_check_command)

    backends_parser = subparsers.add_parser(
        "backends", help="list registered backend capabilities"
    )
    backends_parser.add_argument(
        "--json", action="store_true", help="emit machine-readable JSON"
    )
    backends_parser.set_defaults(func=_backends_command)

    inspect_structure_parser = subparsers.add_parser(
        "inspect-structure", help="inspect an atomistic structure file"
    )
    inspect_structure_parser.add_argument("path", type=Path)
    inspect_structure_parser.set_defaults(func=_inspect_structure_command)

    convert_structure_parser = subparsers.add_parser(
        "convert-structure", help="convert atomistic structure files"
    )
    convert_structure_parser.add_argument("input", type=Path)
    convert_structure_parser.add_argument("output", type=Path)
    convert_structure_parser.set_defaults(func=_convert_structure_command)

    build_slab_parser = subparsers.add_parser(
        "build-slab", help="build an unrelaxed starting slab with optional ASE"
    )
    build_slab_parser.add_argument("--element", required=True)
    build_slab_parser.add_argument(
        "--facet", required=True, choices=SUPPORTED_FCC_FACETS
    )
    build_slab_parser.add_argument("--size", nargs=3, required=True, type=int)
    build_slab_parser.add_argument("--vacuum", required=True, type=float)
    build_slab_parser.add_argument("--out", required=True, type=Path)
    build_slab_parser.set_defaults(func=_build_slab_command)

    place_adsorbate_parser = subparsers.add_parser(
        "place-adsorbate",
        help="place an adsorbate starting geometry with optional ASE",
    )
    place_adsorbate_parser.add_argument("placement", type=Path)
    place_adsorbate_parser.add_argument("--out", required=True, type=Path)
    place_adsorbate_parser.set_defaults(func=_place_adsorbate_command)

    render_qe_parser = subparsers.add_parser(
        "render-qe", help="render a Quantum ESPRESSO pw.x input file"
    )
    render_qe_parser.add_argument("structure", type=Path)
    render_qe_parser.add_argument("--pseudo-map", required=True, type=Path)
    render_qe_parser.add_argument("--out", required=True, type=Path)
    render_qe_parser.add_argument("--calculation", default="scf")
    render_qe_parser.add_argument("--prefix")
    render_qe_parser.add_argument("--pseudo-dir", default="./pseudos")
    render_qe_parser.add_argument("--outdir", default="./tmp")
    render_qe_parser.add_argument("--ecutwfc", required=True, type=float)
    render_qe_parser.add_argument("--ecutrho", type=float)
    render_qe_parser.add_argument("--occupations")
    render_qe_parser.add_argument("--smearing")
    render_qe_parser.add_argument("--degauss", type=float)
    render_qe_parser.add_argument("--k-points", nargs=3, type=int, default=(1, 1, 1))
    render_qe_parser.add_argument("--k-shift", nargs=3, type=int, default=(0, 0, 0))
    render_qe_parser.add_argument(
        "--atomic-positions",
        choices=("angstrom", "crystal"),
        default="angstrom",
        help="ATOMIC_POSITIONS coordinate units to render",
    )
    render_qe_parser.add_argument(
        "--gamma-only",
        action="store_true",
        help="render K_POINTS gamma instead of automatic k-point grid",
    )
    render_qe_parser.add_argument(
        "--cell",
        nargs=3,
        type=float,
        metavar=("A", "B", "C"),
        help="orthorhombic cell lengths in angstrom for structures without a cell",
    )
    render_qe_parser.add_argument(
        "--periodic",
        action="store_true",
        help="mark the structure periodic in all three directions",
    )
    render_qe_parser.set_defaults(func=_render_qe_command)

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
    render_gaussian_parser.add_argument(
        "--job-folders",
        action="store_true",
        help="create one folder per species and place input files inside it",
    )
    render_gaussian_parser.add_argument(
        "--include-run-script",
        action="store_true",
        help="include a simple Gaussian run script template in each job folder",
    )
    render_gaussian_parser.add_argument(
        "--scheduler",
        choices=SCHEDULER_NAMES,
        help="include a scheduler script template; requires --job-folders",
    )
    render_gaussian_parser.set_defaults(func=_render_gaussian_command)

    render_orca_parser = subparsers.add_parser(
        "render-orca", help="render ORCA input files without running ORCA"
    )
    render_orca_parser.add_argument("registry", type=Path)
    render_orca_parser.add_argument("--method", required=True)
    render_orca_parser.add_argument("--basis", required=True)
    render_orca_parser.add_argument(
        "--task", required=True, choices=tuple(ORCA_TASK_PRESETS)
    )
    render_orca_parser.add_argument("--out", required=True, type=Path)
    render_orca_parser.add_argument(
        "--force", action="store_true", help="overwrite existing .inp files"
    )
    render_orca_parser.add_argument(
        "--job-folders",
        action="store_true",
        help="create one folder per species and place input files inside it",
    )
    render_orca_parser.add_argument(
        "--include-run-script",
        action="store_true",
        help="include a simple ORCA run script template in each job folder",
    )
    render_orca_parser.set_defaults(func=_render_orca_command)

    parse_gaussian_parser = subparsers.add_parser(
        "parse-gaussian", help="parse Gaussian .log and .out files"
    )
    parse_gaussian_parser.add_argument("path", type=Path)
    parse_gaussian_parser.add_argument("--out", required=True, type=Path)
    parse_gaussian_parser.add_argument("--csv", type=Path)
    parse_gaussian_parser.set_defaults(func=_parse_gaussian_command)

    parse_orca_parser = subparsers.add_parser(
        "parse-orca", help="parse ORCA .out files"
    )
    parse_orca_parser.add_argument("path", type=Path)
    parse_orca_parser.add_argument("--out", required=True, type=Path)
    parse_orca_parser.add_argument("--csv", type=Path)
    parse_orca_parser.set_defaults(func=_parse_orca_command)

    parse_qe_parser = subparsers.add_parser(
        "parse-qe", help="parse Quantum ESPRESSO pw.x output files"
    )
    parse_qe_parser.add_argument("path", type=Path)
    parse_qe_parser.add_argument("--out", required=True, type=Path)
    parse_qe_parser.add_argument("--csv", type=Path)
    parse_qe_parser.set_defaults(func=_parse_qe_command)

    check_results_parser = subparsers.add_parser(
        "check-results", help="run quality checks on a result collection"
    )
    check_results_parser.add_argument("results", type=Path)
    check_results_parser.add_argument("--species", type=Path)
    check_results_parser.add_argument(
        "--json", action="store_true", help="emit machine-readable JSON"
    )
    check_results_parser.set_defaults(func=_check_results_command)

    reaction_table_parser = subparsers.add_parser(
        "reaction-table", help="compute generic reaction electronic/Gibbs tables"
    )
    reaction_table_parser.add_argument("pathway", type=Path)
    reaction_table_parser.add_argument("results", type=Path)
    reaction_table_parser.add_argument(
        "--quantity", required=True, choices=("electronic", "gibbs")
    )
    reaction_table_parser.add_argument("--out", required=True, type=Path)
    reaction_table_parser.set_defaults(func=_reaction_table_command)

    adsorption_table_parser = subparsers.add_parser(
        "adsorption-table", help="compute generic adsorption energy/free-energy tables"
    )
    adsorption_table_parser.add_argument("adsorption", type=Path)
    adsorption_table_parser.add_argument("results", type=Path)
    adsorption_table_parser.add_argument(
        "--quantity", required=True, choices=("electronic", "gibbs")
    )
    adsorption_table_parser.add_argument("--out", required=True, type=Path)
    adsorption_table_parser.set_defaults(func=_adsorption_table_command)

    che_table_parser = subparsers.add_parser(
        "che-table", help="compute transparent CHE-style free-energy tables"
    )
    che_table_parser.add_argument("pathway", type=Path)
    che_table_parser.add_argument("results", type=Path)
    che_table_parser.add_argument("--out", required=True, type=Path)
    che_table_parser.set_defaults(func=_che_table_command)

    convergence_table_parser = subparsers.add_parser(
        "convergence-table",
        help="compute a plane-wave convergence study table",
    )
    convergence_table_parser.add_argument("study", type=Path)
    convergence_table_parser.add_argument("results", type=Path)
    convergence_table_parser.add_argument("--out", required=True, type=Path)
    convergence_table_parser.set_defaults(func=_convergence_table_command)

    select_conformers_parser = subparsers.add_parser(
        "select-conformers", help="select lowest-energy conformer results"
    )
    select_conformers_parser.add_argument("results", type=Path)
    select_conformers_parser.add_argument(
        "--quantity", required=True, choices=("electronic", "gibbs")
    )
    select_conformers_parser.add_argument("--out", required=True, type=Path)
    select_conformers_parser.add_argument(
        "--allow-mixed",
        action="store_true",
        help="allow comparison across mixed backend/method/basis/task settings",
    )
    select_conformers_parser.set_defaults(func=_select_conformers_command)

    report_parser = subparsers.add_parser(
        "report", help="generate a Markdown workflow report"
    )
    report_parser.add_argument("results", type=Path)
    report_parser.add_argument("--species", type=Path)
    report_parser.add_argument("--out", required=True, type=Path)
    report_parser.set_defaults(func=_report_command)

    export_properties_parser = subparsers.add_parser(
        "export-properties", help="export parsed molecular properties to CSV"
    )
    export_properties_parser.add_argument("results", type=Path)
    export_properties_parser.add_argument(
        "--type",
        choices=PROPERTY_EXPORT_TYPES,
        help="property table to export; omit to export all non-empty property tables",
    )
    export_properties_parser.add_argument("--out", required=True, type=Path)
    export_properties_parser.set_defaults(func=_export_properties_command)

    plot_pathway_parser = subparsers.add_parser(
        "plot-pathway", help="plot a generic reaction pathway table"
    )
    plot_pathway_parser.add_argument("reaction_table", type=Path)
    plot_pathway_parser.add_argument("--out", required=True, type=Path)
    plot_pathway_parser.add_argument("--title")
    plot_pathway_parser.set_defaults(func=_plot_pathway_command)

    plot_spectrum_parser = subparsers.add_parser(
        "plot-spectrum", help="plot a broadened vibrational spectrum"
    )
    plot_spectrum_parser.add_argument("results", type=Path)
    plot_spectrum_parser.add_argument("--species", required=True)
    plot_spectrum_parser.add_argument("--type", required=True, choices=SPECTRUM_TYPES)
    plot_spectrum_parser.add_argument("--out", required=True, type=Path)
    plot_spectrum_parser.add_argument("--csv", type=Path)
    plot_spectrum_parser.add_argument("--width", type=float, default=20.0)
    plot_spectrum_parser.add_argument("--step", type=float, default=1.0)
    plot_spectrum_parser.set_defaults(func=_plot_spectrum_command)

    descriptor_table_parser = subparsers.add_parser(
        "descriptor-table", help="build a screening descriptor CSV"
    )
    descriptor_table_parser.add_argument("campaign", type=Path)
    descriptor_table_parser.add_argument("results", type=Path)
    descriptor_table_parser.add_argument("--out", required=True, type=Path)
    descriptor_table_parser.set_defaults(func=_descriptor_table_command)

    rank_candidates_parser = subparsers.add_parser(
        "rank-candidates", help="apply explicit ranking rules to descriptor CSV"
    )
    rank_candidates_parser.add_argument("campaign", type=Path)
    rank_candidates_parser.add_argument("descriptors", type=Path)
    rank_candidates_parser.add_argument("--out", required=True, type=Path)
    rank_candidates_parser.set_defaults(func=_rank_candidates_command)

    active_learning_parser = subparsers.add_parser(
        "active-learning",
        help="file-based active-learning and BO handoff helpers",
    )
    active_learning_subparsers = active_learning_parser.add_subparsers(
        dest="active_learning_command",
        required=True,
    )
    active_learning_dataset_parser = active_learning_subparsers.add_parser(
        "build-dataset",
        help="build a transparent active-learning descriptor dataset",
    )
    active_learning_dataset_parser.add_argument("campaign", type=Path)
    active_learning_dataset_parser.add_argument("--out", required=True, type=Path)
    active_learning_dataset_parser.set_defaults(
        func=_active_learning_build_dataset_command
    )
    active_learning_score_parser = active_learning_subparsers.add_parser(
        "score-dataset",
        help="apply explicit active-learning objective and constraint rules",
    )
    active_learning_score_parser.add_argument("dataset", type=Path)
    active_learning_score_parser.add_argument("objectives", type=Path)
    active_learning_score_parser.add_argument("--out", required=True, type=Path)
    active_learning_score_parser.set_defaults(
        func=_active_learning_score_dataset_command
    )
    active_learning_export_parser = active_learning_subparsers.add_parser(
        "export-bo-forge",
        help="export a file-based BO Forge interchange folder",
    )
    active_learning_export_parser.add_argument("campaign", type=Path)
    active_learning_export_parser.add_argument("dataset", type=Path)
    active_learning_export_parser.add_argument("--out", required=True, type=Path)
    active_learning_export_parser.set_defaults(func=_active_learning_export_bo_forge_command)

    microkinetics_parser = subparsers.add_parser(
        "microkinetics",
        help="run transparent microkinetic workflow helpers",
    )
    microkinetics_subparsers = microkinetics_parser.add_subparsers(
        dest="microkinetics_command",
        required=True,
    )
    microkinetics_simulate_parser = microkinetics_subparsers.add_parser(
        "simulate",
        help="simulate surface coverages with optional SciPy",
    )
    microkinetics_simulate_parser.add_argument("model", type=Path)
    microkinetics_simulate_parser.add_argument("--conditions", required=True, type=Path)
    microkinetics_simulate_parser.add_argument("--out", required=True, type=Path)
    microkinetics_simulate_parser.set_defaults(func=_microkinetics_simulate_command)
    microkinetics_steady_parser = microkinetics_subparsers.add_parser(
        "steady-state",
        help="solve steady-state coverages with optional SciPy",
    )
    microkinetics_steady_parser.add_argument("model", type=Path)
    microkinetics_steady_parser.add_argument("--conditions", required=True, type=Path)
    microkinetics_steady_parser.add_argument("--out", required=True, type=Path)
    microkinetics_steady_parser.add_argument("--tolerance", type=float, default=1e-8)
    microkinetics_steady_parser.set_defaults(func=_microkinetics_steady_state_command)
    microkinetics_rates_parser = microkinetics_subparsers.add_parser(
        "rates",
        help="compute step rates, species rates, and optional TOF",
    )
    microkinetics_rates_parser.add_argument("model", type=Path)
    microkinetics_rates_parser.add_argument("--state", required=True, type=Path)
    microkinetics_rates_parser.add_argument("--conditions", required=True, type=Path)
    microkinetics_rates_parser.add_argument("--out", required=True, type=Path)
    microkinetics_rates_parser.add_argument("--tof-species")
    microkinetics_rates_parser.add_argument("--site-count", type=float)
    microkinetics_rates_parser.set_defaults(func=_microkinetics_rates_command)
    microkinetics_sensitivity_parser = microkinetics_subparsers.add_parser(
        "sensitivity",
        help="finite-difference sensitivity to log-rate-constant perturbations",
    )
    microkinetics_sensitivity_parser.add_argument("model", type=Path)
    microkinetics_sensitivity_parser.add_argument("--conditions", required=True, type=Path)
    microkinetics_sensitivity_parser.add_argument("--observable", required=True)
    microkinetics_sensitivity_parser.add_argument("--out", required=True, type=Path)
    microkinetics_sensitivity_parser.add_argument(
        "--perturbation",
        type=float,
        default=1e-2,
        help="positive perturbation in ln(k)",
    )
    microkinetics_sensitivity_parser.add_argument("--site-count", type=float)
    microkinetics_sensitivity_parser.set_defaults(
        func=_microkinetics_sensitivity_command
    )
    microkinetics_sample_parser = microkinetics_subparsers.add_parser(
        "sample",
        help="sample user-provided kinetic parameter distributions",
    )
    microkinetics_sample_parser.add_argument("model", type=Path)
    microkinetics_sample_parser.add_argument("--conditions", required=True, type=Path)
    microkinetics_sample_parser.add_argument("--n", required=True, type=int)
    microkinetics_sample_parser.add_argument("--seed", type=int)
    microkinetics_sample_parser.add_argument("--observable")
    microkinetics_sample_parser.add_argument("--site-count", type=float)
    microkinetics_sample_parser.add_argument("--out", required=True, type=Path)
    microkinetics_sample_parser.set_defaults(func=_microkinetics_sample_command)
    microkinetics_plot_trajectory_parser = microkinetics_subparsers.add_parser(
        "plot-trajectory",
        help="plot coverage versus time from a trajectory CSV",
    )
    microkinetics_plot_trajectory_parser.add_argument("trajectory", type=Path)
    microkinetics_plot_trajectory_parser.add_argument("--out", required=True, type=Path)
    microkinetics_plot_trajectory_parser.set_defaults(
        func=_microkinetics_plot_trajectory_command
    )
    microkinetics_plot_steady_parser = microkinetics_subparsers.add_parser(
        "plot-steady-state",
        help="plot steady-state coverages from a steady-state CSV",
    )
    microkinetics_plot_steady_parser.add_argument("steady_state", type=Path)
    microkinetics_plot_steady_parser.add_argument("--out", required=True, type=Path)
    microkinetics_plot_steady_parser.set_defaults(
        func=_microkinetics_plot_steady_state_command
    )
    microkinetics_plot_rates_parser = microkinetics_subparsers.add_parser(
        "plot-rates",
        help="plot species production rates from a rate CSV",
    )
    microkinetics_plot_rates_parser.add_argument("rates", type=Path)
    microkinetics_plot_rates_parser.add_argument("--out", required=True, type=Path)
    microkinetics_plot_rates_parser.set_defaults(func=_microkinetics_plot_rates_command)
    microkinetics_plot_sensitivity_parser = microkinetics_subparsers.add_parser(
        "plot-sensitivity",
        help="plot finite-difference sensitivity rows",
    )
    microkinetics_plot_sensitivity_parser.add_argument("sensitivity", type=Path)
    microkinetics_plot_sensitivity_parser.add_argument("--out", required=True, type=Path)
    microkinetics_plot_sensitivity_parser.set_defaults(
        func=_microkinetics_plot_sensitivity_command
    )
    microkinetics_plot_uncertainty_parser = microkinetics_subparsers.add_parser(
        "plot-uncertainty",
        help="plot uncertainty summary intervals when present",
    )
    microkinetics_plot_uncertainty_parser.add_argument("uncertainty", type=Path)
    microkinetics_plot_uncertainty_parser.add_argument("--out", required=True, type=Path)
    microkinetics_plot_uncertainty_parser.set_defaults(
        func=_microkinetics_plot_uncertainty_command
    )

    run_project_parser = subparsers.add_parser(
        "run-project", help="run explicitly configured project manifest steps"
    )
    run_project_parser.add_argument("manifest", type=Path)
    run_project_parser.set_defaults(func=_run_project_command)

    triage_parser = subparsers.add_parser(
        "triage", help="generate a failed-job triage Markdown report"
    )
    triage_parser.add_argument("results", type=Path)
    triage_parser.add_argument("--out", required=True, type=Path)
    triage_parser.set_defaults(func=_triage_command)
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


def _schema_check_command(args: argparse.Namespace) -> int:
    report = check_schema_file(args.path, write=args.write)
    print(f"path\t{report.path}")
    print(f"file_type\t{report.file_type or 'unknown'}")
    print(f"schema_version\t{'' if report.schema_version is None else report.schema_version}")
    print(f"valid\t{report.valid}")
    print(f"migration\t{report.migration.message}")
    for problem in report.problems:
        print(f"problem\t{problem}")
    return 0 if report.valid else 1


def _backends_command(args: argparse.Namespace) -> int:
    backends = list_backends()
    if args.json:
        print(json.dumps([backend.to_dict() for backend in backends], indent=2))
        return 0

    print(
        "backend\tinput_rendering\toutput_parsing\texecution\tmolecular\tperiodic\tproperties"
    )
    for backend in backends:
        capabilities = backend.capabilities
        print(
            f"{backend.name}\t{capabilities.input_rendering}\t"
            f"{capabilities.output_parsing}\t{capabilities.execution}\t"
            f"{capabilities.molecular_support}\t"
            f"{capabilities.periodic_support}\t"
            f"{';'.join(capabilities.properties_supported)}"
        )
    return 0


def _inspect_structure_command(args: argparse.Namespace) -> int:
    try:
        structures = _read_structure_file(args.path)
    except (OSError, ValueError, ASEUnavailableError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    first = structures[0]
    print(f"path\t{args.path}")
    print(f"frames\t{len(structures)}")
    print(f"atoms\t{len(first.atoms)}")
    print(f"formula\t{_formula_from_atoms(first.atoms)}")
    print(f"periodic\t{first.is_periodic}")
    print(f"pbc\t{' '.join(str(flag) for flag in first.pbc)}")
    if first.cell is not None:
        print(f"cell\t{json.dumps(first.cell)}")
    else:
        print("cell\t")
    return 0


def _convert_structure_command(args: argparse.Namespace) -> int:
    try:
        _convert_structure_file(args.input, args.output)
    except (OSError, ValueError, ASEUnavailableError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    print(f"Converted {args.input} to {args.output}.")
    return 0


def _build_slab_command(args: argparse.Namespace) -> int:
    try:
        structure = build_fcc_surface(
            element=args.element,
            facet=args.facet,
            size=tuple(args.size),
            vacuum=args.vacuum,
        )
        write_structure(structure, args.out)
    except (OSError, ValueError, ASEUnavailableError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    print(f"Wrote starting slab to {args.out}.")
    print(f"atoms\t{len(structure.atoms)}")
    print(f"warning\t{structure.metadata['warning']}")
    return 0


def _place_adsorbate_command(args: argparse.Namespace) -> int:
    try:
        structure = place_adsorbate_from_yaml(args.placement, args.out)
    except (OSError, ValueError, ASEUnavailableError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    print(f"Wrote starting slab+adsorbate structure to {args.out}.")
    print(f"atoms\t{len(structure.atoms)}")
    print(f"warning\t{structure.metadata['warning']}")
    return 0


def _render_qe_command(args: argparse.Namespace) -> int:
    try:
        structures = _read_structure_file(args.structure)
        if len(structures) != 1:
            raise ValueError("render-qe requires a single-frame structure file")
        structure = _structure_with_cli_cell(
            structures[0],
            args.cell,
            periodic=args.periodic,
        )
        pseudopotentials, atomic_masses = _load_qe_pseudo_map(args.pseudo_map)
        k_points = (
            QEKPoints(mode="gamma")
            if args.gamma_only
            else QEKPoints(grid=tuple(args.k_points), shift=tuple(args.k_shift))
        )
        spec = QEInputSpec(
            calculation=args.calculation,
            prefix=args.prefix or args.structure.stem,
            pseudo_dir=args.pseudo_dir,
            outdir=args.outdir,
            ecutwfc=args.ecutwfc,
            ecutrho=args.ecutrho,
            occupations=args.occupations,
            smearing=args.smearing,
            degauss=args.degauss,
            k_points=k_points,
            pseudopotentials=pseudopotentials,
            atomic_masses=atomic_masses,
            atomic_position_units=args.atomic_positions,
        )
        rendered = render_qe_pw_input(structure, spec)
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(rendered, encoding="utf-8")
    except (OSError, ValueError, ASEUnavailableError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    print(f"Wrote QE pw.x input to {args.out}.")
    print(
        "warning\tInspect pseudopotentials, cutoffs, k-points, cell, and "
        "calculation settings before production use."
    )
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
            job_folders=args.job_folders,
            include_run_script=args.include_run_script,
            scheduler=args.scheduler,
        )
    except (OSError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    print("species\tfile")
    for species_name, path in generated:
        print(f"{species_name}\t{path}")
    return 0


def _render_orca_command(args: argparse.Namespace) -> int:
    try:
        species_list = load_species_registry(args.registry)
        spec = CalculationSpec(
            backend="orca",
            method=args.method,
            basis=args.basis,
            task=args.task,
        )
        generated = _render_orca_files(
            species_list=species_list,
            spec=spec,
            out_dir=args.out,
            force=args.force,
            job_folders=args.job_folders,
            include_run_script=args.include_run_script,
        )
    except (OSError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    print("species\tfile")
    for species_name, path in generated:
        print(f"{species_name}\t{path}")
    return 0


def _parse_gaussian_command(args: argparse.Namespace) -> int:
    try:
        paths = _gaussian_output_paths(args.path)
        results = _parse_gaussian_outputs(paths)
        _write_parsed_result_collection(args.out, results, parser="gaussian")
        if args.csv is not None:
            _write_parsed_result_csv(args.csv, results)
    except OSError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    print("file\tsuccess\telectronic_energy_hartree\twarnings")
    for result in results:
        source_path = result.source_path if result.source_path else ""
        energy = (
            ""
            if result.electronic_energy_hartree is None
            else f"{result.electronic_energy_hartree:.12g}"
        )
        print(f"{source_path}\t{result.success}\t{energy}\t{len(result.warnings)}")
    return 0


def _parse_orca_command(args: argparse.Namespace) -> int:
    try:
        paths = _orca_output_paths(args.path)
        results = _parse_orca_outputs(paths)
        _write_parsed_result_collection(args.out, results, parser="orca")
        if args.csv is not None:
            _write_parsed_result_csv(args.csv, results)
    except OSError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    print("file\tsuccess\telectronic_energy_hartree\twarnings")
    for result in results:
        source_path = result.source_path if result.source_path else ""
        energy = (
            ""
            if result.electronic_energy_hartree is None
            else f"{result.electronic_energy_hartree:.12g}"
        )
        print(f"{source_path}\t{result.success}\t{energy}\t{len(result.warnings)}")
    return 0


def _parse_qe_command(args: argparse.Namespace) -> int:
    try:
        paths = _qe_output_paths(args.path)
        results = _parse_qe_outputs(paths)
        _write_parsed_result_collection(args.out, results, parser="qe")
        if args.csv is not None:
            _write_parsed_result_csv(args.csv, results)
    except OSError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    print("file\tsuccess\telectronic_energy_hartree\twarnings")
    for result in results:
        source_path = result.source_path if result.source_path else ""
        energy = (
            ""
            if result.electronic_energy_hartree is None
            else f"{result.electronic_energy_hartree:.12g}"
        )
        print(f"{source_path}\t{result.success}\t{energy}\t{len(result.warnings)}")
    return 0


def _check_results_command(args: argparse.Namespace) -> int:
    try:
        results = load_result_collection(args.results)
        checks = _quality_checks_for_results(results, args.species)
    except (OSError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    if args.json:
        print(json.dumps(_quality_check_payload(checks), indent=2, sort_keys=True))
    else:
        _print_quality_check_summary(checks)
    return 1 if any(check.severity == "error" for check in checks) else 0


def _reaction_table_command(args: argparse.Namespace) -> int:
    try:
        pathway = load_pathway(args.pathway)
        results = load_result_collection(args.results)
        rows = _reaction_energy_rows(pathway, results, args.quantity)
        _write_reaction_table_csv(args.out, rows)
    except (OSError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    print("reaction_id\tquantity\tcomplete\tdelta_hartree\tmissing_species")
    for row in rows:
        delta_hartree = "" if row.delta_hartree is None else f"{row.delta_hartree:.12g}"
        print(
            f"{row.reaction_id}\t{row.quantity}\t{row.complete}\t"
            f"{delta_hartree}\t{';'.join(row.missing_species)}"
        )
    return 0


def _adsorption_table_command(args: argparse.Namespace) -> int:
    try:
        workflow = load_adsorption_workflow(args.adsorption)
        results = load_result_collection(args.results)
        rows = _adsorption_energy_rows(workflow, results, args.quantity)
        _write_adsorption_table_csv(args.out, rows)
    except (OSError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    print(
        "system_id\tquantity\tcomplete\tadsorption_value_hartree\tmissing"
    )
    for row in rows:
        energy = (
            ""
            if row.adsorption_hartree is None
            else f"{row.adsorption_hartree:.12g}"
        )
        print(
            f"{row.system_id}\t{row.quantity}\t{row.complete}\t"
            f"{energy}\t{';'.join(row.missing)}"
        )
    return 0


def _che_table_command(args: argparse.Namespace) -> int:
    try:
        pathway = load_che_pathway(args.pathway)
        results = load_result_collection(args.results)
        rows = che_free_energy_table(pathway, results)
        _write_che_table_csv(args.out, rows)
    except (OSError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    print("reaction_id\tcomplete\tuncorrected_delta_g_ev\tcorrected_delta_g_ev\tmissing")
    for row in rows:
        uncorrected = (
            ""
            if row.uncorrected_delta_g_ev is None
            else f"{row.uncorrected_delta_g_ev:.12g}"
        )
        corrected = (
            ""
            if row.corrected_delta_g_ev is None
            else f"{row.corrected_delta_g_ev:.12g}"
        )
        print(
            f"{row.reaction_id}\t{row.complete}\t{uncorrected}\t"
            f"{corrected}\t{';'.join(row.missing_species)}"
        )
    return 0


def _convergence_table_command(args: argparse.Namespace) -> int:
    try:
        study = load_convergence_study(args.study)
        results = load_result_collection(args.results)
        rows = convergence_table(study, results)
        _write_convergence_table_csv(args.out, rows)
    except (OSError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    print("variable_value\tcomplete\tenergy_ev\tdelta_ev\twithin_tolerance\tmissing")
    for row in rows:
        energy = "" if row.energy_ev is None else f"{row.energy_ev:.12g}"
        delta = (
            ""
            if row.delta_from_previous_ev is None
            else f"{row.delta_from_previous_ev:.12g}"
        )
        within = "" if row.within_tolerance is None else str(row.within_tolerance)
        print(
            f"{row.variable_value}\t{row.complete}\t{energy}\t{delta}\t"
            f"{within}\t{row.missing_reason or ''}"
        )
    return 0


def _select_conformers_command(args: argparse.Namespace) -> int:
    try:
        results = load_result_collection(args.results)
        report = select_lowest_energy_conformers(
            results,
            args.quantity,
            allow_mixed=args.allow_mixed,
        )
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(
            json.dumps(report.to_dict(), indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
    except (OSError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    print("species\tconformer\tenergy_hartree\twarnings")
    for selection in report.selections:
        energy = (
            ""
            if selection.selected_energy_hartree is None
            else f"{selection.selected_energy_hartree:.12g}"
        )
        conformer_id = selection.selected_conformer_id or ""
        print(
            f"{selection.species_name}\t{conformer_id}\t{energy}\t"
            f"{len(selection.warnings)}"
        )
    return 0


def _report_command(args: argparse.Namespace) -> int:
    try:
        results = load_result_collection(args.results)
        species = (
            load_species_registry(args.species) if args.species is not None else None
        )
        checks = _quality_checks_for_results(results, args.species)
        write_markdown_report(
            args.out,
            results,
            species=species,
            quality_checks=checks,
        )
    except (OSError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    print(f"Wrote Markdown report to {args.out}.")
    return 0


def _export_properties_command(args: argparse.Namespace) -> int:
    try:
        results = load_result_collection(args.results)
        if args.type is not None:
            rows = property_rows_for_type(results, args.type)
            args.out.parent.mkdir(parents=True, exist_ok=True)
            args.out.write_text(property_rows_to_csv(args.type, rows), encoding="utf-8")
            if not rows:
                print(
                    f"No {args.type} property rows found; "
                    f"wrote header to {args.out}."
                )
            else:
                print(f"Wrote {len(rows)} {args.type} property row(s) to {args.out}.")
            return 0

        written: list[tuple[str, int, Path]] = []
        args.out.mkdir(parents=True, exist_ok=True)
        for property_type in PROPERTY_EXPORT_TYPES:
            rows = property_rows_for_type(results, property_type)
            if not rows:
                continue
            output_path = args.out / f"{property_type}.csv"
            output_path.write_text(
                property_rows_to_csv(property_type, rows),
                encoding="utf-8",
            )
            written.append((property_type, len(rows), output_path))
    except (OSError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    if not written:
        print("No property rows found; no files written.")
        return 0

    for property_type, row_count, output_path in written:
        print(f"Wrote {row_count} {property_type} property row(s) to {output_path}.")
    return 0


def _plot_pathway_command(args: argparse.Namespace) -> int:
    try:
        plot_pathway_from_csv(args.reaction_table, args.out, title=args.title)
    except OSError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    print(f"Wrote pathway plot to {args.out}.")
    return 0


def _plot_spectrum_command(args: argparse.Namespace) -> int:
    try:
        results = load_result_collection(args.results)
        result = _result_for_species(results, args.species)
        plot_path, csv_path = plot_vibrational_spectrum(
            result,
            args.out,
            spectrum_type=args.type,
            csv_path=args.csv,
            width_cm1=args.width,
            step_cm1=args.step,
        )
    except (OSError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    print(f"Wrote {args.type.upper()} spectrum plot to {plot_path}.")
    print(f"Wrote broadened spectrum CSV to {csv_path}.")
    return 0


def _descriptor_table_command(args: argparse.Namespace) -> int:
    try:
        campaign = load_campaign_manifest(args.campaign)
        results = load_result_collection(args.results)
        checks = run_quality_checks(results)
        table = build_descriptor_table(
            campaign,
            results,
            quality_checks=checks,
        )
        write_descriptor_table_csv(args.out, table)
    except (OSError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    print(f"Wrote descriptor table for {len(table.rows)} candidate(s) to {args.out}.")
    return 0


def _rank_candidates_command(args: argparse.Namespace) -> int:
    try:
        campaign = load_campaign_manifest(args.campaign)
        descriptor_rows, descriptor_headers = _read_dict_csv(args.descriptors)
        table = rank_descriptor_rows(campaign, descriptor_rows, descriptor_headers)
        write_ranked_candidates_csv(args.out, table)
    except (OSError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    ranked_rows = [row for row in table.rows if row["rank_status"] == "ranked"]
    print("rank\tcandidate_id\tscore")
    for row in ranked_rows[:10]:
        print(f"{row['rank']}\t{row.get('candidate_id', '')}\t{row['rank_score']}")
    if not ranked_rows:
        print("No ranked candidates.")
    excluded_count = len(table.rows) - len(ranked_rows)
    if excluded_count:
        print(f"Excluded candidates\t{excluded_count}")
    print(f"Wrote ranked candidates to {args.out}.")
    return 0


def _active_learning_build_dataset_command(args: argparse.Namespace) -> int:
    try:
        campaign = load_active_learning_campaign(args.campaign)
        dataset = build_active_learning_dataset(campaign)
        write_descriptor_dataset_csv(dataset, args.out)
    except (OSError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    print(
        f"Wrote active-learning dataset with {len(dataset.rows)} candidate(s) "
        f"and {len(dataset.headers)} column(s) to {args.out}."
    )
    return 0


def _active_learning_score_dataset_command(args: argparse.Namespace) -> int:
    try:
        rows, headers = _read_dict_csv(args.dataset)
        spec = load_objective_spec(args.objectives)
        scored = score_dataset_rows(rows, headers, spec)
        write_scored_dataset_csv(scored, args.out)
    except (OSError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    ranked = sum(1 for row in scored.rows if row["al_status"] == "ranked")
    print(f"Wrote scored dataset with {ranked} ranked candidate(s) to {args.out}.")
    return 0


def _active_learning_export_bo_forge_command(args: argparse.Namespace) -> int:
    try:
        campaign = load_active_learning_campaign(args.campaign)
        rows, headers = _read_dict_csv(args.dataset)
        summary = export_bo_forge_interchange(campaign, rows, headers, args.out)
    except (OSError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    print(f"Wrote BO Forge interchange folder to {summary.output_dir}.")
    print(f"candidates\t{summary.candidate_count}")
    print(f"observations\t{summary.observation_count}")
    for warning in summary.warnings:
        print(f"warning\t{warning}")
    return 0


def _microkinetics_simulate_command(args: argparse.Namespace) -> int:
    try:
        model = load_microkinetic_model(args.model)
        conditions = load_microkinetic_conditions(args.conditions)
        parameters = _load_microkinetic_rate_parameters(conditions)
        result = simulate_coverages(
            model,
            parameters,
            conditions.initial_coverages,
            conditions.variables,
            conditions.time_grid,
            temperature_K=conditions.temperature_K,
        )
        write_simulation_csv(result, args.out)
    except (OSError, ValueError, KeyError, SciPyUnavailableError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    print("time_points\tspecies\tsuccess\twarnings")
    print(
        f"{len(result.times)}\t{';'.join(sorted(result.coverages))}\t"
        f"{result.success}\t{len(result.warnings)}"
    )
    for warning in result.warnings:
        print(f"warning\t{warning}")
    print(f"Wrote microkinetic trajectory to {args.out}.")
    return 0 if result.success else 1


def _microkinetics_steady_state_command(args: argparse.Namespace) -> int:
    try:
        from qchem_workbench.microkinetics.simulation import (
            solve_steady_state,
            write_steady_state_csv,
        )

        model = load_microkinetic_model(args.model)
        conditions = load_microkinetic_conditions(args.conditions)
        parameters = _load_microkinetic_rate_parameters(conditions)
        result = solve_steady_state(
            model,
            parameters,
            conditions.initial_coverages,
            conditions.variables,
            temperature_K=conditions.temperature_K,
            tolerance=args.tolerance,
        )
        write_steady_state_csv(result, args.out)
    except (OSError, ValueError, KeyError, SciPyUnavailableError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    print("species\tcoverage\tresidual")
    for species_id in sorted(result.coverages):
        print(
            f"{species_id}\t{result.coverages[species_id]:.12g}\t"
            f"{result.residuals[species_id]:.12g}"
        )
    print(f"success\t{result.success}")
    print(f"max_abs_residual\t{result.max_abs_residual:.12g}")
    for warning in result.warnings:
        print(f"warning\t{warning}")
    print(f"Wrote microkinetic steady state to {args.out}.")
    return 0 if result.success else 1


def _microkinetics_rates_command(args: argparse.Namespace) -> int:
    try:
        model = load_microkinetic_model(args.model)
        conditions = load_microkinetic_conditions(args.conditions)
        parameters = _load_microkinetic_rate_parameters(conditions)
        state = _load_microkinetic_state_csv(args.state)
        analysis = microkinetic_rate_analysis(
            model,
            parameters,
            state,
            conditions.variables,
            temperature_K=conditions.temperature_K,
            tof_species=args.tof_species,
            active_site_count=args.site_count,
        )
        write_rate_analysis_csv(analysis, args.out)
    except (OSError, ValueError, KeyError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    print("row_type\tid\trate\tunit")
    for row in analysis.to_rows():
        rate = "" if row["rate"] is None else f"{row['rate']:.12g}"
        print(f"{row['row_type']}\t{row['id']}\t{rate}\t{row['unit'] or ''}")
    for warning in analysis.warnings:
        print(f"warning\t{warning}")
    print(f"Wrote microkinetic rate table to {args.out}.")
    return 0


def _microkinetics_sensitivity_command(args: argparse.Namespace) -> int:
    try:
        model = load_microkinetic_model(args.model)
        conditions = load_microkinetic_conditions(args.conditions)
        parameters = _load_microkinetic_rate_parameters(conditions)
        rows = microkinetic_sensitivity(
            model,
            parameters,
            conditions.initial_coverages,
            conditions.variables,
            observable=args.observable,
            temperature_K=conditions.temperature_K,
            perturbation_ln=args.perturbation,
            active_site_count=args.site_count,
        )
        write_sensitivity_csv(rows, args.out)
    except (OSError, ValueError, KeyError, SciPyUnavailableError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    print("parameter_id\tobservable\tsensitivity\twarnings")
    for row in rows:
        sensitivity = "" if row.sensitivity is None else f"{row.sensitivity:.12g}"
        print(
            f"{row.parameter_id}\t{row.observable}\t{sensitivity}\t"
            f"{';'.join(row.warnings)}"
        )
    print(f"Wrote microkinetic sensitivity table to {args.out}.")
    return 0 if all(row.baseline_converged for row in rows) else 1


def _microkinetics_sample_command(args: argparse.Namespace) -> int:
    try:
        model = load_microkinetic_model(args.model)
        conditions = load_microkinetic_conditions(args.conditions)
        observable = args.observable or conditions.observable
        if observable is None:
            raise ValueError(
                "an observable is required; pass --observable or set conditions.observable"
            )
        distributions = _load_microkinetic_parameter_distributions(conditions)
        result = microkinetic_uncertainty_sample(
            model,
            distributions,
            conditions.initial_coverages,
            conditions.variables,
            observable=observable,
            n_samples=args.n,
            seed=args.seed,
            temperature_K=conditions.temperature_K,
            active_site_count=args.site_count,
        )
        write_uncertainty_csv(result, args.out)
    except (OSError, ValueError, KeyError, SciPyUnavailableError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    summary = result.summary
    print("observable\tsuccess_count\tfailure_count\tmean\tq05\tq95")
    mean = "" if summary.mean is None else f"{summary.mean:.12g}"
    q05 = "" if summary.q05 is None else f"{summary.q05:.12g}"
    q95 = "" if summary.q95 is None else f"{summary.q95:.12g}"
    print(
        f"{summary.observable}\t{summary.success_count}\t"
        f"{summary.failure_count}\t{mean}\t{q05}\t{q95}"
    )
    print(f"Wrote microkinetic uncertainty summary to {args.out}.")
    return 0 if summary.failure_count == 0 else 1


def _microkinetics_plot_trajectory_command(args: argparse.Namespace) -> int:
    try:
        plot_microkinetic_trajectory_csv(args.trajectory, args.out)
    except (OSError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    print(f"Wrote microkinetic trajectory plot to {args.out}.")
    return 0


def _microkinetics_plot_steady_state_command(args: argparse.Namespace) -> int:
    try:
        plot_microkinetic_steady_state_csv(args.steady_state, args.out)
    except (OSError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    print(f"Wrote microkinetic steady-state plot to {args.out}.")
    return 0


def _microkinetics_plot_rates_command(args: argparse.Namespace) -> int:
    try:
        plot_microkinetic_rates_csv(args.rates, args.out)
    except (OSError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    print(f"Wrote microkinetic rate plot to {args.out}.")
    return 0


def _microkinetics_plot_sensitivity_command(args: argparse.Namespace) -> int:
    try:
        plot_microkinetic_sensitivity_csv(args.sensitivity, args.out)
    except (OSError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    print(f"Wrote microkinetic sensitivity plot to {args.out}.")
    return 0


def _microkinetics_plot_uncertainty_command(args: argparse.Namespace) -> int:
    try:
        plot_microkinetic_uncertainty_csv(args.uncertainty, args.out)
    except (OSError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    print(f"Wrote microkinetic uncertainty plot to {args.out}.")
    return 0


def _load_microkinetic_rate_parameters(conditions):
    if conditions.rate_parameters_path is not None:
        return load_rate_parameter_set(conditions.rate_parameters_path)
    return rate_parameter_set_from_mapping(conditions.rate_parameters)


def _load_microkinetic_parameter_distributions(conditions):
    if conditions.parameter_distributions_path is not None:
        return load_parameter_distributions(conditions.parameter_distributions_path)
    return parameter_distributions_from_mapping(conditions.parameter_distributions)


def _load_microkinetic_state_csv(path: Path) -> dict[str, float]:
    with Path(path).open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    if not rows:
        raise ValueError(f"{path}: state CSV is empty")
    if {"species", "coverage"}.issubset(rows[0]):
        state = {}
        for row in rows:
            species_id = row.get("species", "").strip()
            if not species_id:
                raise ValueError(f"{path}: state row is missing species")
            state[species_id] = float(row["coverage"])
        return state
    if len(rows) != 1:
        raise ValueError(
            f"{path}: trajectory-style state CSV must contain exactly one row"
        )
    return {
        key: float(value)
        for key, value in rows[0].items()
        if key != "time" and value not in (None, "")
    }


def _result_for_species(
    results: list[CalculationResult], species_name: str
) -> CalculationResult:
    matches = [result for result in results if result.species_name == species_name]
    if not matches:
        raise ValueError(f"no result found for species {species_name!r}")
    if len(matches) > 1:
        raise ValueError(
            f"multiple results found for species {species_name!r}; provide a "
            "deduplicated result collection"
        )
    return matches[0]


def _run_project_command(args: argparse.Namespace) -> int:
    try:
        manifest = load_project_manifest(args.manifest)
        species_list = load_species_registry(manifest.species_path)
        print(f"Loaded project {manifest.name!r} from {manifest.path}.")
        print(f"Validated {len(species_list)} species in {manifest.species_path}.")
        if not manifest.steps:
            print("No project steps configured.")
            return 0

        reaction_rows: list[ReactionEnergyRow] = []
        calculation_failed = False
        for step in manifest.steps:
            print(f"STEP {step}")
            if step == "render_gaussian":
                _run_project_render_gaussian(manifest, species_list)
            elif step == "parse_gaussian":
                _run_project_parse_gaussian(manifest)
            elif step == "run_pyscf":
                calculation_failed = (
                    _run_project_pyscf(manifest, species_list) or calculation_failed
                )
            elif step == "quality_checks":
                _run_project_quality_checks(manifest)
            elif step == "reaction_table":
                reaction_rows = _run_project_reaction_table(manifest, species_list)
            elif step == "report":
                _run_project_report(manifest, species_list, reaction_rows)
            else:
                raise ValueError(f"unsupported project step {step!r}")
    except (OSError, ValueError, MissingOptionalDependencyError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    return 1 if calculation_failed else 0


def _triage_command(args: argparse.Namespace) -> int:
    try:
        results = load_result_collection(args.results)
        write_failed_jobs_report(args.out, results)
    except (OSError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    classified = classify_triage_results(results)
    print("category\tcount")
    for category, rows in classified.items():
        print(f"{category}\t{len(rows)}")
    print(f"Wrote failed-job triage report to {args.out}.")
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


def _read_structure_file(path: Path) -> list[AtomisticStructure]:
    structure_path = Path(path)
    if _is_xyz_path(structure_path):
        return [
            AtomisticStructure.from_molecule_geometry(frame)
            for frame in read_xyz_frames(structure_path)
        ]

    ase_io = _load_ase_io()
    frames = ase_io.read(str(structure_path), index=":")
    if not isinstance(frames, list):
        frames = [frames]
    return [from_ase_atoms(frame) for frame in frames]


def _structure_with_cli_cell(
    structure: AtomisticStructure,
    cell_lengths: list[float] | None,
    *,
    periodic: bool,
) -> AtomisticStructure:
    cell = structure.cell
    if cell_lengths is not None:
        a, b, c = cell_lengths
        if a <= 0 or b <= 0 or c <= 0:
            raise ValueError("--cell lengths must be positive")
        cell = ((a, 0.0, 0.0), (0.0, b, 0.0), (0.0, 0.0, c))
    pbc = (True, True, True) if periodic else structure.pbc
    return AtomisticStructure(
        atoms=structure.atoms,
        cell=cell,
        pbc=pbc,
        fractional_coordinates=structure.fractional_coordinates,
        surface_normal=structure.surface_normal,
        fixed_atom_indices=structure.fixed_atom_indices,
        charge=structure.charge,
        multiplicity=structure.multiplicity,
        metadata=structure.metadata,
    )


def _load_qe_pseudo_map(path: Path) -> tuple[dict[str, str], dict[str, float]]:
    pseudo_path = Path(path)
    data = yaml.safe_load(pseudo_path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"{pseudo_path}: QE pseudo map must be a mapping")
    if data.get("schema_version") == 1:
        manifest = load_pseudopotential_manifest(pseudo_path)
        atomic_masses = data.get("atomic_masses", {})
        if not isinstance(atomic_masses, dict):
            raise ValueError(f"{pseudo_path}: atomic_masses must be a mapping")
        return (
            {
                element: record.filename
                for element, record in manifest.records.items()
            },
            dict(atomic_masses),
        )

    if "pseudopotentials" in data or "atomic_masses" in data:
        pseudopotentials = data.get("pseudopotentials", {})
        atomic_masses = data.get("atomic_masses", {})
        if not isinstance(pseudopotentials, dict):
            raise ValueError(f"{pseudo_path}: pseudopotentials must be a mapping")
        if not isinstance(atomic_masses, dict):
            raise ValueError(f"{pseudo_path}: atomic_masses must be a mapping")
        return dict(pseudopotentials), dict(atomic_masses)

    pseudopotentials: dict[str, str] = {}
    atomic_masses: dict[str, float] = {}
    for element, entry in data.items():
        if not isinstance(element, str):
            raise ValueError(f"{pseudo_path}: element keys must be strings")
        if not isinstance(entry, dict):
            raise ValueError(
                f"{pseudo_path}: element {element!r} must map to pseudo and mass"
            )
        if "pseudo" not in entry or "mass" not in entry:
            raise ValueError(
                f"{pseudo_path}: element {element!r} requires pseudo and mass"
            )
        pseudopotentials[element] = entry["pseudo"]
        atomic_masses[element] = entry["mass"]
    return pseudopotentials, atomic_masses


def _convert_structure_file(input_path: Path, output_path: Path) -> None:
    source = Path(input_path)
    target = Path(output_path)
    target.parent.mkdir(parents=True, exist_ok=True)

    if _is_xyz_path(source) and _is_xyz_path(target):
        write_xyz_frames(read_xyz_frames(source), target)
        return

    ase_io = _load_ase_io()
    frames = ase_io.read(str(source), index=":")
    if not isinstance(frames, list):
        frames = [frames]
    ase_io.write(str(target), frames if len(frames) != 1 else frames[0])


def _is_xyz_path(path: Path) -> bool:
    return Path(path).suffix.lower() == ".xyz"


def _load_ase_io():
    try:
        import ase.io
    except ImportError as exc:
        raise ASEUnavailableError(
            "ASE is required for this structure format; install the optional "
            "dependency with qchem-workbench[ase]."
        ) from exc
    return ase.io


def _formula_from_atoms(atoms) -> str:
    counts: dict[str, int] = {}
    for atom in atoms:
        counts[atom.symbol] = counts.get(atom.symbol, 0) + 1

    if "C" in counts:
        symbols = ["C"]
        if "H" in counts:
            symbols.append("H")
        symbols.extend(
            symbol for symbol in sorted(counts) if symbol not in {"C", "H"}
        )
    else:
        symbols = sorted(counts)

    return "".join(
        symbol if counts[symbol] == 1 else f"{symbol}{counts[symbol]}"
        for symbol in symbols
    )


def _run_project_render_gaussian(
    manifest: ProjectManifest, species_list: list[Species]
) -> None:
    out_dir = _required_manifest_path(
        manifest.inputs_dir, "project.inputs", "render_gaussian"
    )
    spec = _project_calculation_spec(manifest, "gaussian", "render_gaussian")
    generated = _render_gaussian_files(
        species_list=species_list,
        spec=spec,
        out_dir=out_dir,
        additional_keywords=manifest.calculation.route_keywords,
        force=False,
    )
    print(f"Rendered {len(generated)} Gaussian input file(s) into {out_dir}.")


def _run_project_parse_gaussian(manifest: ProjectManifest) -> None:
    outputs_dir = _required_manifest_path(
        manifest.outputs_dir, "project.outputs", "parse_gaussian"
    )
    results_path = _required_manifest_path(
        manifest.results_path, "project.results", "parse_gaussian"
    )
    paths = _gaussian_output_paths(outputs_dir)
    results = _parse_gaussian_outputs(paths)
    _write_parsed_result_collection(results_path, results, parser="gaussian")
    print(f"Parsed {len(results)} Gaussian output file(s) into {results_path}.")


def _run_project_pyscf(
    manifest: ProjectManifest, species_list: list[Species]
) -> bool:
    results_path = _required_manifest_path(
        manifest.results_path, "project.results", "run_pyscf"
    )
    spec = _project_calculation_spec(manifest, "pyscf", "run_pyscf")
    backend = PySCFBackend()
    results: list[CalculationResult] = []

    for species in species_list:
        try:
            result = backend.run(species, spec)
        except Exception as exc:
            if isinstance(exc, MissingOptionalDependencyError):
                raise
            result = _exception_result(species, spec, exc)
        results.append(result)

    _write_result_collection(results_path, spec, results)
    _print_result_summary(results)
    return not all(result.success for result in results)


def _run_project_quality_checks(manifest: ProjectManifest) -> None:
    results_path = _required_manifest_path(
        manifest.results_path, "project.results", "quality_checks"
    )
    results = load_result_collection(results_path)
    checks = _quality_checks_for_results(results, manifest.species_path)
    _print_quality_check_summary(checks)


def _run_project_reaction_table(
    manifest: ProjectManifest, species_list: list[Species]
) -> list[ReactionEnergyRow]:
    results_path = _required_manifest_path(
        manifest.results_path, "project.results", "reaction_table"
    )
    reaction_table_path = _required_manifest_path(
        manifest.reaction_table_path, "project.reaction_table", "reaction_table"
    )
    if manifest.reaction_quantity is None:
        raise ValueError(
            "reaction_table step requires project.reaction_quantity "
            "('electronic' or 'gibbs')"
        )
    if len(manifest.pathway_paths) != 1:
        raise ValueError(
            "reaction_table step requires exactly one project.pathways entry"
        )

    pathway = load_pathway(manifest.pathway_paths[0], species_registry=species_list)
    results = load_result_collection(results_path)
    rows = _reaction_energy_rows(pathway, results, manifest.reaction_quantity)
    _write_reaction_table_csv(reaction_table_path, rows)
    print(f"Wrote {len(rows)} reaction row(s) to {reaction_table_path}.")
    return rows


def _run_project_report(
    manifest: ProjectManifest,
    species_list: list[Species],
    reaction_rows: list[ReactionEnergyRow],
) -> None:
    results_path = _required_manifest_path(
        manifest.results_path, "project.results", "report"
    )
    report_path = _required_manifest_path(
        manifest.report_path, "project.reports", "report"
    )
    results = load_result_collection(results_path)
    checks = _quality_checks_for_results(results, manifest.species_path)
    write_markdown_report(
        report_path,
        results,
        species=species_list,
        quality_checks=checks,
        reaction_rows=reaction_rows,
    )
    print(f"Wrote Markdown report to {report_path}.")


def _project_calculation_spec(
    manifest: ProjectManifest, expected_backend: str, step: str
) -> CalculationSpec:
    spec = manifest.calculation.to_spec(
        default_backend=manifest.backend_mode or expected_backend
    )
    if spec.backend != expected_backend:
        raise ValueError(
            f"{step} step requires backend {expected_backend!r}; "
            f"manifest configured {spec.backend!r}"
        )
    return spec


def _required_manifest_path(path: Path | None, field: str, step: str) -> Path:
    if path is None:
        raise ValueError(f"{step} step requires {field}")
    return path


def _write_result_collection(
    path: Path, spec: CalculationSpec, results: list[CalculationResult]
) -> None:
    payload = {
        "schema_version": RESULT_COLLECTION_SCHEMA_VERSION,
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
    job_folders: bool = False,
    include_run_script: bool = False,
    scheduler: str | None = None,
) -> list[tuple[str, Path]]:
    if include_run_script and scheduler is None:
        scheduler = "shell"
    if include_run_script and not job_folders:
        raise ValueError("--include-run-script requires --job-folders")
    if scheduler is not None and not job_folders:
        raise ValueError("--scheduler requires --job-folders")

    output_dir = Path(out_dir)
    route = gaussian_route_from_spec(spec, additional_keywords=additional_keywords)
    include_script = scheduler is not None
    jobs = [
        _gaussian_job_paths(output_dir, species.name, job_folders, include_script)
        for species in species_list
    ]
    input_paths = [job["input_path"] for job in jobs]
    if len(set(input_paths)) != len(input_paths):
        raise ValueError("species names produce duplicate Gaussian input filenames")

    conflict_paths = [
        job[key]
        for job in jobs
        for key in ("input_path", "run_script_path")
        if job[key] is not None
    ]
    conflicts = [path for path in conflict_paths if path.exists()]
    if conflicts and not force:
        conflict_list = ", ".join(str(path) for path in conflicts)
        raise ValueError(f"refusing to overwrite existing file(s): {conflict_list}")

    output_dir.mkdir(parents=True, exist_ok=True)
    generated: list[tuple[str, Path]] = []
    for species, job in zip(species_list, jobs):
        path = job["input_path"]
        checkpoint = job["checkpoint"]
        content = render_gaussian_input(
            species,
            spec,
            GaussianInputOptions(
                checkpoint=checkpoint,
                route=route,
                title=f"{species.name} {spec.task} Gaussian input",
            ),
        )
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        if job["run_script_path"] is not None:
            job["run_script_path"].write_text(
                render_gaussian_scheduler_script(str(scheduler), path.name),
                encoding="utf-8",
            )
        generated.append((species.name, path))
    return generated


def _safe_filename(value: str) -> str:
    filename = re.sub(r"[^A-Za-z0-9._-]+", "_", value.strip()).strip("._")
    return filename or "species"


def _gaussian_job_paths(
    output_dir: Path,
    species_name: str,
    job_folders: bool,
    include_run_script: bool,
) -> dict[str, Path | str | None]:
    safe_name = _safe_filename(species_name)
    if job_folders:
        job_dir = output_dir / safe_name
        return {
            "input_path": job_dir / f"{safe_name}.gjf",
            "checkpoint": f"{safe_name}.chk",
            "run_script_path": job_dir / "run_gaussian.sh"
            if include_run_script
            else None,
        }
    return {
        "input_path": output_dir / f"{safe_name}.gjf",
        "checkpoint": None,
        "run_script_path": None,
    }


def _gaussian_run_script(input_filename: str) -> str:
    output_filename = f"{Path(input_filename).stem}.log"
    return (
        "#!/usr/bin/env bash\n"
        "set -euo pipefail\n"
        "\n"
        'GAUSSIAN_CMD="${GAUSSIAN_CMD:-g16}"\n'
        f'"$GAUSSIAN_CMD" < "{input_filename}" > "{output_filename}"\n'
    )


def _render_orca_files(
    species_list: list[Species],
    spec: CalculationSpec,
    out_dir: Path,
    force: bool,
    job_folders: bool = False,
    include_run_script: bool = False,
) -> list[tuple[str, Path]]:
    if include_run_script and not job_folders:
        raise ValueError("--include-run-script requires --job-folders")

    output_dir = Path(out_dir)
    jobs = [
        _orca_job_paths(output_dir, species.name, job_folders, include_run_script)
        for species in species_list
    ]
    input_paths = [job["input_path"] for job in jobs]
    if len(set(input_paths)) != len(input_paths):
        raise ValueError("species names produce duplicate ORCA input filenames")

    conflict_paths = [
        job[key]
        for job in jobs
        for key in ("input_path", "run_script_path")
        if job[key] is not None
    ]
    conflicts = [path for path in conflict_paths if path.exists()]
    if conflicts and not force:
        conflict_list = ", ".join(str(path) for path in conflicts)
        raise ValueError(f"refusing to overwrite existing file(s): {conflict_list}")

    output_dir.mkdir(parents=True, exist_ok=True)
    generated: list[tuple[str, Path]] = []
    for species, job in zip(species_list, jobs):
        path = job["input_path"]
        content = render_orca_input(
            species,
            spec,
            ORCAInputOptions(title=f"{species.name} {spec.task} ORCA input"),
        )
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        if job["run_script_path"] is not None:
            job["run_script_path"].write_text(
                _orca_run_script(path.name),
                encoding="utf-8",
            )
        generated.append((species.name, path))
    return generated


def _orca_job_paths(
    output_dir: Path,
    species_name: str,
    job_folders: bool,
    include_run_script: bool,
) -> dict[str, Path | None]:
    safe_name = _safe_filename(species_name)
    if job_folders:
        job_dir = output_dir / safe_name
        return {
            "input_path": job_dir / f"{safe_name}.inp",
            "run_script_path": job_dir / "run_orca.sh"
            if include_run_script
            else None,
        }
    return {
        "input_path": output_dir / f"{safe_name}.inp",
        "run_script_path": None,
    }


def _orca_run_script(input_filename: str) -> str:
    output_filename = f"{Path(input_filename).stem}.out"
    return (
        "#!/usr/bin/env bash\n"
        "set -euo pipefail\n"
        "\n"
        "# Template only; adapt ORCA_CMD for the local ORCA installation.\n"
        'ORCA_CMD="${ORCA_CMD:-orca}"\n'
        f'"$ORCA_CMD" "{input_filename}" > "{output_filename}"\n'
    )


def _gaussian_output_paths(path: Path) -> list[Path]:
    target = Path(path)
    if target.is_file():
        return [target] if target.suffix.lower() in {".log", ".out"} else []
    if not target.exists():
        raise FileNotFoundError(f"{target} does not exist")
    return sorted(
        file_path
        for file_path in target.rglob("*")
        if file_path.is_file() and file_path.suffix.lower() in {".log", ".out"}
    )


def _parse_gaussian_outputs(paths: list[Path]) -> list[CalculationResult]:
    results: list[CalculationResult] = []
    for path in paths:
        try:
            result = parse_gaussian_output(path)
        except Exception as exc:
            result = CalculationResult(
                species_name=path.stem,
                backend="gaussian",
                method=None,
                basis=None,
                task=None,
                success=False,
                warnings=[f"Parser raised exception: {exc}"],
                metadata={"exception_type": type(exc).__name__},
                source_path=path,
            )
        results.append(result)
    return results


def _orca_output_paths(path: Path) -> list[Path]:
    target = Path(path)
    if target.is_file():
        return [target] if target.suffix.lower() == ".out" else []
    if not target.exists():
        raise FileNotFoundError(f"{target} does not exist")
    return sorted(
        file_path
        for file_path in target.rglob("*")
        if file_path.is_file() and file_path.suffix.lower() == ".out"
    )


def _parse_orca_outputs(paths: list[Path]) -> list[CalculationResult]:
    results: list[CalculationResult] = []
    for path in paths:
        try:
            result = parse_orca_output(path)
        except Exception as exc:
            result = CalculationResult(
                species_name=path.stem,
                backend="orca",
                method=None,
                basis=None,
                task=None,
                success=False,
                warnings=[f"Parser raised exception: {exc}"],
                metadata={"exception_type": type(exc).__name__},
                source_path=path,
            )
        results.append(result)
    return results


def _qe_output_paths(path: Path) -> list[Path]:
    target = Path(path)
    qe_suffixes = {".out", ".pwout"}
    if target.is_file():
        return [target] if target.suffix.lower() in qe_suffixes else []
    if not target.exists():
        raise FileNotFoundError(f"{target} does not exist")
    return sorted(
        file_path
        for file_path in target.rglob("*")
        if file_path.is_file() and file_path.suffix.lower() in qe_suffixes
    )


def _parse_qe_outputs(paths: list[Path]) -> list[CalculationResult]:
    results: list[CalculationResult] = []
    for path in paths:
        try:
            result = parse_qe_output(path)
        except Exception as exc:
            result = CalculationResult(
                species_name=path.stem,
                backend="qe",
                method=None,
                basis=None,
                task=None,
                success=False,
                warnings=[f"Parser raised exception: {exc}"],
                metadata={"exception_type": type(exc).__name__},
                source_path=path,
            )
        results.append(result)
    return results


def _write_parsed_result_collection(
    path: Path, results: list[CalculationResult], parser: str
) -> None:
    payload = {
        "schema_version": RESULT_COLLECTION_SCHEMA_VERSION,
        "parser": parser,
        "results": [result.to_dict() for result in results],
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )


def _write_parsed_result_csv(path: Path, results: list[CalculationResult]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "source_path",
                "species_name",
                "success",
                "electronic_energy_hartree",
                "gibbs_free_energy_hartree",
                "negative_frequency_count",
                "most_negative_frequency_cm1",
                "warning_count",
            ],
        )
        writer.writeheader()
        for result in results:
            writer.writerow(
                {
                    "source_path": (
                        str(result.source_path) if result.source_path else ""
                    ),
                    "species_name": result.species_name,
                    "success": result.success,
                    "electronic_energy_hartree": result.electronic_energy_hartree,
                    "gibbs_free_energy_hartree": result.gibbs_free_energy_hartree,
                    "negative_frequency_count": result.metadata.get(
                        "negative_frequency_count"
                    ),
                    "most_negative_frequency_cm1": result.metadata.get(
                        "most_negative_frequency_cm1"
                    ),
                    "warning_count": len(result.warnings),
                }
            )


def _read_dict_csv(path: Path) -> tuple[list[dict[str, str]], tuple[str, ...]]:
    input_path = Path(path)
    with input_path.open(encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        if not reader.fieldnames:
            raise ValueError(f"{input_path}: CSV is missing headers")
        return list(reader), tuple(reader.fieldnames)


def _quality_checks_for_results(
    results: list[CalculationResult],
    species_path: Path | None,
) -> list[QualityCheck]:
    expected_multiplicities: dict[str, int] = {}
    checks: list[QualityCheck] = []
    if species_path is not None:
        species_list = load_species_registry(species_path)
        match_report = match_results_to_species(species_list, results)
        expected_multiplicities = {
            match.result.species_name: match.species.multiplicity
            for match in match_report.matches
        }
        checks.extend(_quality_checks_from_match_report(match_report))

    checks.extend(run_quality_checks(results, expected_multiplicities))
    return checks


def _quality_checks_from_match_report(match_report) -> list[QualityCheck]:
    checks: list[QualityCheck] = []
    for species_name in match_report.unmatched_species:
        checks.append(
            QualityCheck(
                code="unmatched_species",
                severity="warning",
                message=f"No result matched registry species {species_name!r}.",
                result_identifier=species_name,
            )
        )
    for result in match_report.unmatched_results:
        checks.append(
            QualityCheck(
                code="unmatched_result",
                severity="info",
                message=f"No registry species matched result {result.species_name!r}.",
                result_identifier=result.species_name,
            )
        )
    for ambiguous in match_report.ambiguous_matches:
        checks.append(
            QualityCheck(
                code="ambiguous_result_match",
                severity="warning",
                message=(
                    f"Registry species {ambiguous.species_name!r} matched multiple "
                    "results and needs human review."
                ),
                result_identifier=ambiguous.species_name,
            )
        )
    return checks


def _quality_check_payload(checks: list[QualityCheck]) -> dict[str, object]:
    return {
        "summary": _quality_check_counts(checks),
        "checks": [check.to_dict() for check in checks],
    }


def _quality_check_counts(checks: list[QualityCheck]) -> dict[str, int]:
    return {
        severity: sum(1 for check in checks if check.severity == severity)
        for severity in ("error", "warning", "info")
    }


def _print_quality_check_summary(checks: list[QualityCheck]) -> None:
    if not checks:
        print("No quality checks reported.")
        return

    for severity in ("error", "warning", "info"):
        severity_checks = [check for check in checks if check.severity == severity]
        if not severity_checks:
            continue
        print(f"{severity.upper()} ({len(severity_checks)})")
        for check in severity_checks:
            print(f"- {check.code}: {check.result_identifier}: {check.message}")


def _reaction_energy_rows(pathway, results, quantity: str) -> list[ReactionEnergyRow]:
    if quantity == "electronic":
        return reaction_electronic_energy_table(pathway, results)
    if quantity == "gibbs":
        return reaction_gibbs_free_energy_table(pathway, results)
    raise ValueError(f"unsupported reaction quantity {quantity!r}")


def _adsorption_energy_rows(
    workflow, results, quantity: str
) -> list[AdsorptionEnergyRow]:
    if quantity == "electronic":
        return adsorption_electronic_energy_table(workflow, results)
    if quantity == "gibbs":
        return adsorption_gibbs_free_energy_table(workflow, results)
    raise ValueError(f"unsupported adsorption quantity {quantity!r}")


def _write_reaction_table_csv(path: Path, rows: list[ReactionEnergyRow]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "reaction_id",
                "label",
                "quantity",
                "complete",
                "delta_hartree",
                "delta_ev",
                "delta_kj_mol",
                "missing_species",
                "notes",
            ],
        )
        writer.writeheader()
        for row in rows:
            writer.writerow(
                {
                    "reaction_id": row.reaction_id,
                    "label": row.label,
                    "quantity": row.quantity,
                    "complete": row.complete,
                    "delta_hartree": row.delta_hartree,
                    "delta_ev": row.delta_ev,
                    "delta_kj_mol": row.delta_kj_mol,
                    "missing_species": ";".join(row.missing_species),
                    "notes": row.notes,
                }
            )


def _write_adsorption_table_csv(path: Path, rows: list[AdsorptionEnergyRow]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "system_id",
                "quantity",
                "complete",
                "adsorption_energy_hartree",
                "adsorption_energy_ev",
                "adsorption_energy_kj_mol",
                "slab_result",
                "adsorbate_result",
                "combined_result",
                "missing",
                "warnings",
                "notes",
            ],
        )
        writer.writeheader()
        for row in rows:
            writer.writerow(
                {
                    "system_id": row.system_id,
                    "quantity": row.quantity,
                    "complete": row.complete,
                    "adsorption_energy_hartree": row.adsorption_hartree,
                    "adsorption_energy_ev": row.adsorption_ev,
                    "adsorption_energy_kj_mol": row.adsorption_kj_mol,
                    "slab_result": row.slab_result,
                    "adsorbate_result": row.adsorbate_result,
                    "combined_result": row.combined_result,
                    "missing": ";".join(row.missing),
                    "warnings": ";".join(row.warnings),
                    "notes": row.notes,
                }
            )


def _write_che_table_csv(path: Path, rows: list[CHEFreeEnergyRow]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "reaction_id",
                "label",
                "complete",
                "uncorrected_delta_g_hartree",
                "uncorrected_delta_g_ev",
                "correction_total_eV",
                "corrected_delta_g_ev",
                "corrected_delta_g_kj_mol",
                "correction_terms",
                "missing_species",
                "warnings",
                "notes",
            ],
        )
        writer.writeheader()
        for row in rows:
            writer.writerow(
                {
                    "reaction_id": row.reaction_id,
                    "label": row.label,
                    "complete": row.complete,
                    "uncorrected_delta_g_hartree": row.uncorrected_delta_g_hartree,
                    "uncorrected_delta_g_ev": row.uncorrected_delta_g_ev,
                    "correction_total_eV": row.correction_total_eV,
                    "corrected_delta_g_ev": row.corrected_delta_g_ev,
                    "corrected_delta_g_kj_mol": row.corrected_delta_g_kj_mol,
                    "correction_terms": _format_che_correction_terms(row),
                    "missing_species": ";".join(row.missing_species),
                    "warnings": ";".join(row.warnings),
                    "notes": row.notes,
                }
            )


def _write_convergence_table_csv(path: Path, rows: list[ConvergenceRow]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "variable_value",
                "complete",
                "energy_eV",
                "delta_from_previous_eV",
                "delta_from_previous_eV_per_atom",
                "within_tolerance",
                "n_atoms",
                "missing_reason",
            ],
        )
        writer.writeheader()
        for row in rows:
            writer.writerow(
                {
                    "variable_value": row.variable_value,
                    "complete": row.complete,
                    "energy_eV": row.energy_ev,
                    "delta_from_previous_eV": row.delta_from_previous_ev,
                    "delta_from_previous_eV_per_atom": (
                        row.delta_from_previous_ev_per_atom
                    ),
                    "within_tolerance": row.within_tolerance,
                    "n_atoms": row.n_atoms,
                    "missing_reason": row.missing_reason,
                }
            )


def _format_che_correction_terms(row: CHEFreeEnergyRow) -> str:
    return ";".join(
        (
            f"{term.label}={term.value_eV:.12g} eV"
            f" ({term.sign_convention}; source={term.source or 'N/A'}"
            f"; note={term.note or 'N/A'})"
        )
        for term in row.correction_terms
    )
