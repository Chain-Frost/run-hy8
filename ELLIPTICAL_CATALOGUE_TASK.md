# Current task: HY-8 elliptical catalogue contract

## User direction

> The main work I am on now is **not** trying random project cards. It is to
> extract HY-8's ellipse catalogue from `ShapeDB.dat`, establish how a selected
> catalogue size maps to the GUI `BARRELDATA`/`BARRELGEOMETRY` state, and then
> change `run-hy8` so arbitrary unsupported span/rise combinations fail closed.

This is the current implementation objective. Read
`ELLIPTICAL_VALIDATION_FEEDBACK.md` for earlier local validation results, but
follow this direction when choosing the next investigation and implementation.

## Required work

1. Extract the elliptical size catalogue from the version-pinned
   `reference_docs/ShapeDB.dat`. Preserve the source dataset paths, native
   values, units, ordering and any identifiers or orientation distinctions
   needed to interpret catalogue entries. Record extraction provenance and
   database identity so the result can be independently verified.
2. Establish how selecting a catalogue entry in the HY-8 GUI sets
   `BARRELDATA` and `BARRELGEOMETRY`. Use GUI-created/saved projects for known
   catalogue selections and compare their state with the extracted entries.
   Resolve units, orientation and any additional geometry state required to
   represent that selection before defining the library contract.
3. Change `run-hy8` to accept supported catalogue selections and reject
   unsupported arbitrary span/rise combinations before execution. Define any
   matching tolerance from demonstrated unit conversion or serialization
   precision; do not silently substitute a nearby catalogue size.
4. Add meaningful tests for supported selections, unsupported dimensions,
   orientation behavior and serialization/reading of the established GUI
   geometry state. Validate supported examples with the installed HY-8
   executable, then rerun lint, formatting, type checking and the source suite.

## Investigation boundary

Do not pursue random project-card mutations as the main investigation.
Catalogue extraction and the demonstrated mapping from catalogue selection to
GUI project state are the evidence needed for the implementation.

The earlier ellipse test dimensions are test inputs, not proof that those sizes
belong to the catalogue. Reassess them against the extracted catalogue and
update fixtures to confirmed supported selections where necessary.

## Expected handoff evidence

- A reviewable catalogue extraction artifact and its provenance.
- A documented mapping from selected catalogue entries to GUI
  `BARRELDATA`/`BARRELGEOMETRY` state, with representative saved projects.
- An explicit supported-size contract and actionable rejection behavior for
  unsupported dimensions.
- Local HY-8 results and exact automated-check outcomes for the final change.

The schema, artifact format and implementation design are left to the agent;
the catalogue-based contract and fail-closed behavior are required.


## Implementation status

The catalogue investigation has now established and implemented the following:

- ShapeDB `Shape Names` confirms `CULVERTSHAPE 3 = Elliptical`.
- Ellipse material codes are contextual: 1 = Steel or Aluminum, 2 = Concrete.
- The extracted database contains 23 concrete and 40 Steel-or-Aluminum ellipse
  catalogue rows.
- Concrete 60 in x 38 in and 68 in x 43 in are confirmed supported test sizes.
  The synthetic reversed 38 in x 60 in case has been removed.
- The runtime concrete catalogue is version-pinned in
  `src/run_hy8/ellipse_catalogue.py`; unsupported dimensions fail closed with
  no nearest-size substitution.
- The writer now emits ShapeDB `Br/Tr/Cr/B` values in
  `BARRELGEOMETRY`. A controlled HY-8 8.0.1.2 probe demonstrated that these
  fields are required for positive ellipse barrel flow.
- The writer/reader now translate material codes by shape/material context
  rather than serializing `CulvertMaterial.value` directly.
- Hosted HY-8 executable regression tests passed for two concrete catalogue
  sizes and all three supported concrete inlet configurations, including the
  inverse helpers. Final local Windows/HY-8 acceptance is still required before
  the PR leaves draft status.
