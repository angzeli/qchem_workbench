from __future__ import annotations

import pytest

from qchem_workbench.backends.qe_input import QEKPoints, QEInputSpec, render_qe_pw_input
from qchem_workbench.backends.qe_pseudos import load_pseudopotential_manifest
from qchem_workbench.core.geometry import Atom
from qchem_workbench.core.structure import AtomisticStructure


def test_valid_pseudopotential_manifest(tmp_path):
    manifest_path = _write_manifest(tmp_path)

    manifest = load_pseudopotential_manifest(manifest_path)

    oxygen = manifest.for_element("O")
    assert oxygen.filename == "O.pbe.UPF"
    assert oxygen.family == "Synthetic fixture family"
    assert oxygen.functional == "PBE"
    assert oxygen.source == "Synthetic fixture only"
    assert manifest.pseudopotential_mapping(["O", "Zn"]) == {
        "O": "O.pbe.UPF",
        "Zn": "Zn.pbe.UPF",
    }


def test_missing_pseudopotential_for_structure(tmp_path):
    manifest = load_pseudopotential_manifest(_write_manifest(tmp_path))
    structure = AtomisticStructure(
        atoms=(Atom("O", 0.0, 0.0, 0.0), Atom("H", 0.0, 0.0, 1.0)),
        cell=((10.0, 0.0, 0.0), (0.0, 10.0, 0.0), (0.0, 0.0, 10.0)),
    )

    assert manifest.missing_elements_for_structure(structure) == ("H",)
    with pytest.raises(ValueError, match="missing element"):
        manifest.pseudopotential_mapping_for_structure(structure)


def test_suggested_cutoff_aggregation(tmp_path):
    manifest = load_pseudopotential_manifest(_write_manifest(tmp_path))

    suggestion = manifest.suggested_cutoffs(["O", "Zn"])

    assert suggestion.ecutwfc_ry == 70.0
    assert suggestion.ecutrho_ry == 560.0
    assert suggestion.missing_elements == ()
    assert suggestion.missing_cutoff_elements == ()


def test_unsupported_manifest_schema_version(tmp_path):
    manifest_path = tmp_path / "pseudos.yaml"
    manifest_path.write_text(
        "schema_version: 99\npseudopotentials: {}\n",
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="unsupported schema_version"):
        load_pseudopotential_manifest(manifest_path)


def test_missing_pseudopotential_file_is_warning(tmp_path):
    manifest = load_pseudopotential_manifest(
        _write_manifest(tmp_path),
        pseudo_dir=tmp_path / "pseudo_files",
    )

    assert "was not found" in manifest.warnings[0]


def test_manifest_mapping_can_feed_qe_renderer(tmp_path):
    manifest = load_pseudopotential_manifest(_write_manifest(tmp_path))
    structure = AtomisticStructure(
        atoms=(Atom("O", 0.0, 0.0, 0.0),),
        cell=((10.0, 0.0, 0.0), (0.0, 10.0, 0.0), (0.0, 0.0, 10.0)),
    )
    spec = QEInputSpec(
        calculation="scf",
        prefix="oxygen-demo",
        pseudo_dir="./pseudos",
        outdir="./tmp",
        ecutwfc=60.0,
        k_points=QEKPoints(mode="gamma"),
        pseudopotentials=manifest.pseudopotential_mapping_for_structure(structure),
        atomic_masses={"O": 15.999},
    )

    rendered = render_qe_pw_input(structure, spec)

    assert "ATOMIC_SPECIES\nO 15.999 O.pbe.UPF\n" in rendered


def _write_manifest(tmp_path):
    manifest_path = tmp_path / "pseudos.yaml"
    manifest_path.write_text(
        "schema_version: 1\n"
        "pseudopotentials:\n"
        "  O:\n"
        "    file: O.pbe.UPF\n"
        "    family: Synthetic fixture family\n"
        "    functional: PBE\n"
        "    suggested_ecutwfc_ry: 60\n"
        "    suggested_ecutrho_ry: 480\n"
        "    source: Synthetic fixture only\n"
        "  Zn:\n"
        "    file: Zn.pbe.UPF\n"
        "    family: Synthetic fixture family\n"
        "    functional: PBE\n"
        "    suggested_ecutwfc_ry: 70\n"
        "    suggested_ecutrho_ry: 560\n"
        "    source: Synthetic fixture only\n",
        encoding="utf-8",
    )
    return manifest_path
