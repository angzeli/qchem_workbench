# QE And Surface Workflows

qchem-workbench supports Quantum ESPRESSO and surface workflows as input/output
and bookkeeping utilities. It does not bundle, install, or execute QE, and it
does not choose pseudopotentials, cutoffs, k-points, adsorption sites, or
production settings.

## QE Input Rendering

`qchemwb render-qe` writes `pw.x` input files from an explicit structure,
pseudopotential mapping, atomic masses, cutoffs, k-points, and cell:

```bash
qchemwb render-qe structure.xyz --pseudo-map pseudos.yaml --ecutwfc 40 --cell 12 12 12 --gamma-only --out qe_inputs/demo.in
```

Supported calculation types are `scf`, `relax`, and `vc-relax`. Relax inputs
include `&IONS`; `vc-relax` inputs also include `&CELL`. Fixed atoms can be
stored on `AtomisticStructure.fixed_atom_indices` and render as QE atomic
position constraint flags. Atomic positions can be rendered in `angstrom` or
`crystal` coordinates.

Generated inputs are starting points for human inspection. The renderer does
not add hidden convergence thresholds or production defaults.

## QE Output Parsing

`qchemwb parse-qe` parses QE-like `pw.x` output text into `CalculationResult`
JSON:

```bash
qchemwb parse-qe outputs/ --out results/qe_results.json --csv results/qe_results.csv
```

The parser extracts available total energies, SCF status, cell blocks, relax
trajectory summaries, atomic positions, forces, stress, pressure, and
magnetisation metadata. Missing sections remain missing. Malformed sections
produce warnings rather than fabricated values.

## Pseudopotential Manifests

Pseudopotential manifests record user-provided pseudopotential filenames and
provenance metadata:

```yaml
schema_version: 1
pseudopotentials:
  O:
    file: O.pbe.UPF
    family: User supplied
    functional: PBE
    suggested_ecutwfc_ry: 60
    suggested_ecutrho_ry: 480
    source: User provided
atomic_masses:
  O: 15.999
```

The manifest is metadata, not a correctness guarantee. qchem-workbench does not
download pseudopotentials or recommend a family by default.

## Convergence Studies

Convergence-study YAML files organise cutoff or k-point sweeps:

```bash
qchemwb convergence-table examples/qe_parsing/convergence.yaml examples/qe_parsing/convergence_results.json --out /tmp/convergence.csv
```

The table computes successive total-energy differences and marks whether each
difference is within the user-provided tolerance. It does not choose final
production settings automatically.

## Surface Sites And Placement

Surface bookkeeping models store user-defined slab metadata, adsorption sites,
and coverage values. Site labels such as `top`, `bridge`, or `custom` are user
labels only; the package does not auto-detect active sites or validate chemical
site identity.

`qchemwb place-adsorbate` can use an explicit site definition when ASE is
installed:

```bash
qchemwb place-adsorbate examples/surface_adsorption/placement.yaml --out /tmp/slab_ads.xyz
```

The generated structure is an unrelaxed starting guess requiring human
inspection. qchem-workbench does not optimise adsorbate geometries.

## Structure Pathways

Structure-pathway YAML files organise initial, final, and intermediate images
for external NEB-like workflows. qchem-workbench validates and exports the
structure set only; it does not run NEB or compute barriers.
