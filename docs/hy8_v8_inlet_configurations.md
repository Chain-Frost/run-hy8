# HY-8 v8 inlet-configuration research

This note records the evidence behind `run-hy8`'s inlet-configuration model so
that future maintainers do not need to rediscover the meaning of the HY-8
project cards.

## Scope and evidence

The original findings were recorded on 13 August 2026 against HY-8 executable
version 8.0.1.2. Both elliptical material contexts were audited from the pinned
ShapeDB on 7-8 October 2026, with the retained GUI-created Steel-or-Aluminum
ellipse as independent project-file evidence. The maintained mappings now cover
straight circular, conventional concrete-box, concrete elliptical, and
Steel-or-Aluminum elliptical culverts.

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
HY-8 installation. The audited database is 4,370,624 bytes with SHA-256
`2479e9444feaff529313e18a1b26fc2de4f6b6c541db58477da6bebc602164a7`.
The same hash was obtained from the installed copy, the retained
`ryan-culverts` Git LFS reference, and a fresh extraction from the official
HY-8 8.0.1.2 installer. See `reference_docs/README.md`.

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

The table above records the material-level ShapeDB observations. Elliptical
catalogue rows also carry a per-size `Mannings n` value. Concrete rows are
0.012 throughout, while the Steel-or-Aluminum catalogue contains both 0.034 and
0.033 entries. For supported ellipses, run-hy8 therefore resolves the default
roughness from the exact selected catalogue row rather than applying one
material-wide value to every size.

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

## Elliptical project-card evidence

### Local and catalogue investigation on 7 October 2026

Local Windows testing against `C:\\Program Files\\HY-8 8.00\\HY864.exe`,
file/product version **8.0.1.2**, first exposed two defects in the original
ellipse implementation. A zero-length test fixture caused HY-8 to terminate
with `0xC0000005`; after giving the barrel a non-zero length, the generated
projects completed but reported zero culvert discharge. The detailed local
handoff is retained in `ELLIPTICAL_VALIDATION_FEEDBACK.md`.

The retained `ShapeDB.dat` and the GUI-created
`reference_docs/example-ellipse.hy8` then established the actual file
contract:

- `Shape Names` maps project-file code **3** to `Elliptical`. Code 6 is
  `Arch, Open Bottom`; the earlier code-6 positive-flow probe was therefore
  a false positive and is not ellipse evidence.
- HY-8 material codes are **shape-contextual**. For ellipses,
  `Material Names` is `["Steel or Aluminum", "Concrete", ...]`, so
  `CULVERTMATERIAL 1` means Steel or Aluminum and
  `CULVERTMATERIAL 2` means Concrete. This differs from the circular
  material list.
- HY-8 exposes ellipse sizes as catalogue entries. The pinned database contains
  23 concrete sizes and 40 Steel-or-Aluminum sizes under
  `/Elliptical/<material>/Categories/Category 1/Sub Category 1`.
- Concrete catalogue row 8 is **60 in x 38 in** (1.524 m x 0.9652 m).
  The reversed 38 in x 60 in pair is not a separate concrete catalogue entry,
  so the library does not invent a vertical orientation by swapping dimensions.
- Each catalogue row contains `Span`, `Rise`, `Area`, `Mannings n`,
  `Br`, `Tr`, `Cr`, and `B`. The `Br/Tr/Cr/B` values are required
  HY-8 geometry state, not values that can be replaced with zeros or derived
  from a generic mathematical ellipse.

A controlled HY-8 8.0.1.2 probe demonstrated the hydraulic significance of
that catalogue geometry. For the concrete 60 in x 38 in case:

- writing material code 2 but zero `Br/Tr/Cr/B` produced **zero** barrel flow;
- changing `IRREGSIZE` alone did not fix the result;
- writing `Br=Tr=51.6 in`, `Cr=16.43 in`, and `B=19 in` from the
  ShapeDB catalogue produced positive flow up to the requested 2.0 m3/s;
- changing the legacy inlet compatibility flags did not affect that positive
  flow result.

The fifth `BARRELGEOMETRY` field is not treated as a persisted catalogue
parameter. HY-8 rewrites it during `-OpenRunSave`. The writer supplies the
source catalogue `Area` as a version-pinned input value, while the first four
fields are sourced directly from `Br/Tr/Cr/B` and are the demonstrated
hydraulically significant values.

Accordingly, current concrete-ellipse execution is fail-closed:

- `CULVERTSHAPE 3`;
- contextual concrete `CULVERTMATERIAL 2`;
- dimensions must match an HY-8 8.0.1.2 concrete catalogue row within the
  documented project-file round-trip tolerance;
- no nearest-size substitution and no synthetic rotated size;
- `BARRELGEOMETRY` is populated from that same catalogue row.

The hosted probes are implementation evidence, not the final acceptance run.
After the catalogue-backed writer and normal CI are clean, another local
Windows agent with installed HY-8 8.0.1.2 must rerun the focused executable
suite and record the result before merge/engineering use:

```powershell
python -m pytest -m requires_hy8 -q tests/test_elliptical.py
```

The existing `.rst` and `.rsql` parsers expose crossing headwater,
per-culvert discharge, inlet/outlet control depth, full/free barrel length,
outlet velocity, flow type, profile flow, and HW/D for the external
`ryan-culverts` comparison tooling.

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

### Concrete elliptical

| Index | HY-8 configuration |
| ---: | --- |
| 0 | Square Edge with Headwall |
| 1 | Grooved Edge with Headwall |
| 2 | Grooved Edge Projecting |

These names and their zero-based order come directly from
`Elliptical/Concrete/Entrance Types/Straight/Inlet Names` in the pinned
HY-8 8.0.1.2 `ShapeDB.dat`.

### Steel or Aluminum elliptical

| Index | HY-8 configuration |
| ---: | --- |
| 0 | Headwall |
| 1 | Mitered |
| 2 | Beveled |
| 3 | Thin Edge Projecting |

These names and their zero-based order come directly from
`Elliptical/Steel or Aluminum/Entrance Types/Straight/Inlet Names` in the
pinned HY-8 8.0.1.2 ShapeDB.

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
- Ellipses use `CulvertShape.ELLIPTICAL` (file code 3). Steel or Aluminum is
  contextual material code 1; Concrete is contextual material code 2.
- Concrete and Steel-or-Aluminum ellipses use separate semantic inlet enums and
  separate version-pinned HY-8 catalogues.
- Ellipse dimensions must match the catalogue for the selected material.
  Arbitrary or merely reversed `span`/`rise` pairs are rejected rather than
  synthesized or snapped to a nearby size.
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
