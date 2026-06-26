from __future__ import annotations

import pytest

from qchem_workbench.backends.registry import (
    BackendCapabilities,
    BackendMetadata,
    BackendRegistry,
    BackendRegistryError,
    get_backend,
    list_backends,
)
from qchem_workbench.cli import main


def test_list_built_in_backends():
    names = {backend.name for backend in list_backends()}

    assert {"gaussian", "orca", "pyscf", "qe"} <= names


def test_query_backend_capabilities():
    gaussian = get_backend("Gaussian")
    qe = get_backend("qe")

    assert gaussian.capabilities.input_rendering is True
    assert gaussian.capabilities.output_parsing is True
    assert gaussian.capabilities.execution is False
    assert gaussian.capabilities.molecular_support is True
    assert "vibrational_frequencies" in gaussian.capabilities.properties_supported
    assert qe.capabilities.periodic_support is True


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
