"""Pseudopotential manifest support for Quantum ESPRESSO workflows."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

import yaml

from qchem_workbench.core.structure import AtomisticStructure


PSEUDOPOTENTIAL_MANIFEST_SCHEMA_VERSION = 1


@dataclass(frozen=True)
class PseudopotentialRecord:
    element: str
    filename: str
    family: str | None = None
    functional: str | None = None
    suggested_ecutwfc_ry: float | None = None
    suggested_ecutrho_ry: float | None = None
    source: str | None = None
    warnings: tuple[str, ...] = ()


@dataclass(frozen=True)
class CutoffSuggestion:
    ecutwfc_ry: float | None
    ecutrho_ry: float | None
    missing_elements: tuple[str, ...]
    missing_cutoff_elements: tuple[str, ...]


@dataclass(frozen=True)
class PseudopotentialManifest:
    records: dict[str, PseudopotentialRecord]
    source_path: Path | None = None
    warnings: tuple[str, ...] = ()

    def elements(self) -> tuple[str, ...]:
        return tuple(sorted(self.records))

    def for_element(self, element: str) -> PseudopotentialRecord:
        try:
            return self.records[element]
        except KeyError as exc:
            raise ValueError(f"pseudopotential manifest is missing {element}") from exc

    def missing_elements(self, elements: Iterable[str]) -> tuple[str, ...]:
        requested = {element for element in elements}
        return tuple(sorted(requested - set(self.records)))

    def missing_elements_for_structure(
        self, structure: AtomisticStructure
    ) -> tuple[str, ...]:
        return self.missing_elements(atom.symbol for atom in structure.atoms)

    def pseudopotential_mapping(
        self,
        elements: Iterable[str],
    ) -> dict[str, str]:
        requested = set(elements)
        missing = self.missing_elements(requested)
        if missing:
            raise ValueError(
                "pseudopotential manifest is missing element(s): "
                + ", ".join(missing)
            )
        return {element: self.records[element].filename for element in sorted(requested)}

    def pseudopotential_mapping_for_structure(
        self,
        structure: AtomisticStructure,
    ) -> dict[str, str]:
        return self.pseudopotential_mapping(atom.symbol for atom in structure.atoms)

    def suggested_cutoffs(
        self,
        elements: Iterable[str],
    ) -> CutoffSuggestion:
        missing = self.missing_elements(elements)
        ecutwfc_values: list[float] = []
        ecutrho_values: list[float] = []
        missing_cutoff: list[str] = []
        for element in sorted(set(elements) - set(missing)):
            record = self.records[element]
            if record.suggested_ecutwfc_ry is None:
                missing_cutoff.append(element)
            else:
                ecutwfc_values.append(record.suggested_ecutwfc_ry)
            if record.suggested_ecutrho_ry is None:
                if element not in missing_cutoff:
                    missing_cutoff.append(element)
            else:
                ecutrho_values.append(record.suggested_ecutrho_ry)

        return CutoffSuggestion(
            ecutwfc_ry=max(ecutwfc_values) if ecutwfc_values else None,
            ecutrho_ry=max(ecutrho_values) if ecutrho_values else None,
            missing_elements=missing,
            missing_cutoff_elements=tuple(sorted(missing_cutoff)),
        )

    def suggested_cutoffs_for_structure(
        self,
        structure: AtomisticStructure,
    ) -> CutoffSuggestion:
        return self.suggested_cutoffs(atom.symbol for atom in structure.atoms)


def load_pseudopotential_manifest(
    path: Path,
    *,
    pseudo_dir: Path | None = None,
) -> PseudopotentialManifest:
    manifest_path = Path(path)
    data = yaml.safe_load(manifest_path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"{manifest_path}: pseudopotential manifest must be a mapping")
    schema_version = data.get("schema_version")
    if schema_version != PSEUDOPOTENTIAL_MANIFEST_SCHEMA_VERSION:
        raise ValueError(
            f"{manifest_path}: unsupported schema_version {schema_version!r}; "
            f"expected {PSEUDOPOTENTIAL_MANIFEST_SCHEMA_VERSION}"
        )
    raw_records = data.get("pseudopotentials")
    if not isinstance(raw_records, dict) or not raw_records:
        raise ValueError(f"{manifest_path}: pseudopotentials must be a non-empty mapping")

    warnings: list[str] = []
    records: dict[str, PseudopotentialRecord] = {}
    for element, entry in raw_records.items():
        if not isinstance(element, str) or not element.strip():
            raise ValueError(f"{manifest_path}: element keys must be non-empty strings")
        if not isinstance(entry, dict):
            raise ValueError(f"{manifest_path}: entry for {element!r} must be a mapping")
        record = _record_from_mapping(manifest_path, element.strip(), entry)
        records[record.element] = record
        if pseudo_dir is not None and not (Path(pseudo_dir) / record.filename).exists():
            warnings.append(
                f"{record.element}: pseudopotential file {record.filename!r} "
                f"was not found under {Path(pseudo_dir)}"
            )

    return PseudopotentialManifest(
        records=records,
        source_path=manifest_path,
        warnings=tuple(warnings),
    )


def _record_from_mapping(
    path: Path,
    element: str,
    data: dict[str, Any],
) -> PseudopotentialRecord:
    filename = data.get("file")
    if not isinstance(filename, str) or not filename.strip():
        raise ValueError(f"{path}: pseudopotential {element!r} requires file")
    source = data.get("source")
    if source is None:
        warnings = ("pseudopotential source/provenance is missing",)
    else:
        warnings = ()
    return PseudopotentialRecord(
        element=element,
        filename=filename.strip(),
        family=_optional_str(data.get("family")),
        functional=_optional_str(data.get("functional")),
        suggested_ecutwfc_ry=_optional_positive_float(
            path,
            element,
            "suggested_ecutwfc_ry",
            data.get("suggested_ecutwfc_ry"),
        ),
        suggested_ecutrho_ry=_optional_positive_float(
            path,
            element,
            "suggested_ecutrho_ry",
            data.get("suggested_ecutrho_ry"),
        ),
        source=_optional_str(source),
        warnings=warnings,
    )


def _optional_str(value: Any) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str) or not value.strip():
        raise ValueError("optional pseudopotential text fields must be non-empty")
    return value.strip()


def _optional_positive_float(
    path: Path,
    element: str,
    key: str,
    value: Any,
) -> float | None:
    if value is None:
        return None
    if not isinstance(value, (int, float)) or value <= 0:
        raise ValueError(f"{path}: {element}.{key} must be a positive number")
    return float(value)
