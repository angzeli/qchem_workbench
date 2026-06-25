from __future__ import annotations

from qchem_workbench.cli import main
from qchem_workbench.core.registry import load_species_registry


def test_cli_help(capsys):
    try:
        main(["--help"])
    except SystemExit as exc:
        assert exc.code == 0

    captured = capsys.readouterr()
    assert "qchemwb" in captured.out


def test_cli_version(capsys):
    try:
        main(["--version"])
    except SystemExit as exc:
        assert exc.code == 0

    captured = capsys.readouterr()
    assert "qchemwb 0.1.0" in captured.out


def test_init_blank(tmp_path):
    project_path = tmp_path / "demo"

    exit_code = main(["init", str(project_path), "--template", "blank"])

    assert exit_code == 0
    assert (project_path / "species.yaml").exists()
    assert (project_path / "xyz").is_dir()
    assert (project_path / "outputs").is_dir()
    assert (project_path / "results").is_dir()
    assert (project_path / "reports").is_dir()
    assert load_species_registry(project_path / "species.yaml") == []


def test_init_basic(tmp_path):
    project_path = tmp_path / "demo"

    exit_code = main(["init", str(project_path), "--template", "basic"])

    species = load_species_registry(project_path / "species.yaml")
    assert exit_code == 0
    assert {item.name for item in species} == {
        "water",
        "carbon_dioxide",
        "carbon_monoxide",
    }


def test_init_co2rr_template_is_explicit_and_synthetic(tmp_path):
    project_path = tmp_path / "demo"

    exit_code = main(["init", str(project_path), "--template", "co2rr"])

    species = load_species_registry(project_path / "species.yaml")
    assert exit_code == 0
    assert {item.name for item in species} == {
        "co2rr_carbon_dioxide",
        "co2rr_carbon_monoxide",
        "co2rr_water",
    }
    assert all("synthetic" in item.tags for item in species)


def test_validate_success(tmp_path, capsys):
    project_path = tmp_path / "demo"
    assert main(["init", str(project_path), "--template", "basic"]) == 0

    exit_code = main(["validate", str(project_path / "species.yaml")])

    captured = capsys.readouterr()
    assert exit_code == 0
    assert "Validated 3 species" in captured.out


def test_validate_failure(tmp_path, capsys):
    registry_path = tmp_path / "species.yaml"
    registry_path.write_text("schema_version: 99\nspecies: []\n", encoding="utf-8")

    exit_code = main(["validate", str(registry_path)])

    captured = capsys.readouterr()
    assert exit_code == 1
    assert "unsupported schema_version" in captured.err


def test_init_refuses_to_overwrite_without_force(tmp_path):
    project_path = tmp_path / "demo"
    assert main(["init", str(project_path), "--template", "blank"]) == 0
    registry_path = project_path / "species.yaml"
    registry_path.write_text("sentinel\n", encoding="utf-8")

    exit_code = main(["init", str(project_path), "--template", "basic"])

    assert exit_code == 1
    assert registry_path.read_text(encoding="utf-8") == "sentinel\n"
