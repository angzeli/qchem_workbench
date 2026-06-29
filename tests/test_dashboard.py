from __future__ import annotations

import importlib.util

import pytest

from qchem_workbench.cli import main
from qchem_workbench.active_learning.objectives import load_objective_spec
from qchem_workbench.active_learning.proposals import ProposedCandidate
from qchem_workbench.active_learning.state import load_campaign_state
from qchem_workbench.dashboard.app import (
    DashboardConfig,
    MissingStreamlitError,
    load_dashboard_config,
    render_dashboard,
)
from qchem_workbench.dashboard.active_learning import (
    active_learning_dataset_rows,
    active_learning_missing_descriptor_rows,
    active_learning_objective_rows,
    active_learning_proposal_rows,
    active_learning_quality_flag_rows,
    active_learning_ranking_rows,
    active_learning_state_rows,
    active_learning_transition_rows,
)
from qchem_workbench.dashboard.data import load_dashboard_data
from qchem_workbench.dashboard.data import DashboardData, DashboardSection
from qchem_workbench.dashboard.molecular import (
    molecular_property_rows,
    molecular_result_rows,
    table_rows_to_csv,
)
from qchem_workbench.dashboard.microkinetics import (
    final_coverage_rows,
    load_microkinetic_network_rows,
    microkinetic_output_sections,
    steady_state_warning_rows,
)
from qchem_workbench.dashboard.overview import (
    backend_method_basis_rows,
    missing_data_rows,
    overview_summary_rows,
)
from qchem_workbench.dashboard.quality import (
    failed_calculation_rows,
    quality_check_rows,
    quality_summary_rows,
)
from qchem_workbench.dashboard.structures import (
    dashboard_structure_rows,
    structure_summary_from_xyz,
    structure_summary_rows,
)
from qchem_workbench.dashboard.workflows import (
    adsorption_energy_rows,
    che_correction_display_rows,
    che_energy_rows,
    incomplete_analysis_rows,
    method_consistency_warnings,
    reaction_energy_rows,
)
from qchem_workbench.core.properties import (
    AtomicCharge,
    CalculationProperties,
    DipoleMoment,
    ExcitedState,
    MolecularOrbital,
    OrbitalTable,
    PopulationAnalysis,
    VibrationalMode,
)
from qchem_workbench.core.result import CalculationResult
from qchem_workbench.core.geometry import Atom
from qchem_workbench.core.structure import AtomisticStructure
from qchem_workbench.results.store import save_result_collection


def test_dashboard_config_loads_project_manifest(tmp_path):
    manifest_path = _write_project(tmp_path)

    config = load_dashboard_config(project=manifest_path)

    assert config.project_name == "dashboard demo"
    assert config.species_path == tmp_path / "species.yaml"
    assert config.results_paths == (tmp_path / "results" / "results.json",)
    assert manifest_path in config.loaded_file_paths


def test_dashboard_config_loads_result_files_without_project(tmp_path):
    result_path = tmp_path / "results.json"
    result_path.write_text('{"schema_version": 1, "results": []}\n', encoding="utf-8")

    config = load_dashboard_config(results=(result_path,))

    assert config.project_path is None
    assert config.results_paths == (result_path,)
    assert config.warnings == ()


def test_dashboard_config_warns_for_missing_result_file(tmp_path):
    missing = tmp_path / "missing.json"

    config = load_dashboard_config(results=(missing,))

    assert "does not exist" in config.warnings[0]


def test_dashboard_cli_reports_missing_streamlit(monkeypatch, tmp_path, capsys):
    manifest_path = _write_project(tmp_path)

    def _missing_dashboard(**_kwargs):
        raise MissingStreamlitError("install qchem-workbench[dashboard]")

    monkeypatch.setattr("qchem_workbench.cli.run_dashboard", _missing_dashboard)

    exit_code = main(["dashboard", "--project", str(manifest_path)])

    captured = capsys.readouterr()
    assert exit_code == 1
    assert "qchem-workbench[dashboard]" in captured.err


def test_dashboard_render_helper_with_fake_streamlit():
    fake = _FakeStreamlit()
    config = DashboardConfig(project_name="demo")

    render_dashboard(fake, config)

    assert fake.calls[0][0] == "set_page_config"
    assert ("title", "qchem-workbench dashboard") in fake.calls


@pytest.mark.skipif(
    importlib.util.find_spec("streamlit") is None,
    reason="Streamlit dashboard extra is not installed",
)
def test_dashboard_module_imports_when_streamlit_is_available():
    import qchem_workbench.dashboard.app as app

    assert app._import_streamlit() is not None


def test_dashboard_data_loads_minimal_project(tmp_path):
    manifest_path = _write_project(tmp_path)

    data = load_dashboard_data(project=manifest_path)

    assert data.project_name == "dashboard demo"
    assert data.section("species") is not None
    assert data.missing_sections == ("results[1]",)


def test_dashboard_data_loads_project_results(tmp_path):
    manifest_path = _write_project(tmp_path)
    result_path = tmp_path / "results" / "results.json"
    save_result_collection(
        result_path,
        [
            CalculationResult(
                species_name="water",
                backend="gaussian",
                method="B3LYP",
                basis="def2-SVP",
                task="single_point",
                success=True,
                electronic_energy_hartree=-76.0,
            )
        ],
    )

    data = load_dashboard_data(project=manifest_path)
    results = data.section("results[1]")

    assert results is not None
    assert results.metadata["count"] == 1
    assert results.rows[0]["species_name"] == "water"


def test_dashboard_data_missing_optional_file_is_not_fatal(tmp_path):
    missing = tmp_path / "missing_reaction_table.csv"

    data = load_dashboard_data(results=(), pathway_tables=(missing,))

    assert data.section("pathway_table[1]") is None
    assert data.missing_sections == ("pathway_table[1]",)
    assert data.file_provenance[0].status == "missing"


def test_dashboard_data_malformed_result_file_warns(tmp_path):
    malformed = tmp_path / "results.json"
    malformed.write_text("{not json", encoding="utf-8")

    data = load_dashboard_data(results=(malformed,))

    assert data.section("results[1]") is None
    assert data.warnings
    assert "result store could not be loaded" in data.warnings[0]


def test_dashboard_data_loads_active_learning_state(tmp_path):
    state_path = tmp_path / "campaign_state.json"
    state_path.write_text(
        '{"schema_version": 1, "candidates": {"cand_001": {"state": "pending"}}, "audit_log": []}\n',
        encoding="utf-8",
    )

    data = load_dashboard_data(results=(), active_learning_state=state_path)
    section = data.section("active_learning_state")

    assert section is not None
    assert {"state": "pending", "count": 1} in section.rows


def test_dashboard_overview_rows_include_counts(tmp_path):
    data = _dashboard_data_with_results(tmp_path)

    rows = overview_summary_rows(data)
    backend_rows = backend_method_basis_rows(data)

    assert {"item": "Result count", "value": 2} in rows
    assert backend_rows[0]["backend"] == "gaussian"
    assert backend_rows[0]["count"] == 2


def test_dashboard_missing_data_rows_include_warnings(tmp_path):
    malformed = tmp_path / "results.json"
    malformed.write_text("{not json", encoding="utf-8")
    data = load_dashboard_data(results=(malformed,))

    rows = missing_data_rows(data)

    assert rows
    assert "result store could not be loaded" in rows[0]["message"]


def test_dashboard_quality_grouping_and_filters(tmp_path):
    data = _dashboard_data_with_results(tmp_path)

    summary = quality_summary_rows(data)
    checks = quality_check_rows(data, backend="gaussian", code="unsuccessful_calculation")

    assert {"severity": "error", "count": 1} in summary
    assert len(checks) == 1
    assert checks[0]["species"] == "failed_species"


def test_dashboard_failed_calculation_rows(tmp_path):
    data = _dashboard_data_with_results(tmp_path)

    failed = failed_calculation_rows(data)

    assert len(failed) == 1
    assert failed[0]["species"] == "failed_species"


def test_dashboard_molecular_result_rows_filter_and_missing_values(tmp_path):
    data = _dashboard_data_with_results(tmp_path)

    rows = molecular_result_rows(data, species="water", backend="gaussian")

    assert len(rows) == 1
    assert rows[0]["electronic_energy_hartree"] == -76.0
    assert "gibbs_free_energy_hartree" in rows[0]["missing_values"]


def test_dashboard_molecular_property_rows(tmp_path):
    data = _dashboard_data_with_properties(tmp_path)

    assert molecular_property_rows(data, "dipoles")[0]["total_debye"] == 1.2
    assert molecular_property_rows(data, "charges")[0]["scheme"] == "Mulliken"
    assert molecular_property_rows(data, "orbitals")[0]["energy_ev"] == -8.0
    assert molecular_property_rows(data, "vibrations")[0]["frequency_cm1"] == 1600.0
    assert molecular_property_rows(data, "excitations")[0]["energy_ev"] == 3.1


def test_dashboard_molecular_table_csv_export(tmp_path):
    data = _dashboard_data_with_results(tmp_path)
    rows = molecular_result_rows(data)

    csv_text = table_rows_to_csv(rows)

    assert "electronic_energy_hartree" in csv_text
    assert "water" in csv_text


def test_dashboard_molecular_property_unknown_type_is_error(tmp_path):
    data = _dashboard_data_with_results(tmp_path)

    with pytest.raises(ValueError, match="unsupported molecular property"):
        molecular_property_rows(data, "redox_potentials")


def test_dashboard_reaction_table_helpers(tmp_path):
    reaction_path = tmp_path / "reaction_table.csv"
    _write_csv(
        reaction_path,
        ["reaction_id", "complete", "delta_ev", "backend", "method", "basis"],
        [
            {
                "reaction_id": "r1",
                "complete": "True",
                "delta_ev": "0.1",
                "backend": "gaussian",
                "method": "B3LYP",
                "basis": "def2-SVP",
            },
            {
                "reaction_id": "r2",
                "complete": "False",
                "delta_ev": "",
                "backend": "orca",
                "method": "PBE0",
                "basis": "def2-SVP",
            },
        ],
    )
    data = load_dashboard_data(pathway_tables=(reaction_path,))
    rows = reaction_energy_rows(data)

    assert len(rows) == 2
    assert incomplete_analysis_rows(rows)[0]["reaction_id"] == "r2"
    assert method_consistency_warnings(rows, label="reaction")


def test_dashboard_adsorption_table_helpers(tmp_path):
    adsorption_path = tmp_path / "adsorption_table.csv"
    _write_csv(
        adsorption_path,
        ["system_id", "quantity", "complete", "adsorption_energy_ev"],
        [
            {
                "system_id": "co_on_surface",
                "quantity": "adsorption_electronic_energy",
                "complete": "True",
                "adsorption_energy_ev": "-0.2",
            }
        ],
    )
    data = load_dashboard_data(adsorption_tables=(adsorption_path,))

    assert adsorption_energy_rows(data)[0]["system_id"] == "co_on_surface"


def test_dashboard_che_table_correction_display(tmp_path):
    che_path = tmp_path / "che_table.csv"
    _write_csv(
        che_path,
        ["reaction_id", "complete", "corrected_delta_g_ev", "correction_total_eV", "correction_terms"],
        [
            {
                "reaction_id": "step_1",
                "complete": "True",
                "corrected_delta_g_ev": "0.3",
                "correction_total_eV": "-0.1",
                "correction_terms": "CHE potential correction=-0.1 eV",
            }
        ],
    )
    data = load_dashboard_data(che_tables=(che_path,))

    assert che_energy_rows(data)[0]["reaction_id"] == "step_1"
    assert "CHE potential" in che_correction_display_rows(data)[0]["correction_terms"]


def test_dashboard_structure_summary_from_xyz(tmp_path):
    xyz_path = tmp_path / "hydrogen.xyz"
    xyz_path.write_text("2\nsynthetic hydrogen\nH 0 0 0\nH 0 0 0.7\n", encoding="utf-8")

    rows = structure_summary_from_xyz(xyz_path)

    assert rows[0]["atom_count"] == 2
    assert rows[0]["formula"] == "H2"
    assert rows[0]["periodic"] is False


def test_dashboard_periodic_structure_summary():
    structure = AtomisticStructure(
        atoms=(Atom("Cu", 0.0, 0.0, 0.0),),
        cell=((2.0, 0.0, 0.0), (0.0, 2.0, 0.0), (0.0, 0.0, 5.0)),
        pbc=(True, True, False),
        surface_normal=(0.0, 0.0, 1.0),
        fixed_atom_indices=(0,),
    )

    row = structure_summary_rows((structure,))[0]

    assert row["formula"] == "Cu"
    assert row["pbc"] == "True True False"
    assert row["cell_volume_angstrom3"] == pytest.approx(20.0)
    assert row["fixed_atom_indices"] == "0"


def test_dashboard_missing_structure_summary():
    data = DashboardData(
        loaded_sections=(
            DashboardSection(
                name="species",
                kind="registry",
                rows=({"name": "missing", "geometry_path": "/no/such/file.xyz"},),
            ),
        )
    )

    rows = dashboard_structure_rows(data)

    assert "could not load structure" in rows[0]["status"]


def test_dashboard_microkinetic_network_rows(tmp_path):
    model_path = _write_microkinetic_model(tmp_path)

    rows, warnings = load_microkinetic_network_rows(model_path)

    assert warnings == []
    assert rows is not None
    assert rows["site_types"][0]["id"] == "star"
    assert rows["steps"][0]["rate_constant_forward"] == "k_ads"


def test_dashboard_microkinetic_output_sections(tmp_path):
    simulation = tmp_path / "trajectory.csv"
    steady = tmp_path / "steady.csv"
    rates = tmp_path / "rates.csv"
    sensitivity = tmp_path / "sensitivity.csv"
    _write_csv(simulation, ["time", "CO_star", "star"], [{"time": "0", "CO_star": "0.1", "star": "0.9"}])
    _write_csv(
        steady,
        ["species", "coverage", "residual", "success", "max_abs_residual"],
        [{"species": "CO_star", "coverage": "0.5", "residual": "0.1", "success": "False", "max_abs_residual": "0.1"}],
    )
    _write_csv(rates, ["row_type", "id", "rate"], [{"row_type": "tof", "id": "CO_g", "rate": "1.0"}])
    _write_csv(
        sensitivity,
        ["parameter_id", "observable", "sensitivity"],
        [{"parameter_id": "k_ads", "observable": "product_rate:CO_g", "sensitivity": "0.2"}],
    )

    data = load_dashboard_data(
        microkinetic_outputs=(simulation, steady, rates, sensitivity),
    )
    sections = microkinetic_output_sections(data)

    assert final_coverage_rows(sections["simulation"])[0]["species"] == "CO_star"
    assert steady_state_warning_rows(sections["steady_state"])[0]["species"] == "CO_star"
    assert sections["rates"][0]["row_type"] == "tof"
    assert sections["sensitivity"][0]["parameter_id"] == "k_ads"


def test_dashboard_missing_microkinetic_output_is_not_fatal(tmp_path):
    missing = tmp_path / "missing_microkinetic.csv"

    data = load_dashboard_data(microkinetic_outputs=(missing,))

    assert data.missing_sections == ("microkinetic_output[1]",)


def test_dashboard_active_learning_state_and_dataset_rows(tmp_path):
    dataset_path = _write_active_learning_dataset(tmp_path)
    state_path = _write_active_learning_state(tmp_path)

    data = load_dashboard_data(
        active_learning_datasets=(dataset_path,),
        active_learning_state=state_path,
    )

    assert active_learning_state_rows(data)[0]["state"] == "completed"
    assert active_learning_dataset_rows(data)[0]["candidate_id"] == "cand_001"


def test_dashboard_active_learning_ranking_and_missing_rows(tmp_path):
    dataset_path = _write_active_learning_dataset(tmp_path)
    data = load_dashboard_data(active_learning_datasets=(dataset_path,))
    rows = active_learning_dataset_rows(data)

    ranking = active_learning_ranking_rows(rows)
    missing = active_learning_missing_descriptor_rows(rows)
    quality = active_learning_quality_flag_rows(rows)

    assert ranking[0]["candidate_id"] == "cand_001"
    assert "score_component_ads" in ranking[0]["score_components"]
    assert missing[0]["candidate_id"] == "cand_002"
    assert quality[0]["quality_flags"] == "missing_descriptor"


def test_dashboard_active_learning_objectives_and_proposals(tmp_path):
    objectives = load_objective_spec(_write_objectives(tmp_path))
    objective_rows = active_learning_objective_rows(objectives)
    missing_objectives = active_learning_objective_rows(None)
    proposals = active_learning_proposal_rows(
        (
            ProposedCandidate(candidate_id="cand_002", proposal_rank=2),
            ProposedCandidate(candidate_id="cand_001", proposal_rank=1),
        )
    )

    assert objective_rows["objectives"][0]["direction"] == "minimise"
    assert objective_rows["constraints"][0]["op"] == "equals"
    assert missing_objectives["warnings"]
    assert proposals[0]["candidate_id"] == "cand_001"


def test_dashboard_active_learning_transition_rows(tmp_path):
    state = load_campaign_state(_write_active_learning_state(tmp_path, with_audit=True))

    rows = active_learning_transition_rows(state)

    assert rows[0]["candidate_id"] == "cand_001"
    assert rows[0]["to_state"] == "completed"


def test_dashboard_render_helper_with_loaded_data(tmp_path):
    fake = _FakeStreamlit()
    config = DashboardConfig(project_name="demo")
    data = _dashboard_data_with_results(tmp_path)

    render_dashboard(fake, config, data=data)

    assert ("header", "Overview") in fake.calls
    assert ("header", "Quality") in fake.calls


class _FakeStreamlit:
    def __init__(self):
        self.calls = []

    def set_page_config(self, **kwargs):
        self.calls.append(("set_page_config", kwargs))

    def title(self, text):
        self.calls.append(("title", text))

    def caption(self, text):
        self.calls.append(("caption", text))

    def header(self, text):
        self.calls.append(("header", text))

    def subheader(self, text):
        self.calls.append(("subheader", text))

    def table(self, rows):
        self.calls.append(("table", rows))

    def download_button(self, label, data, file_name, mime):
        self.calls.append(("download_button", label, file_name, mime, data))


def _write_project(tmp_path):
    (tmp_path / "species.yaml").write_text("schema_version: 1\nspecies: []\n", encoding="utf-8")
    manifest_path = tmp_path / "qchem_project.yaml"
    manifest_path.write_text(
        "schema_version: 1\n"
        "project:\n"
        "  name: dashboard demo\n"
        "  species: species.yaml\n"
        "  results: results/results.json\n",
        encoding="utf-8",
    )
    return manifest_path


def _dashboard_data_with_results(tmp_path):
    result_path = tmp_path / "results.json"
    save_result_collection(
        result_path,
        [
            CalculationResult(
                species_name="water",
                backend="gaussian",
                method="B3LYP",
                basis="def2-SVP",
                task="single_point",
                success=True,
                electronic_energy_hartree=-76.0,
            ),
            CalculationResult(
                species_name="failed_species",
                backend="gaussian",
                method="B3LYP",
                basis="def2-SVP",
                task="single_point",
                success=False,
                warnings=["Synthetic failure fixture"],
            ),
        ],
    )
    return load_dashboard_data(results=(result_path,))


def _dashboard_data_with_properties(tmp_path):
    result_path = tmp_path / "property_results.json"
    save_result_collection(
        result_path,
        [
            CalculationResult(
                species_name="water",
                backend="gaussian",
                method="B3LYP",
                basis="def2-SVP",
                task="freq",
                success=True,
                electronic_energy_hartree=-76.0,
                properties=CalculationProperties(
                    dipole_moment=DipoleMoment(total_debye=1.2),
                    population_analyses=(
                        PopulationAnalysis(
                            scheme="Mulliken",
                            atomic_charges=(
                                AtomicCharge(
                                    atom_index=1,
                                    symbol="O",
                                    charge_e=-0.4,
                                    scheme="Mulliken",
                                ),
                            ),
                        ),
                    ),
                    orbital_table=OrbitalTable(
                        backend="gaussian",
                        orbitals=(
                            MolecularOrbital(index=1, energy_ev=-8.0, occupation=2.0),
                        ),
                        homo_index=1,
                    ),
                    vibrational_modes=(
                        VibrationalMode(
                            mode_index=1,
                            frequency_cm1=1600.0,
                            ir_intensity_km_mol=10.0,
                        ),
                    ),
                    excitations=(
                        ExcitedState(
                            state_index=1,
                            energy_ev=3.1,
                            wavelength_nm=400.0,
                        ),
                    ),
                ),
            )
        ],
    )
    return load_dashboard_data(results=(result_path,))


def _write_csv(path, headers, rows):
    import csv

    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=headers)
        writer.writeheader()
        writer.writerows(rows)


def _write_microkinetic_model(tmp_path):
    path = tmp_path / "model.yaml"
    path.write_text(
        "schema_version: 1\n"
        "microkinetic_model:\n"
        "  name: synthetic dashboard microkinetic fixture\n"
        "  site_types:\n"
        "    - id: star\n"
        "      total_sites: 1.0\n"
        "      unit: fraction\n"
        "  species:\n"
        "    gas:\n"
        "      CO_g:\n"
        "        phase: gas\n"
        "    surface:\n"
        "      CO_star:\n"
        "        phase: surface\n"
        "        site_type: star\n"
        "  steps:\n"
        "    - id: co_ads\n"
        "      reversible: false\n"
        "      reactants:\n"
        "        CO_g: 1\n"
        "        star: 1\n"
        "      products:\n"
        "        CO_star: 1\n"
        "      rate_constant_forward: k_ads\n",
        encoding="utf-8",
    )
    return path


def _write_active_learning_dataset(tmp_path):
    path = tmp_path / "al_dataset.csv"
    _write_csv(
        path,
        [
            "candidate_id",
            "al_rank",
            "al_score",
            "al_status",
            "al_reasons",
            "score_component_ads",
            "missing_ads_reason",
            "ads_quality_flags",
        ],
        [
            {
                "candidate_id": "cand_001",
                "al_rank": "1",
                "al_score": "0.4",
                "al_status": "ranked",
                "al_reasons": "",
                "score_component_ads": "0.4",
                "missing_ads_reason": "",
                "ads_quality_flags": "",
            },
            {
                "candidate_id": "cand_002",
                "al_rank": "",
                "al_score": "",
                "al_status": "excluded",
                "al_reasons": "missing_descriptor",
                "score_component_ads": "",
                "missing_ads_reason": "missing_result",
                "ads_quality_flags": "missing_descriptor",
            },
        ],
    )
    return path


def _write_active_learning_state(tmp_path, *, with_audit: bool = False):
    audit = (
        '"audit_log": ['
        '{"timestamp_utc": "2026-01-01T00:00:00+00:00", '
        '"candidate_id": "cand_001", "from_state": "pending", '
        '"to_state": "completed", "reason": "synthetic", "result": "results.json"}]'
        if with_audit
        else '"audit_log": []'
    )
    path = tmp_path / "campaign_state.json"
    path.write_text(
        '{"schema_version": 1, '
        '"candidates": {"cand_001": {"state": "completed"}}, '
        f"{audit}"
        "}\n",
        encoding="utf-8",
    )
    return path


def _write_objectives(tmp_path):
    path = tmp_path / "objectives.yaml"
    path.write_text(
        "schema_version: 1\n"
        "objectives:\n"
        "  - id: ads\n"
        "    source_column: ads_energy_eV\n"
        "    direction: minimise\n"
        "constraints:\n"
        "  - id: clean\n"
        "    source_column: quality_error_count\n"
        "    op: equals\n"
        "    value: 0\n",
        encoding="utf-8",
    )
    return path
