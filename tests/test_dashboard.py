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


class _FakeStreamlit:
    def __init__(self):
        self.calls = []

    def set_page_config(self, **kwargs):
        self.calls.append(("set_page_config", kwargs))

    def title(self, text):
        self.calls.append(("title", text))

    def caption(self, text):
        self.calls.append(("caption", text))

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
