# Active-learning report: synthetic adsorption active-learning example

## Campaign overview

| Item | Value |
| --- | --- |
| Campaign | synthetic adsorption active-learning example |
| Candidates in registry | 2 |
| Candidates in state file | 2 |
| Rows in dataset | 2 |
| Descriptor sources | ads:csv |

## Candidate counts by state

| State | Count |
| --- | --- |
| completed | 1 |
| excluded | 0 |
| failed | 0 |
| pending | 1 |
| proposed | 0 |
| unobserved | 0 |

## Objective definitions

| ID | Source column | Direction | Weight | Units from column name |
| --- | --- | --- | --- | --- |
| minimise_adsorption_energy | ads_adsorption_energy_eV | minimise | 1 | eV |

| Constraint ID | Source column | Operator | Value |
| --- | --- | --- | --- |
| require_no_quality_errors | ads_quality_error_count | equals | 0 |

## Observed objective summary

| Column | Units | Observed rows | Minimum | Maximum | Mean |
| --- | --- | --- | --- | --- | --- |
| objective_minimise_adsorption_energy_value | not specified | 1 | 0.45 | 0.45 | 0.45 |
| al_score | not specified | 1 | 0.45 | 0.45 | 0.45 |

## Current best candidates

| Rank | Candidate ID | Score | Status | Reasons |
| --- | --- | --- | --- | --- |
| 1 | cand_co_top | 0.45 | ranked | N/A |

## Proposed next candidates

| Proposal rank | Candidate ID | Acquisition value | Proposed by | Notes |
| --- | --- | --- | --- | --- |
| 1 | cand_h_top | 0.72 | synthetic_bo_forge_fixture | Synthetic proposal for demonstrating import only |

## Failed and pending calculations

| Candidate ID | State | Result | Reason |
| --- | --- | --- | --- |
| cand_h_top | pending | N/A | Synthetic example keeps this candidate pending for loop-report coverage. |

## Quality warnings

| Candidate ID | Source | Quality errors | Quality warnings | Flags | Missing data |
| --- | --- | --- | --- | --- | --- |
| cand_h_top | ads | 1 | 1 | missing_adsorption_energy | N/A |

## BO Forge export/import provenance

| Item | Value |
| --- | --- |
| Dataset contains BO-style score columns | yes |
| Proposal import included | yes |
| Stable interchange path | file-based CSV/JSON; no BO Forge Python dependency is required |
