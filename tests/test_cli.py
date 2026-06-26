from __future__ import annotations

import csv
import importlib.util
import json

import pytest

from qchem_workbench.backends.gaussian_parser import parse_gaussian_output
from qchem_workbench.backends.orca_parser import parse_orca_output
from qchem_workbench.backends.pyscf_backend import MissingOptionalDependencyError
from qchem_workbench.backends.qe_parser import parse_qe_output
from qchem_workbench.cli import main
from qchem_workbench.core.properties import CalculationProperties, VibrationalMode
from qchem_workbench.core.result import CalculationResult
from qchem_workbench.core.registry import load_species_registry
from qchem_workbench.results.store import save_result_collection


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
    assert "qchemwb 1.0.0" in captured.out


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


def test_inspect_structure_xyz(tmp_path, capsys):
    xyz_path = tmp_path / "water.xyz"
    xyz_path.write_text(
        "3\n"
        "synthetic fixture water geometry\n"
        "O 0 0 0\n"
        "H 0 0 1\n"
        "H 0 1 0\n",
        encoding="utf-8",
    )

    exit_code = main(["inspect-structure", str(xyz_path)])

    captured = capsys.readouterr()
    assert exit_code == 0
    assert "atoms\t3" in captured.out
    assert "formula\tH2O" in captured.out
    assert "periodic\tFalse" in captured.out


def test_convert_structure_xyz_to_xyz(tmp_path):
    input_path = tmp_path / "input.xyz"
    output_path = tmp_path / "output.xyz"
    input_path.write_text(
        "1\nsynthetic fixture hydrogen geometry\nH 0 0 0\n",
        encoding="utf-8",
    )

    exit_code = main(["convert-structure", str(input_path), str(output_path)])

    assert exit_code == 0
    assert output_path.read_text(encoding="utf-8") == (
        "1\nsynthetic fixture hydrogen geometry\nH 0 0 0\n"
    )


def test_convert_structure_ase_format_reports_missing_ase(tmp_path, capsys):
    if importlib.util.find_spec("ase") is not None:
        pytest.skip("ASE is installed; missing-ASE error path is not applicable")
    input_path = tmp_path / "input.xyz"
    output_path = tmp_path / "output.traj"
    input_path.write_text(
        "1\nsynthetic fixture hydrogen geometry\nH 0 0 0\n",
        encoding="utf-8",
    )

    exit_code = main(["convert-structure", str(input_path), str(output_path)])

    captured = capsys.readouterr()
    assert exit_code == 1
    assert "ASE is required" in captured.err


def test_convert_structure_ase_only_format_when_available(tmp_path):
    pytest.importorskip("ase")
    input_path = tmp_path / "input.xyz"
    output_path = tmp_path / "output.traj"
    input_path.write_text(
        "1\nsynthetic fixture hydrogen geometry\nH 0 0 0\n",
        encoding="utf-8",
    )

    exit_code = main(["convert-structure", str(input_path), str(output_path)])

    assert exit_code == 0
    assert output_path.exists()


def test_build_slab_cli_when_ase_available(tmp_path, capsys):
    pytest.importorskip("ase")
    out_path = tmp_path / "slabs" / "cu111.xyz"

    exit_code = main(
        [
            "build-slab",
            "--element",
            "Cu",
            "--facet",
            "111",
            "--size",
            "2",
            "2",
            "4",
            "--vacuum",
            "15",
            "--out",
            str(out_path),
        ]
    )

    captured = capsys.readouterr()
    assert exit_code == 0
    assert out_path.exists()
    assert "atoms\t16" in captured.out
    assert "not relaxed" in captured.out


def test_place_adsorbate_cli_when_ase_available(tmp_path, capsys):
    pytest.importorskip("ase")
    (tmp_path / "slab.xyz").write_text(
        "1\nsynthetic fixture slab atom\nCu 0 0 0\n",
        encoding="utf-8",
    )
    (tmp_path / "co.xyz").write_text(
        "2\nsynthetic fixture adsorbate\nC 0 0 0\nO 0 0 1.1\n",
        encoding="utf-8",
    )
    placement_path = tmp_path / "placement.yaml"
    placement_path.write_text(
        "schema_version: 1\n"
        "placement:\n"
        "  slab_structure_path: slab.xyz\n"
        "  adsorbate_structure_path: co.xyz\n"
        "  anchor_atom: 0\n"
        "  target_position: [0.0, 0.0, 0.0]\n"
        "  height: 2.0\n",
        encoding="utf-8",
    )
    out_path = tmp_path / "structures" / "slab_co.xyz"

    exit_code = main(
        ["place-adsorbate", str(placement_path), "--out", str(out_path)]
    )

    captured = capsys.readouterr()
    assert exit_code == 0
    assert out_path.exists()
    assert "atoms\t3" in captured.out
    assert "not relaxed" in captured.out


def test_render_qe_from_fixture_structure(tmp_path, capsys):
    structure_path = tmp_path / "h2.xyz"
    structure_path.write_text(
        "2\n"
        "synthetic fixture hydrogen molecule in box\n"
        "H 0 0 0\n"
        "H 0 0 0.74\n",
        encoding="utf-8",
    )
    pseudo_map = tmp_path / "pseudos.yaml"
    pseudo_map.write_text(
        "pseudopotentials:\n"
        "  H: H.pbe.UPF\n"
        "atomic_masses:\n"
        "  H: 1.008\n",
        encoding="utf-8",
    )
    out_path = tmp_path / "qe_inputs" / "h2.in"

    exit_code = main(
        [
            "render-qe",
            str(structure_path),
            "--pseudo-map",
            str(pseudo_map),
            "--out",
            str(out_path),
            "--ecutwfc",
            "30",
            "--cell",
            "12",
            "12",
            "12",
            "--gamma-only",
        ]
    )

    rendered = out_path.read_text(encoding="utf-8")
    captured = capsys.readouterr()
    assert exit_code == 0
    assert "ATOMIC_SPECIES\nH 1.008 H.pbe.UPF\n" in rendered
    assert "CELL_PARAMETERS angstrom\n12 0 0\n0 12 0\n0 0 12\n" in rendered
    assert rendered.endswith("K_POINTS gamma\n")
    assert "Inspect pseudopotentials" in captured.out


def test_render_qe_missing_pseudo_map(tmp_path, capsys):
    structure_path = tmp_path / "h.xyz"
    structure_path.write_text(
        "1\nsynthetic fixture hydrogen atom\nH 0 0 0\n",
        encoding="utf-8",
    )

    exit_code = main(
        [
            "render-qe",
            str(structure_path),
            "--pseudo-map",
            str(tmp_path / "missing.yaml"),
            "--out",
            str(tmp_path / "h.in"),
            "--ecutwfc",
            "30",
            "--cell",
            "10",
            "10",
            "10",
        ]
    )

    captured = capsys.readouterr()
    assert exit_code == 1
    assert "missing.yaml" in captured.err


def test_render_qe_options_appear_in_output(tmp_path):
    structure_path = tmp_path / "cu.xyz"
    structure_path.write_text(
        "1\nsynthetic fixture copper cell\nCu 0 0 0\n",
        encoding="utf-8",
    )
    pseudo_map = tmp_path / "pseudos.yaml"
    pseudo_map.write_text(
        "Cu:\n"
        "  pseudo: Cu.pbe.UPF\n"
        "  mass: 63.546\n",
        encoding="utf-8",
    )
    out_path = tmp_path / "cu.in"

    exit_code = main(
        [
            "render-qe",
            str(structure_path),
            "--pseudo-map",
            str(pseudo_map),
            "--out",
            str(out_path),
            "--calculation",
            "relax",
            "--prefix",
            "cu-demo",
            "--pseudo-dir",
            "/pseudos",
            "--outdir",
            "/scratch/qe",
            "--ecutwfc",
            "40",
            "--ecutrho",
            "320",
            "--occupations",
            "smearing",
            "--smearing",
            "mp",
            "--degauss",
            "0.02",
            "--k-points",
            "2",
            "2",
            "1",
            "--cell",
            "3.6",
            "3.6",
            "10",
            "--periodic",
        ]
    )

    rendered = out_path.read_text(encoding="utf-8")
    assert exit_code == 0
    assert "  calculation = 'relax'," in rendered
    assert "  prefix = 'cu-demo'," in rendered
    assert "  pseudo_dir = '/pseudos'," in rendered
    assert "  outdir = '/scratch/qe'," in rendered
    assert "  ecutrho = 320," in rendered
    assert "  occupations = 'smearing'," in rendered
    assert "  smearing = 'mp'," in rendered
    assert "  degauss = 0.02," in rendered
    assert "&IONS\n/\n" in rendered
    assert "K_POINTS automatic\n2 2 1 0 0 0\n" in rendered


def test_init_refuses_to_overwrite_without_force(tmp_path):
    project_path = tmp_path / "demo"
    assert main(["init", str(project_path), "--template", "blank"]) == 0
    registry_path = project_path / "species.yaml"
    registry_path.write_text("sentinel\n", encoding="utf-8")

    exit_code = main(["init", str(project_path), "--template", "basic"])

    assert exit_code == 1
    assert registry_path.read_text(encoding="utf-8") == "sentinel\n"


def test_run_pyscf_writes_json_with_mocked_backend(tmp_path, monkeypatch, capsys):
    project_path = tmp_path / "demo"
    assert main(["init", str(project_path), "--template", "basic"]) == 0
    out_path = project_path / "results" / "pyscf_results.json"

    class FakeBackend:
        def run(self, species, spec):
            return CalculationResult(
                species_name=species.name,
                backend="pyscf",
                method=spec.method,
                basis=spec.basis,
                task=spec.task,
                success=True,
                electronic_energy_hartree=-1.0,
            )

    monkeypatch.setattr("qchem_workbench.cli.PySCFBackend", FakeBackend)

    exit_code = main(
        [
            "run-pyscf",
            str(project_path / "species.yaml"),
            "--method",
            "b3lyp",
            "--basis",
            "sto-3g",
            "--out",
            str(out_path),
        ]
    )

    payload = json.loads(out_path.read_text(encoding="utf-8"))
    captured = capsys.readouterr()
    assert exit_code == 0
    assert payload["calculation"]["method"] == "b3lyp"
    assert payload["calculation"]["basis"] == "sto-3g"
    assert len(payload["results"]) == 3
    assert all(result["success"] for result in payload["results"])
    assert "species\tsuccess" in captured.out


def test_run_pyscf_continues_after_species_failure(tmp_path, monkeypatch):
    project_path = tmp_path / "demo"
    assert main(["init", str(project_path), "--template", "basic"]) == 0
    out_path = project_path / "results" / "pyscf_results.json"

    class FakeBackend:
        def run(self, species, spec):
            if species.name == "carbon_dioxide":
                raise RuntimeError("synthetic backend failure")
            return CalculationResult(
                species_name=species.name,
                backend="pyscf",
                method=spec.method,
                basis=spec.basis,
                task=spec.task,
                success=True,
            )

    monkeypatch.setattr("qchem_workbench.cli.PySCFBackend", FakeBackend)

    exit_code = main(
        [
            "run-pyscf",
            str(project_path / "species.yaml"),
            "--method",
            "b3lyp",
            "--basis",
            "sto-3g",
            "--out",
            str(out_path),
        ]
    )

    payload = json.loads(out_path.read_text(encoding="utf-8"))
    failed = [result for result in payload["results"] if not result["success"]]
    assert exit_code == 1
    assert len(payload["results"]) == 3
    assert failed[0]["species_name"] == "carbon_dioxide"
    assert "synthetic backend failure" in failed[0]["warnings"][0]


def test_run_pyscf_reports_missing_optional_dependency(
    tmp_path, monkeypatch, capsys
):
    project_path = tmp_path / "demo"
    assert main(["init", str(project_path), "--template", "basic"]) == 0
    out_path = project_path / "results" / "pyscf_results.json"

    class MissingBackend:
        def run(self, species, spec):
            raise MissingOptionalDependencyError("install optional PySCF dependency")

    monkeypatch.setattr("qchem_workbench.cli.PySCFBackend", MissingBackend)

    exit_code = main(
        [
            "run-pyscf",
            str(project_path / "species.yaml"),
            "--method",
            "b3lyp",
            "--basis",
            "sto-3g",
            "--out",
            str(out_path),
        ]
    )

    captured = capsys.readouterr()
    assert exit_code == 1
    assert "install optional PySCF dependency" in captured.err
    assert not out_path.exists()


def test_render_gaussian_generates_files(tmp_path, capsys):
    project_path = tmp_path / "demo"
    assert main(["init", str(project_path), "--template", "basic"]) == 0
    out_dir = project_path / "gaussian_inputs"

    exit_code = main(
        [
            "render-gaussian",
            str(project_path / "species.yaml"),
            "--method",
            "wb97xd",
            "--basis",
            "6-31+G(d,p)",
            "--task",
            "single_point",
            "--out",
            str(out_dir),
        ]
    )

    captured = capsys.readouterr()
    water_input = (out_dir / "water.gjf").read_text(encoding="utf-8")
    assert exit_code == 0
    assert (out_dir / "carbon_dioxide.gjf").exists()
    assert "# wb97xd/6-31+G(d,p)" in water_input
    assert "\n0 1\n" in water_input
    assert "water\t" in captured.out


def test_render_gaussian_refuses_to_overwrite_without_force(tmp_path):
    project_path = tmp_path / "demo"
    assert main(["init", str(project_path), "--template", "basic"]) == 0
    out_dir = project_path / "gaussian_inputs"
    out_dir.mkdir()
    water_path = out_dir / "water.gjf"
    water_path.write_text("sentinel\n", encoding="utf-8")

    exit_code = main(
        [
            "render-gaussian",
            str(project_path / "species.yaml"),
            "--method",
            "wb97xd",
            "--basis",
            "6-31+G(d,p)",
            "--task",
            "single_point",
            "--out",
            str(out_dir),
        ]
    )

    assert exit_code == 1
    assert water_path.read_text(encoding="utf-8") == "sentinel\n"


def test_render_gaussian_uses_task_solvent_and_extra_keywords(tmp_path):
    project_path = tmp_path / "demo"
    assert main(["init", str(project_path), "--template", "basic"]) == 0
    out_dir = project_path / "gaussian_inputs"

    exit_code = main(
        [
            "render-gaussian",
            str(project_path / "species.yaml"),
            "--method",
            "wb97xd",
            "--basis",
            "6-31+G(d,p)",
            "--task",
            "opt_freq",
            "--solvent",
            "smd,solvent=water",
            "--route-keyword",
            "scf=tight",
            "--out",
            str(out_dir),
        ]
    )

    water_input = (out_dir / "water.gjf").read_text(encoding="utf-8")
    assert exit_code == 0
    assert (
        "# wb97xd/6-31+G(d,p) opt freq scrf=(smd,solvent=water) scf=tight"
        in water_input
    )


def test_render_gaussian_flat_layout_remains_default(tmp_path):
    project_path = tmp_path / "demo"
    assert main(["init", str(project_path), "--template", "basic"]) == 0
    out_dir = project_path / "gaussian_inputs"

    exit_code = main(
        [
            "render-gaussian",
            str(project_path / "species.yaml"),
            "--method",
            "wb97xd",
            "--basis",
            "6-31+G(d,p)",
            "--task",
            "single_point",
            "--out",
            str(out_dir),
        ]
    )

    assert exit_code == 0
    assert (out_dir / "water.gjf").exists()
    assert not (out_dir / "water" / "water.gjf").exists()


def test_render_gaussian_job_folder_layout(tmp_path):
    project_path = tmp_path / "demo"
    assert main(["init", str(project_path), "--template", "basic"]) == 0
    out_dir = project_path / "gaussian_inputs"

    exit_code = main(
        [
            "render-gaussian",
            str(project_path / "species.yaml"),
            "--method",
            "wb97xd",
            "--basis",
            "6-31+G(d,p)",
            "--task",
            "single_point",
            "--out",
            str(out_dir),
            "--job-folders",
        ]
    )

    water_input = (out_dir / "water" / "water.gjf").read_text(encoding="utf-8")
    assert exit_code == 0
    assert "%chk=water.chk\n" in water_input
    assert (out_dir / "carbon_dioxide" / "carbon_dioxide.gjf").exists()


def test_render_gaussian_run_script_generation(tmp_path):
    project_path = tmp_path / "demo"
    assert main(["init", str(project_path), "--template", "basic"]) == 0
    out_dir = project_path / "gaussian_inputs"

    exit_code = main(
        [
            "render-gaussian",
            str(project_path / "species.yaml"),
            "--method",
            "wb97xd",
            "--basis",
            "6-31+G(d,p)",
            "--task",
            "single_point",
            "--out",
            str(out_dir),
            "--job-folders",
            "--include-run-script",
        ]
    )

    script = (out_dir / "water" / "run_gaussian.sh").read_text(encoding="utf-8")
    assert exit_code == 0
    assert 'GAUSSIAN_CMD="${GAUSSIAN_CMD:-g16}"' in script
    assert '"$GAUSSIAN_CMD" < "water.gjf" > "water.log"' in script


def test_render_gaussian_run_script_requires_job_folders(tmp_path):
    project_path = tmp_path / "demo"
    assert main(["init", str(project_path), "--template", "basic"]) == 0

    exit_code = main(
        [
            "render-gaussian",
            str(project_path / "species.yaml"),
            "--method",
            "wb97xd",
            "--basis",
            "6-31+G(d,p)",
            "--task",
            "single_point",
            "--out",
            str(project_path / "gaussian_inputs"),
            "--include-run-script",
        ]
    )

    assert exit_code == 1


def test_render_gaussian_slurm_scheduler_template(tmp_path):
    project_path = tmp_path / "demo"
    assert main(["init", str(project_path), "--template", "basic"]) == 0
    out_dir = project_path / "gaussian_inputs"

    exit_code = main(
        [
            "render-gaussian",
            str(project_path / "species.yaml"),
            "--method",
            "wb97xd",
            "--basis",
            "6-31+G(d,p)",
            "--task",
            "single_point",
            "--out",
            str(out_dir),
            "--job-folders",
            "--scheduler",
            "slurm",
        ]
    )

    script = (out_dir / "water" / "run_gaussian.sh").read_text(encoding="utf-8")
    assert exit_code == 0
    assert "#SBATCH --job-name=water" in script
    assert "Template only" in script
    assert not (out_dir / "water" / "water.log").exists()


def test_render_gaussian_scheduler_requires_job_folders(tmp_path):
    project_path = tmp_path / "demo"
    assert main(["init", str(project_path), "--template", "basic"]) == 0

    exit_code = main(
        [
            "render-gaussian",
            str(project_path / "species.yaml"),
            "--method",
            "wb97xd",
            "--basis",
            "6-31+G(d,p)",
            "--task",
            "single_point",
            "--out",
            str(project_path / "gaussian_inputs"),
            "--scheduler",
            "slurm",
        ]
    )

    assert exit_code == 1


def test_render_orca_generates_files(tmp_path, capsys):
    project_path = tmp_path / "demo"
    assert main(["init", str(project_path), "--template", "basic"]) == 0
    out_dir = project_path / "orca_inputs"

    exit_code = main(
        [
            "render-orca",
            str(project_path / "species.yaml"),
            "--method",
            "b3lyp",
            "--basis",
            "def2-svp",
            "--task",
            "single_point",
            "--out",
            str(out_dir),
        ]
    )

    captured = capsys.readouterr()
    water_input = (out_dir / "water.inp").read_text(encoding="utf-8")
    assert exit_code == 0
    assert (out_dir / "carbon_dioxide.inp").exists()
    assert "! b3lyp def2-svp SP" in water_input
    assert "\n* xyz 0 1\n" in water_input
    assert "water\t" in captured.out


def test_render_orca_job_folder_layout(tmp_path):
    project_path = tmp_path / "demo"
    assert main(["init", str(project_path), "--template", "basic"]) == 0
    out_dir = project_path / "orca_inputs"

    exit_code = main(
        [
            "render-orca",
            str(project_path / "species.yaml"),
            "--method",
            "b3lyp",
            "--basis",
            "def2-svp",
            "--task",
            "opt_freq",
            "--out",
            str(out_dir),
            "--job-folders",
        ]
    )

    water_input = (out_dir / "water" / "water.inp").read_text(encoding="utf-8")
    assert exit_code == 0
    assert "! b3lyp def2-svp Opt Freq" in water_input
    assert (out_dir / "carbon_dioxide" / "carbon_dioxide.inp").exists()


def test_render_orca_refuses_to_overwrite_without_force(tmp_path):
    project_path = tmp_path / "demo"
    assert main(["init", str(project_path), "--template", "basic"]) == 0
    out_dir = project_path / "orca_inputs"
    out_dir.mkdir()
    water_path = out_dir / "water.inp"
    water_path.write_text("sentinel\n", encoding="utf-8")

    exit_code = main(
        [
            "render-orca",
            str(project_path / "species.yaml"),
            "--method",
            "b3lyp",
            "--basis",
            "def2-svp",
            "--task",
            "single_point",
            "--out",
            str(out_dir),
        ]
    )

    assert exit_code == 1
    assert water_path.read_text(encoding="utf-8") == "sentinel\n"


def test_render_orca_run_script_generation(tmp_path):
    project_path = tmp_path / "demo"
    assert main(["init", str(project_path), "--template", "basic"]) == 0
    out_dir = project_path / "orca_inputs"

    exit_code = main(
        [
            "render-orca",
            str(project_path / "species.yaml"),
            "--method",
            "b3lyp",
            "--basis",
            "def2-svp",
            "--task",
            "single_point",
            "--out",
            str(out_dir),
            "--job-folders",
            "--include-run-script",
        ]
    )

    script = (out_dir / "water" / "run_orca.sh").read_text(encoding="utf-8")
    assert exit_code == 0
    assert "Template only" in script
    assert 'ORCA_CMD="${ORCA_CMD:-orca}"' in script
    assert '"$ORCA_CMD" "water.inp" > "water.out"' in script


def test_render_orca_run_script_requires_job_folders(tmp_path):
    project_path = tmp_path / "demo"
    assert main(["init", str(project_path), "--template", "basic"]) == 0

    exit_code = main(
        [
            "render-orca",
            str(project_path / "species.yaml"),
            "--method",
            "b3lyp",
            "--basis",
            "def2-svp",
            "--task",
            "single_point",
            "--out",
            str(project_path / "orca_inputs"),
            "--include-run-script",
        ]
    )

    assert exit_code == 1


def test_parse_gaussian_scans_recursively_and_writes_json(tmp_path):
    outputs = tmp_path / "outputs"
    nested = outputs / "nested"
    nested.mkdir(parents=True)
    (outputs / "water.log").write_text(
        " # wb97xd/6-31g\n"
        " SCF Done:  E(RB3LYP) =  -76.1000000000     A.U. after 10 cycles\n"
        " Normal termination of Gaussian 16\n",
        encoding="utf-8",
    )
    (nested / "co2.out").write_text(
        " # wb97xd/6-31g\n"
        " SCF Done:  E(RB3LYP) =  -188.2000000000     A.U. after 10 cycles\n"
        " Normal termination of Gaussian 16\n",
        encoding="utf-8",
    )
    (outputs / "ignore.txt").write_text("not a Gaussian output\n", encoding="utf-8")
    out_path = tmp_path / "results" / "gaussian_results.json"

    exit_code = main(["parse-gaussian", str(outputs), "--out", str(out_path)])

    payload = json.loads(out_path.read_text(encoding="utf-8"))
    assert exit_code == 0
    assert payload["parser"] == "gaussian"
    assert [result["species_name"] for result in payload["results"]] == [
        "co2",
        "water",
    ]


def test_parse_gaussian_writes_csv(tmp_path):
    outputs = tmp_path / "outputs"
    outputs.mkdir()
    (outputs / "freq.log").write_text(
        " # wb97xd/6-31g freq\n"
        " Frequencies --   -10.0   250.0\n"
        " SCF Done:  E(RB3LYP) =  -1.0000000000     A.U. after 3 cycles\n"
        " Normal termination of Gaussian 16\n",
        encoding="utf-8",
    )
    out_path = tmp_path / "results" / "gaussian_results.json"
    csv_path = tmp_path / "results" / "gaussian_results.csv"

    exit_code = main(
        [
            "parse-gaussian",
            str(outputs),
            "--out",
            str(out_path),
            "--csv",
            str(csv_path),
        ]
    )

    with csv_path.open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    assert exit_code == 0
    assert rows[0]["species_name"] == "freq"
    assert rows[0]["negative_frequency_count"] == "1"
    assert rows[0]["most_negative_frequency_cm1"] == "-10.0"


def test_parse_gaussian_continues_on_parser_exception(tmp_path, monkeypatch):
    outputs = tmp_path / "outputs"
    outputs.mkdir()
    (outputs / "bad.log").write_text("synthetic malformed output\n", encoding="utf-8")
    (outputs / "good.log").write_text(
        " # hf/sto-3g\n Normal termination of Gaussian 16\n",
        encoding="utf-8",
    )
    out_path = tmp_path / "results" / "gaussian_results.json"

    def fake_parse(path):
        if path.name == "bad.log":
            raise ValueError("synthetic parser failure")
        return parse_gaussian_output(path)

    monkeypatch.setattr("qchem_workbench.cli.parse_gaussian_output", fake_parse)

    exit_code = main(["parse-gaussian", str(outputs), "--out", str(out_path)])

    payload = json.loads(out_path.read_text(encoding="utf-8"))
    failed = [result for result in payload["results"] if not result["success"]]
    assert exit_code == 0
    assert len(payload["results"]) == 2
    assert any(
        "synthetic parser failure" in result["warnings"][0] for result in failed
    )


def test_parse_orca_scans_recursively_and_writes_json(tmp_path):
    outputs = tmp_path / "outputs"
    nested = outputs / "nested"
    nested.mkdir(parents=True)
    (outputs / "water.out").write_text(
        "! B3LYP def2-SVP SP\n"
        "FINAL SINGLE POINT ENERGY     -76.1000000000\n"
        "****ORCA TERMINATED NORMALLY****\n",
        encoding="utf-8",
    )
    (nested / "co2.out").write_text(
        "! B3LYP def2-SVP SP\n"
        "FINAL SINGLE POINT ENERGY     -188.2000000000\n"
        "****ORCA TERMINATED NORMALLY****\n",
        encoding="utf-8",
    )
    (outputs / "ignore.log").write_text("not scanned by parse-orca\n", encoding="utf-8")
    out_path = tmp_path / "results" / "orca_results.json"

    exit_code = main(["parse-orca", str(outputs), "--out", str(out_path)])

    payload = json.loads(out_path.read_text(encoding="utf-8"))
    assert exit_code == 0
    assert payload["parser"] == "orca"
    assert [result["species_name"] for result in payload["results"]] == [
        "co2",
        "water",
    ]
    assert all(result["backend"] == "orca" for result in payload["results"])


def test_parse_orca_writes_csv(tmp_path):
    outputs = tmp_path / "outputs"
    outputs.mkdir()
    (outputs / "freq.out").write_text(
        "! B3LYP def2-SVP Freq\n"
        "Frequencies --   -10.0   250.0\n"
        "FINAL SINGLE POINT ENERGY     -1.0000000000\n"
        "****ORCA TERMINATED NORMALLY****\n",
        encoding="utf-8",
    )
    out_path = tmp_path / "results" / "orca_results.json"
    csv_path = tmp_path / "results" / "orca_results.csv"

    exit_code = main(
        [
            "parse-orca",
            str(outputs),
            "--out",
            str(out_path),
            "--csv",
            str(csv_path),
        ]
    )

    with csv_path.open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    assert exit_code == 0
    assert rows[0]["species_name"] == "freq"
    assert rows[0]["negative_frequency_count"] == "1"
    assert rows[0]["most_negative_frequency_cm1"] == "-10.0"


def test_parse_orca_continues_on_parser_exception(tmp_path, monkeypatch):
    outputs = tmp_path / "outputs"
    outputs.mkdir()
    (outputs / "bad.out").write_text("synthetic malformed output\n", encoding="utf-8")
    (outputs / "good.out").write_text(
        "! B3LYP def2-SVP SP\n****ORCA TERMINATED NORMALLY****\n",
        encoding="utf-8",
    )
    out_path = tmp_path / "results" / "orca_results.json"

    def fake_parse(path):
        if path.name == "bad.out":
            raise ValueError("synthetic ORCA parser failure")
        return parse_orca_output(path)

    monkeypatch.setattr("qchem_workbench.cli.parse_orca_output", fake_parse)

    exit_code = main(["parse-orca", str(outputs), "--out", str(out_path)])

    payload = json.loads(out_path.read_text(encoding="utf-8"))
    failed = [result for result in payload["results"] if not result["success"]]
    assert exit_code == 0
    assert len(payload["results"]) == 2
    assert any(
        "synthetic ORCA parser failure" in result["warnings"][0]
        for result in failed
    )


def test_parse_qe_scans_recursively_and_writes_json(tmp_path):
    outputs = tmp_path / "outputs"
    nested = outputs / "nested"
    nested.mkdir(parents=True)
    (outputs / "cu.out").write_text(
        "     convergence has been achieved in 6 iterations\n"
        "!    total energy              =     -114.000000 Ry\n"
        "JOB DONE.\n",
        encoding="utf-8",
    )
    (nested / "h2.pwout").write_text(
        "     convergence has been achieved in 4 iterations\n"
        "!    total energy              =     -2.000000 Ry\n"
        "JOB DONE.\n",
        encoding="utf-8",
    )
    (outputs / "ignore.log").write_text("not scanned by parse-qe\n", encoding="utf-8")
    out_path = tmp_path / "results" / "qe_results.json"

    exit_code = main(["parse-qe", str(outputs), "--out", str(out_path)])

    payload = json.loads(out_path.read_text(encoding="utf-8"))
    assert exit_code == 0
    assert payload["parser"] == "qe"
    assert [result["species_name"] for result in payload["results"]] == [
        "cu",
        "h2",
    ]
    assert all(result["backend"] == "qe" for result in payload["results"])


def test_parse_qe_writes_csv(tmp_path):
    outputs = tmp_path / "outputs"
    outputs.mkdir()
    (outputs / "cu.out").write_text(
        "     convergence has been achieved in 6 iterations\n"
        "!    total energy              =     -114.000000 Ry\n"
        "Maximum force = 0.001 Ry/bohr\n"
        "JOB DONE.\n",
        encoding="utf-8",
    )
    out_path = tmp_path / "results" / "qe_results.json"
    csv_path = tmp_path / "results" / "qe_results.csv"

    exit_code = main(
        [
            "parse-qe",
            str(outputs),
            "--out",
            str(out_path),
            "--csv",
            str(csv_path),
        ]
    )

    with csv_path.open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    assert exit_code == 0
    assert rows[0]["species_name"] == "cu"
    assert rows[0]["electronic_energy_hartree"] == "-57.0"


def test_parse_qe_continues_on_parser_exception(tmp_path, monkeypatch):
    outputs = tmp_path / "outputs"
    outputs.mkdir()
    (outputs / "bad.out").write_text("synthetic malformed output\n", encoding="utf-8")
    (outputs / "good.out").write_text(
        "     convergence has been achieved in 4 iterations\n"
        "!    total energy              =     -2.000000 Ry\n"
        "JOB DONE.\n",
        encoding="utf-8",
    )
    out_path = tmp_path / "results" / "qe_results.json"

    def fake_parse(path):
        if path.name == "bad.out":
            raise ValueError("synthetic QE parser failure")
        return parse_qe_output(path)

    monkeypatch.setattr("qchem_workbench.cli.parse_qe_output", fake_parse)

    exit_code = main(["parse-qe", str(outputs), "--out", str(out_path)])

    payload = json.loads(out_path.read_text(encoding="utf-8"))
    failed = [result for result in payload["results"] if not result["success"]]
    assert exit_code == 0
    assert len(payload["results"]) == 2
    assert any(
        "synthetic QE parser failure" in result["warnings"][0] for result in failed
    )


def test_check_results_clean_result_set(tmp_path, capsys):
    results_path = tmp_path / "results.json"
    save_result_collection(
        results_path,
        [
            CalculationResult(
                species_name="water",
                backend="gaussian",
                method="wb97xd",
                basis="6-31g",
                task="single_point",
                success=True,
                electronic_energy_hartree=-76.0,
            )
        ],
    )

    exit_code = main(["check-results", str(results_path)])

    captured = capsys.readouterr()
    assert exit_code == 0
    assert "No quality checks reported." in captured.out


def test_check_results_reports_warnings(tmp_path, capsys):
    results_path = tmp_path / "results.json"
    save_result_collection(
        results_path,
        [
            CalculationResult(
                species_name="water",
                backend="gaussian",
                method="wb97xd",
                basis="6-31g",
                task="single_point",
                success=True,
                electronic_energy_hartree=None,
            )
        ],
    )

    exit_code = main(["check-results", str(results_path)])

    captured = capsys.readouterr()
    assert exit_code == 0
    assert "WARNING" in captured.out
    assert "missing_electronic_energy" in captured.out


def test_check_results_errors_exit_nonzero(tmp_path, capsys):
    results_path = tmp_path / "results.json"
    save_result_collection(
        results_path,
        [
            CalculationResult(
                species_name="water",
                backend="gaussian",
                method="wb97xd",
                basis="6-31g",
                task="single_point",
                success=False,
                electronic_energy_hartree=-76.0,
            )
        ],
    )

    exit_code = main(["check-results", str(results_path)])

    captured = capsys.readouterr()
    assert exit_code == 1
    assert "ERROR" in captured.out
    assert "unsuccessful_calculation" in captured.out


def test_check_results_json_output(tmp_path, capsys):
    results_path = tmp_path / "results.json"
    save_result_collection(
        results_path,
        [
            CalculationResult(
                species_name="water",
                backend="gaussian",
                method="wb97xd",
                basis="6-31g",
                task="single_point",
                success=True,
                electronic_energy_hartree=None,
            )
        ],
    )

    exit_code = main(["check-results", str(results_path), "--json"])

    payload = json.loads(capsys.readouterr().out)
    assert exit_code == 0
    assert payload["summary"]["warning"] == 1
    assert payload["checks"][0]["code"] == "missing_electronic_energy"


def test_check_results_uses_species_registry(tmp_path, capsys):
    project_path = tmp_path / "demo"
    assert main(["init", str(project_path), "--template", "basic"]) == 0
    results_path = tmp_path / "results.json"
    save_result_collection(
        results_path,
        [
            CalculationResult(
                species_name="water",
                backend="gaussian",
                method="wb97xd",
                basis="6-31g",
                task="single_point",
                success=True,
                electronic_energy_hartree=-76.0,
            )
        ],
    )

    exit_code = main(
        [
            "check-results",
            str(results_path),
            "--species",
            str(project_path / "species.yaml"),
        ]
    )

    captured = capsys.readouterr()
    assert exit_code == 0
    assert "unmatched_species" in captured.out


def test_reaction_table_electronic_mode(tmp_path, capsys):
    pathway_path = tmp_path / "pathway.yaml"
    pathway_path.write_text(
        "schema_version: 1\n"
        "reactions:\n"
        "  - id: r1\n"
        "    label: A to B\n"
        "    reactants: {A: 1}\n"
        "    products: {B: 1}\n",
        encoding="utf-8",
    )
    results_path = tmp_path / "results.json"
    save_result_collection(
        results_path,
        [
            CalculationResult(
                species_name="A",
                backend="gaussian",
                method="wb97xd",
                basis="6-31g",
                task="single_point",
                success=True,
                electronic_energy_hartree=-2.0,
            ),
            CalculationResult(
                species_name="B",
                backend="gaussian",
                method="wb97xd",
                basis="6-31g",
                task="single_point",
                success=True,
                electronic_energy_hartree=-1.5,
            ),
        ],
    )
    out_path = tmp_path / "reaction_table.csv"

    exit_code = main(
        [
            "reaction-table",
            str(pathway_path),
            str(results_path),
            "--quantity",
            "electronic",
            "--out",
            str(out_path),
        ]
    )

    captured = capsys.readouterr()
    rows = list(csv.DictReader(out_path.open(encoding="utf-8", newline="")))
    assert exit_code == 0
    assert "delta_e_electronic" in captured.out
    assert rows[0]["quantity"] == "delta_e_electronic"
    assert float(rows[0]["delta_hartree"]) == 0.5


def test_reaction_table_gibbs_mode(tmp_path):
    pathway_path = tmp_path / "pathway.yaml"
    pathway_path.write_text(
        "schema_version: 1\n"
        "reactions:\n"
        "  - id: r1\n"
        "    reactants: {A: 1}\n"
        "    products: {B: 1}\n",
        encoding="utf-8",
    )
    results_path = tmp_path / "results.json"
    save_result_collection(
        results_path,
        [
            CalculationResult(
                species_name="A",
                backend="gaussian",
                method="wb97xd",
                basis="6-31g",
                task="freq",
                success=True,
                gibbs_free_energy_hartree=-2.0,
            ),
            CalculationResult(
                species_name="B",
                backend="gaussian",
                method="wb97xd",
                basis="6-31g",
                task="freq",
                success=True,
                gibbs_free_energy_hartree=-1.25,
            ),
        ],
    )
    out_path = tmp_path / "reaction_table.csv"

    exit_code = main(
        [
            "reaction-table",
            str(pathway_path),
            str(results_path),
            "--quantity",
            "gibbs",
            "--out",
            str(out_path),
        ]
    )

    rows = list(csv.DictReader(out_path.open(encoding="utf-8", newline="")))
    assert exit_code == 0
    assert rows[0]["quantity"] == "delta_g_gibbs"
    assert float(rows[0]["delta_hartree"]) == 0.75


def test_reaction_table_missing_data(tmp_path):
    pathway_path = tmp_path / "pathway.yaml"
    pathway_path.write_text(
        "schema_version: 1\n"
        "reactions:\n"
        "  - id: r1\n"
        "    reactants: {A: 1}\n"
        "    products: {B: 1}\n",
        encoding="utf-8",
    )
    results_path = tmp_path / "results.json"
    save_result_collection(
        results_path,
        [
            CalculationResult(
                species_name="A",
                backend="gaussian",
                method="wb97xd",
                basis="6-31g",
                task="single_point",
                success=True,
                electronic_energy_hartree=-2.0,
            )
        ],
    )
    out_path = tmp_path / "reaction_table.csv"

    exit_code = main(
        [
            "reaction-table",
            str(pathway_path),
            str(results_path),
            "--quantity",
            "electronic",
            "--out",
            str(out_path),
        ]
    )

    rows = list(csv.DictReader(out_path.open(encoding="utf-8", newline="")))
    assert exit_code == 0
    assert rows[0]["complete"] == "False"
    assert rows[0]["missing_species"] == "B"
    assert rows[0]["delta_hartree"] == ""


def _write_adsorption_cli_fixture(
    adsorption_path, system_id="co_on_surface", adsorbate="co_gas", combined="slab_co"
) -> None:
    adsorption_path.write_text(
        "schema_version: 1\n"
        "adsorption_systems:\n"
        f"  - id: {system_id}\n"
        "    slab_result: slab_clean\n"
        f"    adsorbate_result: {adsorbate}\n"
        f"    combined_result: {combined}\n",
        encoding="utf-8",
    )


def _save_adsorption_cli_results(results_path, results) -> None:
    save_result_collection(
        results_path,
        [CalculationResult(**result) for result in results],
    )


def test_adsorption_table_electronic_mode(tmp_path, capsys):
    adsorption_path = tmp_path / "adsorption.yaml"
    _write_adsorption_cli_fixture(adsorption_path)
    results_path = tmp_path / "results.json"
    _save_adsorption_cli_results(
        results_path,
        [
            {
                "species_name": "slab_clean",
                "backend": "qe",
                "method": "pbe",
                "basis": "ecutwfc=40",
                "task": "scf",
                "success": True,
                "electronic_energy_hartree": -100.0,
            },
            {
                "species_name": "co_gas",
                "backend": "qe",
                "method": "pbe",
                "basis": "ecutwfc=40",
                "task": "scf",
                "success": True,
                "electronic_energy_hartree": -10.0,
            },
            {
                "species_name": "slab_co",
                "backend": "qe",
                "method": "pbe",
                "basis": "ecutwfc=40",
                "task": "scf",
                "success": True,
                "electronic_energy_hartree": -111.0,
            },
        ],
    )
    out_path = tmp_path / "adsorption_table.csv"

    exit_code = main(
        [
            "adsorption-table",
            str(adsorption_path),
            str(results_path),
            "--quantity",
            "electronic",
            "--out",
            str(out_path),
        ]
    )

    captured = capsys.readouterr()
    rows = list(csv.DictReader(out_path.open(encoding="utf-8", newline="")))
    assert exit_code == 0
    assert "adsorption_electronic_energy" in captured.out
    assert rows[0]["system_id"] == "co_on_surface"
    assert float(rows[0]["adsorption_energy_hartree"]) == -1.0


def test_adsorption_table_gibbs_mode(tmp_path):
    adsorption_path = tmp_path / "adsorption.yaml"
    _write_adsorption_cli_fixture(adsorption_path)
    results_path = tmp_path / "results.json"
    _save_adsorption_cli_results(
        results_path,
        [
            {
                "species_name": "slab_clean",
                "backend": "qe",
                "method": "pbe",
                "basis": "ecutwfc=40",
                "task": "scf",
                "success": True,
                "gibbs_free_energy_hartree": -100.2,
            },
            {
                "species_name": "co_gas",
                "backend": "qe",
                "method": "pbe",
                "basis": "ecutwfc=40",
                "task": "scf",
                "success": True,
                "gibbs_free_energy_hartree": -10.2,
            },
            {
                "species_name": "slab_co",
                "backend": "qe",
                "method": "pbe",
                "basis": "ecutwfc=40",
                "task": "scf",
                "success": True,
                "gibbs_free_energy_hartree": -111.0,
            },
        ],
    )
    out_path = tmp_path / "adsorption_table.csv"

    exit_code = main(
        [
            "adsorption-table",
            str(adsorption_path),
            str(results_path),
            "--quantity",
            "gibbs",
            "--out",
            str(out_path),
        ]
    )

    rows = list(csv.DictReader(out_path.open(encoding="utf-8", newline="")))
    assert exit_code == 0
    assert rows[0]["quantity"] == "adsorption_gibbs_free_energy"
    assert float(rows[0]["adsorption_energy_hartree"]) == pytest.approx(-0.6)


def test_adsorption_table_missing_data(tmp_path):
    adsorption_path = tmp_path / "adsorption.yaml"
    _write_adsorption_cli_fixture(adsorption_path)
    results_path = tmp_path / "results.json"
    _save_adsorption_cli_results(
        results_path,
        [
            {
                "species_name": "slab_clean",
                "backend": "qe",
                "method": "pbe",
                "basis": "ecutwfc=40",
                "task": "scf",
                "success": True,
                "electronic_energy_hartree": -100.0,
            },
            {
                "species_name": "co_gas",
                "backend": "qe",
                "method": "pbe",
                "basis": "ecutwfc=40",
                "task": "scf",
                "success": True,
                "electronic_energy_hartree": -10.0,
            },
        ],
    )
    out_path = tmp_path / "adsorption_table.csv"

    exit_code = main(
        [
            "adsorption-table",
            str(adsorption_path),
            str(results_path),
            "--quantity",
            "electronic",
            "--out",
            str(out_path),
        ]
    )

    rows = list(csv.DictReader(out_path.open(encoding="utf-8", newline="")))
    assert exit_code == 0
    assert rows[0]["complete"] == "False"
    assert rows[0]["missing"] == "missing_result:combined:slab_co"
    assert rows[0]["adsorption_energy_hartree"] == ""


def test_adsorption_table_csv_output_includes_units(tmp_path):
    adsorption_path = tmp_path / "adsorption.yaml"
    _write_adsorption_cli_fixture(
        adsorption_path, system_id="h_on_surface", adsorbate="h_gas", combined="slab_h"
    )
    results_path = tmp_path / "results.json"
    _save_adsorption_cli_results(
        results_path,
        [
            {
                "species_name": "slab_clean",
                "backend": "qe",
                "method": "pbe",
                "basis": "ecutwfc=40",
                "task": "scf",
                "success": True,
                "electronic_energy_hartree": -100.0,
            },
            {
                "species_name": "h_gas",
                "backend": "qe",
                "method": "pbe0",
                "basis": "ecutwfc=40",
                "task": "scf",
                "success": True,
                "electronic_energy_hartree": -1.0,
            },
            {
                "species_name": "slab_h",
                "backend": "qe",
                "method": "pbe",
                "basis": "ecutwfc=40",
                "task": "scf",
                "success": True,
                "electronic_energy_hartree": -102.0,
            },
        ],
    )
    out_path = tmp_path / "adsorption_table.csv"

    exit_code = main(
        [
            "adsorption-table",
            str(adsorption_path),
            str(results_path),
            "--quantity",
            "electronic",
            "--out",
            str(out_path),
        ]
    )

    rows = list(csv.DictReader(out_path.open(encoding="utf-8", newline="")))
    assert exit_code == 0
    assert {
        "adsorption_energy_hartree",
        "adsorption_energy_ev",
        "adsorption_energy_kj_mol",
    }.issubset(rows[0])
    assert "mixed backend/method" in rows[0]["warnings"]


def _write_che_cli_fixture(tmp_path, extra_fields: str = ""):
    path = tmp_path / "che_pathway.yaml"
    path.write_text(
        "schema_version: 1\n"
        "reactions:\n"
        "  - id: r1\n"
        "    reactants: {A: 1}\n"
        "    products: {B: 1}\n"
        f"{extra_fields}",
        encoding="utf-8",
    )
    return path


def _write_che_cli_results(results_path, include_b: bool = True) -> None:
    results = [
        CalculationResult(
            species_name="A",
            backend="gaussian",
            method="b3lyp",
            basis="def2-svp",
            task="freq",
            success=True,
            gibbs_free_energy_hartree=-2.0,
        )
    ]
    if include_b:
        results.append(
            CalculationResult(
                species_name="B",
                backend="gaussian",
                method="b3lyp",
                basis="def2-svp",
                task="freq",
                success=True,
                gibbs_free_energy_hartree=-1.9,
            )
        )
    save_result_collection(results_path, results)


def test_che_table_basic(tmp_path, capsys):
    pathway_path = _write_che_cli_fixture(tmp_path)
    results_path = tmp_path / "results.json"
    _write_che_cli_results(results_path)
    out_path = tmp_path / "che_table.csv"

    exit_code = main(
        [
            "che-table",
            str(pathway_path),
            str(results_path),
            "--out",
            str(out_path),
        ]
    )

    captured = capsys.readouterr()
    rows = list(csv.DictReader(out_path.open(encoding="utf-8", newline="")))
    assert exit_code == 0
    assert "corrected_delta_g_ev" in captured.out
    assert rows[0]["reaction_id"] == "r1"
    assert rows[0]["complete"] == "True"
    assert rows[0]["corrected_delta_g_ev"] == rows[0]["uncorrected_delta_g_ev"]


def test_che_table_shows_correction_terms(tmp_path):
    pathway_path = _write_che_cli_fixture(
        tmp_path,
        "    proton_electron_pairs: 1\n"
        "    potential_V: 0.5\n"
        "    potential_reference: SHE\n"
        "    correction_terms:\n"
        "      - label: user supplied term\n"
        "        value_eV: 0.1\n"
        "        sign_convention: added to uncorrected delta G\n"
        "        source: synthetic fixture table\n",
    )
    results_path = tmp_path / "results.json"
    _write_che_cli_results(results_path)
    out_path = tmp_path / "che_table.csv"

    exit_code = main(
        [
            "che-table",
            str(pathway_path),
            str(results_path),
            "--out",
            str(out_path),
        ]
    )

    rows = list(csv.DictReader(out_path.open(encoding="utf-8", newline="")))
    assert exit_code == 0
    assert "user supplied term=0.1 eV" in rows[0]["correction_terms"]
    assert "CHE potential correction=-0.5 eV" in rows[0]["correction_terms"]
    assert float(rows[0]["correction_total_eV"]) == pytest.approx(-0.4)


def test_che_table_missing_data(tmp_path):
    pathway_path = _write_che_cli_fixture(
        tmp_path,
        "    proton_electron_pairs: 1\n"
        "    potential_V: 0.5\n"
        "    potential_reference: SHE\n",
    )
    results_path = tmp_path / "results.json"
    _write_che_cli_results(results_path, include_b=False)
    out_path = tmp_path / "che_table.csv"

    exit_code = main(
        [
            "che-table",
            str(pathway_path),
            str(results_path),
            "--out",
            str(out_path),
        ]
    )

    rows = list(csv.DictReader(out_path.open(encoding="utf-8", newline="")))
    assert exit_code == 0
    assert rows[0]["complete"] == "False"
    assert rows[0]["missing_species"] == "B"
    assert rows[0]["corrected_delta_g_ev"] == ""
    assert rows[0]["correction_total_eV"] == "-0.5"


def test_che_table_csv_output_has_units(tmp_path):
    pathway_path = _write_che_cli_fixture(
        tmp_path,
        "    proton_electron_pairs: 1\n"
        "    pH: 7\n",
    )
    results_path = tmp_path / "results.json"
    _write_che_cli_results(results_path)
    out_path = tmp_path / "che_table.csv"

    exit_code = main(
        [
            "che-table",
            str(pathway_path),
            str(results_path),
            "--out",
            str(out_path),
        ]
    )

    rows = list(csv.DictReader(out_path.open(encoding="utf-8", newline="")))
    assert exit_code == 0
    assert {
        "uncorrected_delta_g_ev",
        "correction_total_eV",
        "corrected_delta_g_ev",
        "corrected_delta_g_kj_mol",
    }.issubset(rows[0])
    assert "CHE pH correction" in rows[0]["correction_terms"]


def test_select_conformers_writes_json(tmp_path, capsys):
    results_path = tmp_path / "results.json"
    out_path = tmp_path / "selected_conformers.json"
    save_result_collection(
        results_path,
        [
            CalculationResult(
                species_name="ethanol",
                conformer_id="conf_001",
                backend="gaussian",
                method="b3lyp",
                basis="def2-svp",
                task="single_point",
                success=True,
                electronic_energy_hartree=-10.0,
            ),
            CalculationResult(
                species_name="ethanol",
                conformer_id="conf_002",
                backend="gaussian",
                method="b3lyp",
                basis="def2-svp",
                task="single_point",
                success=True,
                electronic_energy_hartree=-10.2,
            ),
        ],
    )

    exit_code = main(
        [
            "select-conformers",
            str(results_path),
            "--quantity",
            "electronic",
            "--out",
            str(out_path),
        ]
    )

    payload = json.loads(out_path.read_text(encoding="utf-8"))
    captured = capsys.readouterr()
    assert exit_code == 0
    assert payload["selections"][0]["selected_conformer_id"] == "conf_002"
    assert "ethanol\tconf_002" in captured.out


def test_report_command_writes_markdown(tmp_path, capsys):
    project_path = tmp_path / "demo"
    assert main(["init", str(project_path), "--template", "basic"]) == 0
    results_path = project_path / "results" / "results.json"
    save_result_collection(
        results_path,
        [
            CalculationResult(
                species_name="water",
                backend="gaussian",
                method="wb97xd",
                basis="6-31g",
                task="single_point",
                success=True,
                electronic_energy_hartree=-76.0,
            )
        ],
    )
    out_path = project_path / "reports" / "report.md"

    exit_code = main(
        [
            "report",
            str(results_path),
            "--species",
            str(project_path / "species.yaml"),
            "--out",
            str(out_path),
        ]
    )

    captured = capsys.readouterr()
    report = out_path.read_text(encoding="utf-8")
    assert exit_code == 0
    assert "Wrote Markdown report" in captured.out
    assert "# qchem-workbench report" in report
    assert "## Quality-check summary" in report
    assert "unmatched_species" in report


def test_plot_pathway_command_writes_png(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("MPLCONFIGDIR", str(tmp_path / "mpl"))
    table_path = tmp_path / "reaction_table.csv"
    table_path.write_text(
        "reaction_id,label,quantity,complete,delta_hartree,delta_ev,delta_kj_mol,"
        "missing_species,notes\n"
        "r1,A to B,delta_e_electronic,True,0.1,2.7,262.5,,synthetic fixture\n",
        encoding="utf-8",
    )
    out_path = tmp_path / "pathway.png"

    exit_code = main(["plot-pathway", str(table_path), "--out", str(out_path)])

    captured = capsys.readouterr()
    assert exit_code == 0
    assert "Wrote pathway plot" in captured.out
    assert out_path.read_bytes().startswith(b"\x89PNG")


def test_plot_spectrum_command_writes_png_and_csv(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("MPLCONFIGDIR", str(tmp_path / "mpl"))
    results_path = tmp_path / "results.json"
    save_result_collection(
        results_path,
        [
            CalculationResult(
                species_name="water",
                backend="gaussian",
                method="b3lyp",
                basis="def2-svp",
                task="freq",
                success=True,
                properties=CalculationProperties(
                    vibrational_modes=(
                        VibrationalMode(
                            frequency_cm1=100.0,
                            ir_intensity_km_mol=2.0,
                        ),
                    )
                ),
            )
        ],
    )
    out_path = tmp_path / "water_ir.png"

    exit_code = main(
        [
            "plot-spectrum",
            str(results_path),
            "--species",
            "water",
            "--type",
            "ir",
            "--out",
            str(out_path),
        ]
    )

    captured = capsys.readouterr()
    csv_path = out_path.with_suffix(".csv")
    assert exit_code == 0
    assert "Wrote IR spectrum plot" in captured.out
    assert out_path.read_bytes().startswith(b"\x89PNG")
    assert csv_path.exists()
    assert "intensity_km_mol" in csv_path.read_text(encoding="utf-8").splitlines()[0]


def test_descriptor_table_command_writes_csv(tmp_path, capsys):
    campaign_path = tmp_path / "campaign.yaml"
    campaign_path.write_text(
        "schema_version: 1\n"
        "campaign:\n"
        "  name: demo\n"
        "  results: results/results.json\n"
        "  candidates:\n"
        "    - id: water\n"
        "      species: water\n"
        "  descriptors:\n"
        "    - name: electronic_energy_hartree\n"
        "      source: result\n"
        "      field: electronic_energy_hartree\n"
        "    - name: gap_ev\n"
        "      source: result\n"
        "      field: gap_ev\n",
        encoding="utf-8",
    )
    results_path = tmp_path / "results.json"
    save_result_collection(
        results_path,
        [
            CalculationResult(
                species_name="water",
                backend="gaussian",
                method="wb97xd",
                basis="6-31g",
                task="single_point",
                success=True,
                electronic_energy_hartree=-76.0,
            )
        ],
    )
    out_path = tmp_path / "descriptors.csv"

    exit_code = main(
        [
            "descriptor-table",
            str(campaign_path),
            str(results_path),
            "--out",
            str(out_path),
        ]
    )

    captured = capsys.readouterr()
    with out_path.open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    assert exit_code == 0
    assert "Wrote descriptor table for 1 candidate" in captured.out
    assert rows[0]["candidate_id"] == "water"
    assert rows[0]["electronic_energy_hartree"] == "-76.0"
    assert rows[0]["gap_ev"] == ""
    assert rows[0]["quality_flags"] == ""


def test_rank_candidates_command_writes_ranked_csv(tmp_path, capsys):
    campaign_path = _write_ranking_campaign(
        tmp_path,
        ranking=(
            "      - descriptor: gap_ev\n"
            "        direction: maximize\n"
            "        weight: 2.0\n"
        ),
    )
    descriptors_path = tmp_path / "descriptors.csv"
    descriptors_path.write_text(
        "candidate_id,gap_ev,quality_error_count\n"
        "a,2.0,0\n"
        "b,3.0,0\n",
        encoding="utf-8",
    )
    out_path = tmp_path / "ranked.csv"

    exit_code = main(
        [
            "rank-candidates",
            str(campaign_path),
            str(descriptors_path),
            "--out",
            str(out_path),
        ]
    )

    captured = capsys.readouterr()
    with out_path.open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    assert exit_code == 0
    assert "rank\tcandidate_id\tscore" in captured.out
    assert rows[0]["candidate_id"] == "b"
    assert rows[0]["rank"] == "1"
    assert rows[0]["rank_score"] == "6.0"
    assert rows[0]["score_component_gap_ev"] == "6.0"


def test_rank_candidates_command_filters_quality_errors(tmp_path, capsys):
    campaign_path = _write_ranking_campaign(
        tmp_path,
        ranking=(
            "      - descriptor: quality_error_count\n"
            "        filter: exclude_quality_errors\n"
            "      - descriptor: gap_ev\n"
            "        direction: maximize\n"
        ),
    )
    descriptors_path = tmp_path / "descriptors.csv"
    descriptors_path.write_text(
        "candidate_id,gap_ev,quality_error_count\n"
        "a,2.0,0\n"
        "b,3.0,1\n",
        encoding="utf-8",
    )
    out_path = tmp_path / "ranked.csv"

    exit_code = main(
        [
            "rank-candidates",
            str(campaign_path),
            str(descriptors_path),
            "--out",
            str(out_path),
        ]
    )

    captured = capsys.readouterr()
    with out_path.open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    excluded = {row["candidate_id"]: row for row in rows if row["rank_status"] == "excluded"}
    assert exit_code == 0
    assert "Excluded candidates\t1" in captured.out
    assert excluded["b"]["ranking_reasons"] == "quality_errors_present"


def test_rank_candidates_command_keeps_missing_values_unranked(tmp_path):
    campaign_path = _write_ranking_campaign(
        tmp_path,
        ranking=(
            "      - descriptor: gap_ev\n"
            "        direction: maximize\n"
        ),
    )
    descriptors_path = tmp_path / "descriptors.csv"
    descriptors_path.write_text(
        "candidate_id,gap_ev,quality_error_count\n"
        "a,,0\n",
        encoding="utf-8",
    )
    out_path = tmp_path / "ranked.csv"

    exit_code = main(
        [
            "rank-candidates",
            str(campaign_path),
            str(descriptors_path),
            "--out",
            str(out_path),
        ]
    )

    with out_path.open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    assert exit_code == 0
    assert rows[0]["rank"] == ""
    assert rows[0]["rank_status"] == "excluded"
    assert rows[0]["ranking_reasons"] == "missing_descriptor:gap_ev"
    assert rows[0]["gap_ev"] == ""


def test_run_project_renders_gaussian_inputs(tmp_path, capsys):
    project_path = tmp_path / "demo"
    assert main(["init", str(project_path), "--template", "basic"]) == 0
    manifest_path = project_path / "qchem_project.yaml"
    manifest_path.write_text(
        "schema_version: 1\n"
        "project:\n"
        "  name: demo\n"
        "  species: species.yaml\n"
        "  inputs: gaussian_inputs\n"
        "  backend_mode: gaussian\n"
        "  calculation:\n"
        "    method: wb97xd\n"
        "    basis: 6-31g\n"
        "    task: single_point\n"
        "  steps: [render_gaussian]\n",
        encoding="utf-8",
    )

    exit_code = main(["run-project", str(manifest_path)])

    captured = capsys.readouterr()
    assert exit_code == 0
    assert "STEP render_gaussian" in captured.out
    assert (project_path / "gaussian_inputs" / "water.gjf").exists()


def test_run_project_runs_mocked_pyscf_and_report(
    tmp_path, monkeypatch, capsys
):
    project_path = tmp_path / "demo"
    assert main(["init", str(project_path), "--template", "basic"]) == 0
    manifest_path = project_path / "qchem_project.yaml"
    manifest_path.write_text(
        "schema_version: 1\n"
        "project:\n"
        "  name: demo\n"
        "  species: species.yaml\n"
        "  results: results/results.json\n"
        "  reports: reports/report.md\n"
        "  backend_mode: pyscf\n"
        "  calculation:\n"
        "    method: b3lyp\n"
        "    basis: sto-3g\n"
        "    task: single_point\n"
        "  steps: [run_pyscf, quality_checks, report]\n",
        encoding="utf-8",
    )

    class FakeBackend:
        def run(self, species, spec):
            return CalculationResult(
                species_name=species.name,
                backend="pyscf",
                method=spec.method,
                basis=spec.basis,
                task=spec.task,
                success=True,
                electronic_energy_hartree=-1.0,
            )

    monkeypatch.setattr("qchem_workbench.cli.PySCFBackend", FakeBackend)

    exit_code = main(["run-project", str(manifest_path)])

    captured = capsys.readouterr()
    payload = json.loads(
        (project_path / "results" / "results.json").read_text(encoding="utf-8")
    )
    report = (project_path / "reports" / "report.md").read_text(encoding="utf-8")
    assert exit_code == 0
    assert "STEP run_pyscf" in captured.out
    assert "STEP report" in captured.out
    assert len(payload["results"]) == 3
    assert "# qchem-workbench report" in report


def test_run_project_parses_gaussian_fixture_and_generates_report(
    tmp_path, capsys
):
    project_path = tmp_path / "demo"
    assert main(["init", str(project_path), "--template", "basic"]) == 0
    outputs = project_path / "outputs"
    (outputs / "water.log").write_text(
        " # wb97xd/6-31g\n"
        " SCF Done:  E(RB3LYP) =  -76.1000000000     A.U. after 10 cycles\n"
        " Normal termination of Gaussian 16\n",
        encoding="utf-8",
    )
    manifest_path = project_path / "qchem_project.yaml"
    manifest_path.write_text(
        "schema_version: 1\n"
        "project:\n"
        "  name: demo\n"
        "  species: species.yaml\n"
        "  outputs: outputs\n"
        "  results: results/gaussian_results.json\n"
        "  reports: reports/report.md\n"
        "  steps: [parse_gaussian, quality_checks, report]\n",
        encoding="utf-8",
    )

    exit_code = main(["run-project", str(manifest_path)])

    captured = capsys.readouterr()
    payload = json.loads(
        (project_path / "results" / "gaussian_results.json").read_text(
            encoding="utf-8"
        )
    )
    report = (project_path / "reports" / "report.md").read_text(encoding="utf-8")
    assert exit_code == 0
    assert "STEP parse_gaussian" in captured.out
    assert payload["results"][0]["species_name"] == "water"
    assert payload["results"][0]["electronic_energy_hartree"] == -76.1
    assert "unmatched_species" in report


def test_triage_command_writes_failed_jobs_markdown(tmp_path, capsys):
    results_path = tmp_path / "results.json"
    save_result_collection(
        results_path,
        [
            CalculationResult(
                species_name="missing-energy",
                backend="gaussian",
                method="wb97xd",
                basis="6-31g",
                task="single_point",
                success=True,
                warnings=["SCF electronic energy was not parsed."],
            )
        ],
    )
    out_path = tmp_path / "failed_jobs.md"

    exit_code = main(["triage", str(results_path), "--out", str(out_path)])

    captured = capsys.readouterr()
    report = out_path.read_text(encoding="utf-8")
    assert exit_code == 0
    assert "missing_energy" in captured.out
    assert "# Failed job triage" in report
    assert "missing-energy" in report


def _write_ranking_campaign(tmp_path, *, ranking: str):
    campaign_path = tmp_path / "campaign.yaml"
    campaign_path.write_text(
        "schema_version: 1\n"
        "campaign:\n"
        "  name: demo\n"
        "  results: results/results.json\n"
        "  candidates:\n"
        "    - id: a\n"
        "      species: a\n"
        "    - id: b\n"
        "      species: b\n"
        "  descriptors:\n"
        "    - name: gap_ev\n"
        "      source: result\n"
        "      field: gap_ev\n"
        "  ranking:\n"
        "    rules:\n"
        f"{ranking}",
        encoding="utf-8",
    )
    return campaign_path
