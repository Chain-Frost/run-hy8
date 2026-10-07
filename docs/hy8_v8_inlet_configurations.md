# HY-8 v8 inlet-configuration research

This note records the evidence behind `run-hy8`'s inlet-configuration model so
that future maintainers do not need to rediscover the meaning of the HY-8
project cards.

## Scope and evidence

The original findings were recorded on 13 August 2026 against HY-8 executable
version 8.0.1.2. The concrete elliptical context was audited on 7 October 2026
against the same executable/database pair. The maintained mappings now cover
straight circular, conventional concrete-box, and concrete elliptical culverts.

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

## Elliptical project-card evidence

### Local validation on 7 October 2026

Local execution against `C:\Program Files\HY-8 8.00\HY864.exe`, file and
product version **8.0.1.2**, did not establish working elliptical hydraulics.
The installed and retained `ShapeDB.dat` files both matched the SHA-256 above.

The initial four executable tests crashed with exit status `3221225477`
(`0xC0000005`). Their fixture inherited identical inlet/outlet stations and
therefore a zero-length barrel. Giving the fixture a 20 m length prevented
the crash. The revised fixture uses tailwater 0.2 m above the outlet invert
and a 0.2/1.0/2.0 m3/s min/design/max flow range.

Both orientations and all three concrete inlet configurations preserved their
project cards and produced finite reports, but reported **zero culvert
discharge**. Finite output alone is therefore insufficient acceptance evidence.
The round-trip tests now also require positive culvert discharge. The forward
helper at 1.0 m3/s raises `RoadwayOvertoppingError`, with HY-8 reporting all
discharge over the roadway. Separate user-defined-flow and narrower
min/design/max probes reproduced zero culvert discharge.

Elliptical hydraulic execution and inverse helpers remain unvalidated. The
cause of the zero-discharge reports needs investigation before engineering
use; successful serialization and executable exit status do not resolve it.

A Windows execution probe used the official HY-8 8.0.1.2 installer payload,
including its byte-identical `ShapeDB.dat`, and exercised `-OpenRunSave`
against deliberately modified project files.

The observed file contract is:

- `CULVERTSHAPE 3` is the HY-8 v8 elliptical shape code.
- `CULVERTMATERIAL 1` is concrete.
- `BARRELDATA` preserves span and rise independently.
- A 5.0 ft × 3.166667 ft horizontal ellipse and the reversed
  3.166667 ft × 5.0 ft vertical ellipse both completed with exit code 0,
  generated `.rst` and `.rsql`, and retained `CULVERTSHAPE 3`.
- HY-8 therefore does not use separate horizontal/vertical shape codes; the
  orientation is represented by the span/rise relationship.

These probes establish the project-file/orchestration contract only. They do
not make `run-hy8` an authority for elliptical hydraulic equations.

The hosted Windows probe is retained as implementation evidence, but it is not
the final local acceptance run. Before merge/engineering use, another agent with
access to an installed HY-8 8.0.1.2 environment should rerun the
`@pytest.mark.requires_hy8` ellipse tests locally, including both orientations,
inverse helpers, writer/reader round trips, and `.rst`/`.rsql` parsing. Record
the executable path/version and the local result in the PR handoff. Hosted CI
does not replace that local HY-8 executable validation.

From a Python 3.14 environment with HY-8 8.0.1.2 installed and discoverable by
`Hy8Executable`, the focused handoff command is:

```powershell
python -m pytest -m requires_hy8 -q tests/test_elliptical.py
```

The generated ellipse reports were also parsed through the existing `.rst` and
`.rsql` readers. Crossing headwater, per-culvert discharge, inlet/outlet
control depth, full/free barrel length, outlet velocity, flow type, profile
flow, and HW/D were all available without a parser change. This is the result
surface used by the external `ryan-culverts` comparison tooling.

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
- Concrete ellipses use `CulvertShape.ELLIPTICAL` (file code 3) with
  `EllipticalConcreteInlet`; unsupported ellipse material/inlet contexts
  remain fail-closed.
- Horizontal and vertical elliptical orientations use the same shape code and
  retain `span` and `rise` independently through JSON and `.hy8` round trips.
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
