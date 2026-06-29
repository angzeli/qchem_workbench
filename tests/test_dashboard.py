from __future__ import annotations

import importlib.util

import pytest

from qchem_workbench.cli import main
from qchem_workbench.dashboard.app import (
    DashboardConfig,
    MissingStreamlitError,
    load_dashboard_config,
    render_dashboard,
)
from qchem_workbench.dashboard.data import load_dashboard_data
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
from qchem_workbench.core.result import CalculationResult
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
