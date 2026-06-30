from __future__ import annotations

import pytest

from qchem_workbench.backends.registry import (
    BackendCapabilities,
    BackendCapability,
    BackendMetadata,
    BackendRegistry,
    BackendRegistryError,
    get_backend,
    list_backends,
)
from qchem_workbench.cli import main


def test_list_built_in_backends():
    names = {backend.name for backend in list_backends()}

    assert {"ase", "gaussian", "orca", "pyscf", "qe"} <= names


def test_backend_capability_creation_and_serialisation():
    capability = BackendCapability(
        backend_id=" Example ",
        display_name="Example Backend",
        can_parse_output=True,
        supports_molecular=True,
        requires_external_executable=True,
        notes=("fixture backend",),
        stability="experimental",
        properties_supported=("electronic_energy",),
    )

    data = capability.to_dict()

    assert capability.backend_id == "example"
    assert data["backend_id"] == "example"
    assert data["can_parse_output"] is True
    assert data["supports_molecular"] is True
    assert data["requires_external_executable"] is True
    assert data["stability"] == "experimental"
    assert data["properties_supported"] == ["electronic_energy"]
    assert data["capabilities"]["output_parsing"] is True


def test_backend_capability_rejects_unknown_stability():
    with pytest.raises(ValueError, match="stability"):
        BackendCapability(
            backend_id="bad",
            display_name="Bad Backend",
            stability="beta",  # type: ignore[arg-type]
        )


def test_query_backend_capabilities():
    gaussian = get_backend("Gaussian")
    qe = get_backend("qe")

    assert gaussian.capabilities.input_rendering is True
    assert gaussian.capabilities.output_parsing is True
    assert gaussian.capabilities.execution is False
    assert gaussian.capabilities.molecular_support is True
    assert "dipole_moment" in gaussian.capabilities.properties_supported
    assert "population_analysis" in gaussian.capabilities.properties_supported
    assert "vibrational_frequencies" in gaussian.capabilities.properties_supported
    assert qe.capabilities.periodic_support is True


def test_conservative_gaussian_and_qe_flags():
    gaussian = get_backend("gaussian")
    qe = get_backend("qe")

    assert gaussian.can_render_input is True
    assert gaussian.can_parse_output is True
    assert gaussian.can_execute is False
    assert gaussian.requires_external_executable is True
    assert gaussian.supports_periodic is False
    assert gaussian.supports_thermochemistry is True
    assert gaussian.supports_forces is False
    assert qe.display_name == "Quantum ESPRESSO pw.x"
    assert qe.can_execute is False
    assert qe.supports_periodic is True
    assert qe.supports_forces is True
    assert qe.supports_stress is True
    assert qe.supports_thermochemistry is False
    assert qe.supports_microkinetics is False


def test_ase_registered_as_optional_experimental_helper():
    ase = get_backend("ase")

    assert ase.can_execute is False
    assert ase.can_render_input is False
    assert ase.can_parse_output is False
    assert ase.required_optional_extra == "ase"
    assert ase.stability == "experimental"


def test_missing_backend_error_is_clear():
    with pytest.raises(BackendRegistryError, match="available backends"):
        get_backend("missing-backend")


def test_custom_backend_registration():
    registry = BackendRegistry()
    registry.register(
        BackendMetadata(
            name="custom",
            display_name="Custom Backend",
            capabilities=BackendCapabilities(output_parsing=True),
        )
    )

    assert registry.names() == ("custom",)
    assert registry.get("CUSTOM").capabilities.output_parsing is True


def test_cli_lists_registered_backend_capabilities(capsys):
    exit_code = main(["backends"])

    captured = capsys.readouterr()
    assert exit_code == 0
    assert "backend\tinput_rendering\toutput_parsing" in captured.out
    assert "gaussian\tTrue\tTrue\tFalse\tTrue\tFalse" in captured.out
    assert "qe\tTrue\tTrue\tFalse\tTrue\tTrue" in captured.out
