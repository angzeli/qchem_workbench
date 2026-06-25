"""Starter project templates for qchemwb init."""

from __future__ import annotations


PROJECT_DIRECTORIES = ("xyz", "outputs", "results", "reports")
TEMPLATE_NAMES = ("blank", "basic", "co2rr")


def get_template_files(name: str) -> dict[str, str]:
    try:
        return dict(_TEMPLATES[name])
    except KeyError as exc:
        raise ValueError(f"unknown template {name!r}") from exc


_BLANK_SPECIES_YAML = """schema_version: 1
species: []
"""

_BASIC_SPECIES_YAML = """schema_version: 1
species:
  - name: water
    formula: H2O
    charge: 0
    multiplicity: 1
    geometry_path: xyz/water.xyz
    tags: [starter, synthetic]
    notes: Synthetic starter geometry; not reference scientific data.
  - name: carbon_dioxide
    formula: CO2
    charge: 0
    multiplicity: 1
    geometry_path: xyz/carbon_dioxide.xyz
    tags: [starter, synthetic]
    notes: Synthetic starter geometry; not reference scientific data.
  - name: carbon_monoxide
    formula: CO
    charge: 0
    multiplicity: 1
    geometry_path: xyz/carbon_monoxide.xyz
    tags: [starter, synthetic]
    notes: Synthetic starter geometry; not reference scientific data.
"""

_CO2RR_SPECIES_YAML = """schema_version: 1
species:
  - name: co2rr_carbon_dioxide
    formula: CO2
    charge: 0
    multiplicity: 1
    geometry_path: xyz/co2rr_carbon_dioxide.xyz
    tags: [co2rr-example, starter, synthetic]
    notes: Synthetic CO2RR starter example; not reference scientific data.
  - name: co2rr_carbon_monoxide
    formula: CO
    charge: 0
    multiplicity: 1
    geometry_path: xyz/co2rr_carbon_monoxide.xyz
    tags: [co2rr-example, starter, synthetic]
    notes: Synthetic CO2RR starter example; not reference scientific data.
  - name: co2rr_water
    formula: H2O
    charge: 0
    multiplicity: 1
    geometry_path: xyz/co2rr_water.xyz
    tags: [co2rr-example, starter, synthetic]
    notes: Synthetic CO2RR starter example; not reference scientific data.
"""

_WATER_XYZ = """3
synthetic starter geometry; not reference scientific data
O 0 0 0
H 0 0.757 0.586
H 0 -0.757 0.586
"""

_CARBON_DIOXIDE_XYZ = """3
synthetic starter geometry; not reference scientific data
C 0 0 0
O 0 0 1.16
O 0 0 -1.16
"""

_CARBON_MONOXIDE_XYZ = """2
synthetic starter geometry; not reference scientific data
C 0 0 0
O 0 0 1.13
"""

_TEMPLATES = {
    "blank": {
        "species.yaml": _BLANK_SPECIES_YAML,
    },
    "basic": {
        "species.yaml": _BASIC_SPECIES_YAML,
        "xyz/water.xyz": _WATER_XYZ,
        "xyz/carbon_dioxide.xyz": _CARBON_DIOXIDE_XYZ,
        "xyz/carbon_monoxide.xyz": _CARBON_MONOXIDE_XYZ,
    },
    "co2rr": {
        "species.yaml": _CO2RR_SPECIES_YAML,
        "xyz/co2rr_carbon_dioxide.xyz": _CARBON_DIOXIDE_XYZ,
        "xyz/co2rr_carbon_monoxide.xyz": _CARBON_MONOXIDE_XYZ,
        "xyz/co2rr_water.xyz": _WATER_XYZ,
    },
}
