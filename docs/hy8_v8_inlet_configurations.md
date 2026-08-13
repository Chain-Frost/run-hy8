# HY-8 v8 inlet-configuration research

This note records the evidence behind `run-hy8`'s inlet-configuration model so
that future maintainers do not need to rediscover the meaning of the HY-8
project cards.

## Scope and evidence

The findings were recorded on 13 August 2026 against HY-8 executable version
8.0.1.2. They apply to the straight circular and conventional concrete-box
shapes currently supported by `run-hy8`.

Three sources were used:

1. The installed HY-8 User Manual, particularly section 4.4, *Inlet
   Configurations*, and section 11.3, *Polynomial Coefficients - Box*.
2. The installed `ShapeDB.dat` HDF5 database. Its `Inlet Names` datasets provide
   the ordered, shape/material-specific configuration lists used by HY-8 v8.
3. Executed `.hy8` project probes and `.rst`/`.rsql` comparisons using HY-8
   8.0.1.2. The lasting regression coverage is in
   `tests/test_inlet_configurations.py` and `tests/test_reader.py`.

`ShapeDB.dat` is evidence used to maintain the checked-in registry. It is not a
runtime dependency: callers must be able to create projects without a local
HY-8 installation.

The same database also supplies the default Manning's n values. All observed
HY-8 8.0.1.2 values are preserved in `hydraulic_defaults.py`, including shapes
that `run-hy8` does not yet construct:

| Shape | Material | Top n | Bottom n |
| --- | --- | ---: | ---: |
| Arch, Open Bottom | Corrugated Aluminum | 0.035 | 0.035 |
| Arch, Open Bottom | Corrugated Steel | 0.035 | 0.035 |
| Circular | Concrete | 0.012 | 0.012 |
| Circular | Corrugated Aluminum | 0.031 | 0.031 |
| Circular | Corrugated PE | 0.024 | 0.024 |
| Circular | Corrugated Steel | 0.024 | 0.024 |
| Circular | PVC | 0.011 | 0.011 |
| Circular | Smooth HDPE | 0.012 | 0.012 |
| Concrete Box | Concrete | 0.012 | 0.012 |
| Concrete Open-Bottom Arch | Concrete | 0.012 | 0.035 |
| Elliptical | Concrete | 0.012 | 0.012 |
| Elliptical | Steel or Aluminum | 0.034 | 0.034 |
| High-Profile Arch | Corrugated Aluminum | 0.035 | 0.035 |
| High-Profile Arch | Corrugated Steel | 0.035 | 0.035 |
| Low-Profile Arch | Corrugated Aluminum | 0.035 | 0.035 |
| Low-Profile Arch | Corrugated Steel | 0.035 | 0.035 |
| Metal Box | Corrugated Aluminum | 0.035 | 0.035 |
| Metal Box | Corrugated Steel | 0.035 | 0.035 |
| Pipe Arch | Aluminum Structural Plate | 0.035 | 0.035 |
| Pipe Arch | Concrete | 0.012 | 0.012 |
| Pipe Arch | Steel Structural Plate | 0.035 | 0.035 |
| Pipe Arch | Steel or Aluminum | 0.025 | 0.025 |
| South Dakota Concrete Box Culvert | Concrete | 0.012 | 0.012 |
| User Defined | Concrete | 0.012 | 0.012 |
| User Defined | Corrugated Metal Riveted or Welded | 0.035 | 0.035 |

When ShapeDB contains only `Mannings`, the table repeats that value for the two
numbers required by `BARRELDATA`. The concrete open-bottom arch is an important
exception where ShapeDB explicitly supplies different top and bottom defaults.

Defaults are selected by shape and material, even where values happen to match.
A new supported context must be enabled explicitly; there is deliberately no
catch-all fallback. Users may always provide `manning_n_top` and
`manning_n_bottom` manually. Providing both bypasses the defaults; providing
one preserves that override and defaults only the missing side.

## What the two inlet-edge cards mean in v8

The card names are misleading:

- `INLETEDGETYPE71` is the authoritative contextual list index in HY-8 v8. Its
  meaning depends on the culvert shape, material, and inlet type.
- `INLETEDGETYPE` is an older compatibility card. HY-8 v8 still expects the
  card to exist, but it is not the source used by `run-hy8` to describe the
  current hydraulic selection.

The following experiments established that behavior:

- Removing `INLETEDGETYPE71` allowed the executable to run, but HY-8
  reinterpreted several inlet selections from the older card and wrote changed
  contextual indices when saving the project.
- Removing `INLETEDGETYPE` caused `-OpenRunSave` not to produce the normal
  result files, despite its console text reporting completion. It therefore
  remains part of the v8 file grammar.
- Keeping the correct `INLETEDGETYPE71` values while changing every
  `INLETEDGETYPE` value to zero produced the same parsed `.rst` results as the
  HY-8-saved reference project. HY-8 subsequently normalised the older values
  when saving.

For that reason the writer emits a neutral zero for `INLETEDGETYPE` and derives
`INLETEDGETYPE71` from the semantic configuration registry. The reader ignores
the older card and requires the contextual one.

## Supported contextual lists

The index is zero-based within each list.

### Circular concrete

| Index | HY-8 configuration |
| ---: | --- |
| 0 | Square Edge with Headwall |
| 1 | Grooved End Projecting |
| 2 | Grooved End in Headwall |
| 3 | Beveled Edge (1:1) |
| 4 | Beveled Edge (1.5:1) |
| 5 | Mitered to Conform to Slope |

### Circular corrugated steel

| Index | HY-8 configuration |
| ---: | --- |
| 0 | Thin Edge Projecting |
| 1 | Mitered to Conform to Slope |
| 2 | Square Edge with Headwall |
| 3 | Beveled Edge (1:1) |
| 4 | Beveled Edge (1.5:1) |

### Circular smooth HDPE

| Index | HY-8 configuration |
| ---: | --- |
| 0 | Square Edge with Headwall |
| 1 | Beveled Edge (1:1) |
| 2 | Beveled Edge (1.5:1) |
| 3 | Thin Edge Projecting |
| 4 | Mitered to Conform to Slope |

### Conventional concrete box

| Index | HY-8 configuration |
| ---: | --- |
| 0 | Square Edge (90°) Headwall |
| 1 | 1.5:1 Bevel (90°) Headwall |
| 2 | 1:1 Bevel Headwall |
| 3 | Square Edge (30–75° flare) Wingwall |
| 4 | Square Edge (90° or 15° flare) Wingwall |
| 5 | Square Edge (0° flare) Wingwall |
| 6 | 1.5:1 Bevel (18–34° flare) Wingwall |
| 7 | 1:1 Bevel (45° flare) Wingwall |

These are discrete HY-8 configurations, not arbitrary numeric flare angles.
An external adapter may map another application's categories to them, but that
mapping does not belong in `run-hy8`.

## Implementation consequences

- Public identifiers are separated by shape and material. A single integer
  enum would incorrectly assign one meaning to a context-dependent index.
- The public `StrEnum` values are semantic slugs. Contextual file indices live
  only in `HY8_V8_INLET_SPECS`.
- `CulvertBarrel` validation rejects a configuration from the wrong
  shape/material context.
- Old `InletEdgeType` and `InletEdgeType71` inputs are migration-only and emit
  `LegacyInletConfigurationWarning`.
- Pre-v8 project headers are unsupported and rejected; there is no attempt to
  reconstruct older project semantics.

## Extending support

When adding another HY-8 v8 shape or material:

1. Inspect its ordered `Inlet Names` dataset in the same HY-8 8 shape database.
2. Confirm the names against the bundled v8 manual.
3. Add a new shape/material-specific semantic enum and registry entries.
4. Create or retain an HY-8-saved project fixture for every supported index.
5. Test reader resolution and exact card serialization.
6. Execute both the HY-8-saved fixture and its `run-hy8` round trip, then compare
   parsed `.rst` and `.rsql` results.
7. Record the executable version and any limits of the new evidence here.

Do not infer an unsupported mapping from similarly worded inlet names, and do
not silently fall back to another shape, material, or inlet configuration.
