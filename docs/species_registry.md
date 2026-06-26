# Species Registry

Species registries are YAML files with `schema_version: 1` and a `species`
list. Geometry paths are resolved relative to the registry file.

```yaml
schema_version: 1
species:
  - name: water
    formula: H2O
    charge: 0
    multiplicity: 1
    geometry_path: xyz/water.xyz
    tags: [demo]
    notes: Synthetic example molecule.
```

Single `geometry_path` entries and conformer lists are both supported. Missing
geometry files and malformed XYZ files are errors. Missing parsed scientific
values should remain missing rather than being replaced with placeholders.
