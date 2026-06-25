"""Match calculation results to registry species."""

from __future__ import annotations

from dataclasses import dataclass

from qchem_workbench.core.result import CalculationResult
from qchem_workbench.core.species import Species


@dataclass(frozen=True)
class SpeciesResultMatch:
    species: Species
    result: CalculationResult
    strategy: str


@dataclass(frozen=True)
class AmbiguousSpeciesMatch:
    species_name: str
    candidate_result_identifiers: tuple[str, ...]


@dataclass(frozen=True)
class ResultMatchReport:
    matches: tuple[SpeciesResultMatch, ...]
    ambiguous_matches: tuple[AmbiguousSpeciesMatch, ...]
    unmatched_species: tuple[str, ...]
    unmatched_results: tuple[CalculationResult, ...]


def match_results_to_species(
    species_list: list[Species],
    results: list[CalculationResult],
) -> ResultMatchReport:
    used_result_ids: set[int] = set()
    matches: list[SpeciesResultMatch] = []
    ambiguous: list[AmbiguousSpeciesMatch] = []
    unmatched_species: list[str] = []

    for species in species_list:
        exact_candidates = [
            result for result in results if result.species_name == species.name
        ]
        if len(exact_candidates) == 1:
            result = exact_candidates[0]
            matches.append(SpeciesResultMatch(species, result, "species_name"))
            used_result_ids.add(id(result))
            continue
        if len(exact_candidates) > 1:
            ambiguous.append(_ambiguous(species.name, exact_candidates))
            used_result_ids.update(id(result) for result in exact_candidates)
            continue

        stem_candidates = [
            result
            for result in results
            if id(result) not in used_result_ids
            and result.source_path is not None
            and result.source_path.stem == species.name
        ]
        if len(stem_candidates) == 1:
            result = stem_candidates[0]
            matches.append(SpeciesResultMatch(species, result, "filename_stem"))
            used_result_ids.add(id(result))
            continue
        if len(stem_candidates) > 1:
            ambiguous.append(_ambiguous(species.name, stem_candidates))
            used_result_ids.update(id(result) for result in stem_candidates)
            continue

        unmatched_species.append(species.name)

    unmatched_results = tuple(
        result for result in results if id(result) not in used_result_ids
    )
    return ResultMatchReport(
        matches=tuple(matches),
        ambiguous_matches=tuple(ambiguous),
        unmatched_species=tuple(unmatched_species),
        unmatched_results=unmatched_results,
    )


def _ambiguous(
    species_name: str, candidates: list[CalculationResult]
) -> AmbiguousSpeciesMatch:
    return AmbiguousSpeciesMatch(
        species_name=species_name,
        candidate_result_identifiers=tuple(
            _result_identifier(result) for result in candidates
        ),
    )


def _result_identifier(result: CalculationResult) -> str:
    if result.source_path is not None:
        return str(result.source_path)
    return (
        f"{result.species_name}|{result.backend}|{result.method}|"
        f"{result.basis}|{result.task}"
    )
