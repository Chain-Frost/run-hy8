# Roadway overtopping validation support

Date: 2026-10-05

Issue: #2

Branch: `feature/issue-2-roadway-overtopping-validation`

Baseline: `main` at `9d578a3a7045f0aa84698964f0fb64e7347fe309`

## Implementation status

Adapter implementation, executable validation and the irregular-profile flow
padding workaround are complete for PR #3. The user supplied a GUI-authored
six-point fixture; padded executable runs preserve its geometry and match the
GUI-displayed hydraulic results. A separate multi-crossing GUI save remains an
optional follow-up comparison. Exact user-defined submergence-law reconstruction
and independent solver acceptance remain outside the demonstrated evidence.

The final wheel has been rebuilt and verified against all 25 package source/type
files, with isolated installation/import checks. Final committed source/wheel
identity is recorded in `docs/validation_data/roadway_padding_build_provenance.json`.
The original 24-case provenance below is retained as historical evidence.

See [the implemented contract and exact commands](../roadway_overtopping.md),
[24 retained adapter cases](../validation_data/hy8_8_0_1_2_roadway_adapter.csv)
and [source/wheel/executable provenance](../validation_data/roadway_adapter_provenance.json).

Implemented: explicit SI coefficient with English `WEIRCOEFF` read/write,
typed profile shapes, finite/ordered geometry checks, supported submerged input,
result-time `ERROR/WARN/ALLOW` across crossing/project helpers and intermediate
inverse batches, matching CLI option, raw profile evidence and SI result parsing.
The installed manual's 3-15 irregular count is stale: FHWA's 7.70 release history
raises it to 5000, confirmed by a successful 5000-point saved-file probe.

HY-8 8.0.1.2 was run with Python 3.14.6 on Windows. All 24 matrix cases verified
saved inputs and exactly equivalent parsed reader/writer reports. These are
adapter tests, not paired `ryan-culverts` hydraulic validation. Paved/gravel
ignore the stored explicit coefficient in the observed cases; user-defined
results respond to coefficient and tailwater. The exact user-defined
submergence law remains unresolved, and no independent paved/gravel correction
selector is claimed.

A three-point irregular overtopping case with two user-flow entries crashes at
executable offset `0x141ed5` (access violation `0xc0000005`); three entries succeed.
The writer pads irregular user-flow sets to at least three while preserving
requested values. Other exploratory 5/16-point report probes also crashed;
the retained three-point cases and a 5000-point probe succeeded. This is
version-specific executable behavior, not evidence that every profile in the
accepted station-count range executes reliably. No hydraulic equations were added.

No user project was available for the required GUI-authored irregular/submerged
round-trip. The user will create one later. The optional fixture test is ready
and explicitly skips until `HY8_ROADWAY_GUI_FIXTURE` is set. Interactive GUI
investigation was stopped at the user's request; no GUI elements were implemented.

Repository checks executed with `PYTHONPATH=src`:

- `python -m pytest tests -q`: **120 passed**, one GUI-fixture skip, four maintained
  comparison-harness tests deselected by the repository's default marker policy.
  Runtime: 16.67 seconds. HY-8 executable tests ran, including all three surfaces,
  free/submerged cases, single-request irregular padding and English result matching.
- `python -m ruff check .`: passed.
- `python -m ruff format --check .`: passed.
- `python -m pyright src/run_hy8`: passed, zero errors/warnings.
- `python -m mkdocs build --strict`: passed after the provenance JSON was
  generated (an earlier run failed because that linked artifact did not yet exist).
- `git diff --check`: passed.
- `python -m build --wheel --outdir validation_artifacts/wheels`: passed.
- Isolated target install and `python -I scripts/verify_roadway_wheel.py` with the
  exact arguments in the handoff: passed; all 25 source/typing files matched,
  installed version `2026.10.5.1`, isolated import and coefficient smoke passed.
- `python scripts/validate_roadway.py --matrix --output validation_artifacts/roadway-matrix --csv docs/validation_data/hy8_8_0_1_2_roadway_adapter.csv`:
  all 24 cases passed saved-input and parsed-report round-trip checks.

HY-8's observed `.rst` precision is two decimal places; `.rsql` has roughly six
significant figures and no roadway discharge in the inspected outputs. The
reporting-policy threshold is 0.005 m3/s. No independent-solver acceptance
tolerances, calibration or external roadway regression baselines were selected.

## Purpose

Extend `run-hy8` so a desktop validation agent can deliberately create, execute, read and
audit HY-8 roadway-overtopping cases required by the downstream `ryan-culverts` external
validation work.

The original `run-hy8` use case was primarily culvert checking. Roadway overtopping was
often an unexpected design condition. This work must therefore support intentional roadway
overtopping without silently removing that safety behaviour for existing culvert-only users.

Related downstream branch:

`Chain-Frost/ryan-culverts:validation/roadway-overtopping-external`

## Important design separation

There are two different concerns and they must not remain conflated:

1. **Is the HY-8 input hydraulically/model-format valid?**
2. **Does a caller intend to accept roadway overtopping in the result?**

A submerged roadway can be a valid HY-8 input. It should not be rejected merely because
tailwater reaches or exceeds the lowest road crest.

Unexpected roadway discharge is instead a result-policy concern and should be evaluated
after HY-8 results are parsed.

## Required work

### 1. Add explicit user-defined roadway discharge coefficient support

`RoadwaySurface.USER_DEFINED` exists, but the supported model does not currently expose
the associated roadway coefficient and the reader/writer does not preserve `WEIRCOEFF`.

Add a typed internal SI field for the user-defined roadway discharge coefficient.

Before freezing the implementation, verify using HY-8 8.0.1.2 and the installed/manual
evidence:

- the exact meaning of `WEIRCOEFF`;
- the accepted executable range;
- the saved-file unit convention;
- the conversion required between the package's SI model and the HY-8 project file;
- whether the conversion is independent of the HY-8 display-unit setting.

The coefficient is dimensioned for a relationship of the form `Q = C L H^(3/2)`; do not
treat it as dimensionless. Verify the conversion experimentally rather than relying only on
dimensional inference.

Requirements:

- require a coefficient where HY-8 requires one for user-defined roadway-coefficient mode;
- reject missing, non-finite and executable/manual-invalid values;
- retain it in `RoadwayProfile.to_dict()` / `from_dict()`;
- preserve it through JSON/configuration;
- parse `WEIRCOEFF` from existing HY-8 files;
- write `WEIRCOEFF` when generating HY-8 files;
- round-trip without changing its physical SI meaning;
- never silently substitute a paved/gravel coefficient.

### 2. Make roadway profile semantics explicit

Investigate and document the HY-8 8.0.1.2 roadway profile contract before replacing the
current raw `shape: int` behaviour with stronger validation.

Verify:

- constant versus irregular roadway shape flags;
- required station counts for each;
- the manual's stated irregular-profile range, believed to be 3â€“15 points;
- station ordering requirements;
- duplicate-station behaviour;
- allowed/required horizontal extent;
- whether a two-point linear slope is accepted as an irregular profile.

If HY-8 requires three points for an irregular profile, represent a linear slope with an
explicitly collinear middle point rather than inventing unsupported two-point semantics.

Keep the Python model aligned with what HY-8 actually accepts.

### 3. Permit intentional submerged-roadway inputs

Remove the blanket validation rule that rejects a crossing solely because constant tailwater
reaches or exceeds the roadway crest.

That condition can be part of a valid intentional roadway-overtopping case.

Retain checks for genuinely invalid geometry or unsupported input combinations.

For executable validation cases, inspect the actual project saved/run by HY-8 and verify
input parity for:

- tailwater;
- roadway station/elevation profile;
- roadway extent/width;
- roadway surface mode;
- explicit user-defined coefficient where applicable.

Do not assume that the in-memory Python object proves what HY-8 used.

### 4. Determine user-defined coefficient/submergence semantics

This is a required research item, not an assumption.

Using HY-8 8.0.1.2, establish whether:

- a user-defined roadway coefficient can coexist with a separately selected paved/gravel
  submergence correction;
- selecting `USER_DEFINED` surface changes or disables HY-8's paved/gravel submergence
  treatment;
- another saved-file field controls the two concepts independently;
- the GUI exposes a combination that `run-hy8` does not yet represent.

Retain the evidence used to reach the conclusion.

If HY-8 cannot independently combine coefficient control and paved/gravel submergence
treatment, expose that limitation clearly. Do not design the public API as though the
combination exists.

This matters to the downstream comparison: coefficient-controlled free-overflow cases and
paved/gravel submerged cases may need to be classified as different validation families.

### 5. Add an explicit unexpected-overtopping policy

The old package behaviour protected culvert-only users by rejecting one particular input
condition. That does not reliably detect actual roadway overtopping and blocks legitimate
submerged cases.

Replace that protection with a result-time policy based on parsed HY-8 roadway discharge.

Preferred public concept:

`RoadwayOvertoppingPolicy`

with three modes:

- `ERROR` â€” unexpected non-trivial roadway discharge is treated as a failure;
- `WARN` â€” return the valid HY-8 result and emit a clear warning;
- `ALLOW` â€” return the result without an overtopping warning.

Default high-level culvert-checking workflows to `ERROR` unless inspection of the current
public API demonstrates that another default is required for compatibility.

Intentional validation scripts must be able to select `WARN` or `ALLOW`.

The CLI should expose one clear policy option rather than multiple overlapping booleans.
A form such as the following is preferable:

```text
--roadway-overtopping error|warn|allow
```

A backward-compatible shorthand such as `--allow-roadway-overtopping` can be considered
only if it materially improves usability.

Policy requirements:

- trigger from **actual parsed roadway discharge**;
- do not trigger merely because HW is above crest;
- do not trigger merely because TW is above crest;
- use a documented numerical/reporting threshold so HY-8 display noise is not interpreted
  as meaningful roadway flow;
- include roadway discharge and crossing identity in the warning/error;
- preserve the underlying HY-8 result for diagnostic workflows where appropriate.

### 6. Desktop HY-8 evidence

Complete the behaviour research and executable tests on Windows with the actual HY-8
installation.

Record:

- exact `run-hy8` commit;
- Python version;
- HY-8 file/product version;
- HY-8 executable SHA-256 if practical;
- any relevant manual/file hashes;
- GUI steps used to create reference fixtures;
- whether project display units alter stored project-file values.

Prefer HY-8 8.0.1.2 where available.

Create at least one GUI-authored reference project containing an irregular roadway and
submerged-roadway condition. Use it to prove supported reader â†’ writer â†’ executable
round-trip equivalence.

### 7. Focused test coverage

Add unit/config/round-trip tests for:

- `WEIRCOEFF` parsing;
- `WEIRCOEFF` writing;
- SI-to-HY-8 and HY-8-to-SI coefficient conversion;
- `RoadwayProfile` dictionary round-trip;
- JSON/config round-trip;
- missing user-defined coefficient;
- non-finite coefficient;
- values outside the verified HY-8 range;
- constant roadway profile;
- irregular profile point-count rules;
- station ordering and invalid duplicates as supported by HY-8;
- submerged constant-tailwater project serialization;
- paved surface;
- gravel surface;
- user-defined surface/coefficient;
- `ERROR`, `WARN` and `ALLOW` overtopping policies;
- zero roadway flow not falsely triggering the policy;
- non-zero roadway flow triggering the selected policy.

Add executable tests, marked consistently with the existing `requires_hy8` marker, for
the smallest cases needed to prove actual HY-8 input/output parity.

### 8. Build identity for downstream validation

The downstream `ryan-culverts` validation must be able to state exactly which
`run-hy8` implementation generated the comparison evidence.

After implementation stabilises:

- commit all source changes first;
- build from that exact commit;
- if a wheel is used, record its SHA-256;
- install it into the desktop validation environment;
- verify the installed distribution/version and, where practical, source revision;
- run an isolated import/smoke test with the source checkout removed from `PYTHONPATH`.

Issue #1 covers broader transactional packaging improvements. Do not expand this task into
issue #1 unless it is genuinely required to establish the validation build identity.

## Validation use cases to unlock

This work exists to enable the following downstream HY-8 comparisons:

### Free overflow

- constant-level crest;
- linear/sloping crest;
- irregular/sag roadway;
- partially active irregular crest;
- roadway activation over a discharge series.

### Submerged roadway

- paved;
- gravel;
- multiple supported downstream/upstream head ratios;
- cases near the downstream `ryan-culverts` applicability boundary;
- equal-stage and near-equal-stage executable behaviour.

### Combined crossing

- culvert only below road activation;
- first road activation;
- combined culvert + roadway flow;
- submerged roadway plus culvert.

`run-hy8` must expose the HY-8 evidence cleanly; it must not contain the
`ryan-culverts` comparison logic itself.

## Scope limits

Do not:

- add independent roadway hydraulic equations to `run-hy8`;
- calibrate values to make HY-8 match another solver;
- add `ryan-culverts` as a runtime dependency;
- add floodway pavement/batter/scour design;
- add debris/blockage;
- assume user-defined and paved/gravel submergence behaviour can coexist before verifying it;
- silently weaken the unexpected-overtopping protection used by culvert-only workflows;
- solve unrelated packaging issue #1 unless required for build identification.

## Repository checks

Follow `docs/agents.md`.

At minimum run and record:

```powershell
python -m pytest tests
python -m ruff check .
python -m ruff format --check .
python -m pyright src/run_hy8
python -m mkdocs build --strict
git diff --check
```

Also run the focused `requires_hy8` executable tests in the desktop environment.

If a validation wheel is produced, run the isolated installed-wheel smoke check and record
the exact wheel hash.

Do not claim checks were run unless they were actually executed.

### User-provided GUI fixture, 2026-10-05

The user supplied `tests/floodway.hy8`, saved from the GUI. Its SHA-256 is
`3bc229d41091dddb77a914718dfd5bb8f1b6112f3d121c0aa4be5b01354419a7`.
The original is preserved: six roadway points, paved surface, crest 19 m,
tailwater 12 m, flows approximately 8/30/100 mÂ³/s, ten 0.9 m circular barrels.
The reader/writer preserves its roadway and constant tailwater exactly in a
file round-trip.

HY-8 8.0.1.2 `-OpenRunSave` exits with `3221225477` (`0xC0000005`) on both
an untouched copy and its adapter rewrite. A six-point submerged derivative
also crashes. Changing bottom roughness to 0.012 and lowering flows to
2/10/20 did not resolve the crash. These observations do not establish its cause.

A separate adapter-derived three-point profile, stations 0/10/20 m and
elevations 20/19/21 m, runs successfully with the original culverts, roughness
and flows. Free flow uses the original 12 m tailwater; submerged flow uses
19.2 m. Both produce roadway discharge and identical parsed executable reports
after reader/writer round-trip. These derivatives are not GUI-authored fixtures
and do not satisfy the original six-point executable validation requirement.
Saved inputs and reports are retained locally under ignored
`validation_artifacts/floodway-gui/`.

Reproduce the maintained input and derived executable tests with:

```powershell
$env:PYTHONPATH = 'src'
python -m pytest tests/test_roadway.py -k floodway -q
```

Executed result: three tests passed. No GUI interaction was used.

### Follow-up investigation and GUI handoff

The earlier three-point derivative was an incomplete workaround. A generated
matrix varying roadway point counts (3/4/5/6/7) and discharge counts (3/6/8)
showed `-OpenRunSave` success exactly when discharge count was at least roadway
point count. The seven-point/six-flow case crashed; seven points/eight flows
succeeded. On the unchanged six-point user geometry, five sorted discharges
crashed, while six and seven succeeded. This strongly suggests an indexing or
allocation defect in that automation path; it does not prove the internal cause.

With six sorted discharges 1/2/4/8/30/100 mÂ³/s, the original geometry produces
HW 20.71 m and roadway flow 48.05 mÂ³/s at 100 mÂ³/s, matching the user's GUI
screenshot (culvert flow 51.95 mÂ³/s). The maintained executable tests now retain
all six original roadway points and add three smaller flows. Submerged tailwater
19.2 m produces HW 21.13 m and roadway flow 73.05 mÂ³/s. Both reports survive
reader/writer executable round-trip unchanged.

`-BuildFullReport` also succeeds on an untouched copy of the original three-flow
fixture. Its generated `.rpt` crossing table contains the same HW 20.71 m,
culvert 51.95 mÂ³/s and roadway 48.05 mÂ³/s. Thus the model can calculate correctly
through another noninteractive executable command. `-OpenRunSavePlots` crashes
like `-OpenRunSave`. The adapter's existing three-flow padding is insufficient
for larger irregular profiles; automatic generalization remains separate work.

One early raw-card flow insertion placed cards beyond their expected input
block, producing zero flows and misleading zero overtopping. Those outputs are
excluded from hydraulic evidence; the successful flow-count probes use the
writer with validated, sorted flow lists.

`scripts/make_roadway_gui_review.py` generates ten crossings in
`tests/fixtures/roadway_gui_review.hy8`: original six-point geometry with three
or six flows, user-defined coefficient and gravel variants, and constant-profile
controls; each has free and submerged tailwater. Eight six-flow crossings ran
individually and had identical reader/writer executable reports. The two original
three-flow variants retain the failure for comparison in the GUI. No automated
GUI interaction was performed. The user will save a separate GUI copy as
described in `tests/fixtures/roadway_gui_review.md`.

Raw matrix inputs, reports and JSON outcomes are retained under ignored
`validation_artifacts/floodway-investigation/`.

### Checks of both supported flow styles

Twenty additional cases compared user-defined and native min/design/max flow
inputs under free and submerged tailwater. Constant two-point profiles passed
both styles. Three-point irregular profiles passed both styles. Six-point
irregular profiles failed with three user flows but passed min/design/max, which
HY-8 expands to eleven active calculation flows. Twelve-point irregular profiles
failed with three user flows and with native min/design/max. Boundary follow-ups
confirmed eleven-point min/design/max succeeds, and twelve-point user-defined
with twelve explicit flows succeeds, under both tailwater conditions.

Raw files and `matrix.json` are retained under ignored
`validation_artifacts/flow-style-investigation/`; compact outcomes are recorded
in `docs/validation_data/hy8_8_0_1_2_roadway_flow_styles.csv`. The observed condition
concerns active calculation-flow count, not simply the number of flow values in
the input. The extra overtopping activation row does not avoid the failure.
Four maintained executable regression cases cover native min/design/max with
six/eleven roadway points and free/submerged tailwater, checking flow expansion,
method preservation, roadway discharge, and exact report round-trip.

Configuration/model code rejects `min-max-increment`; its enum declaration does
not indicate implemented support. Existing rejection coverage was also executed.

### Minimal irregular-profile padding implemented

The writer now supplies exactly as many explicit user flows as irregular roadway
points when the requested list is shorter; sufficient lists are unchanged.
Constant profiles retain their existing serialization. Helpers split the largest
interval, preserving requested flows and labels and avoiding precision collapse.
Distinctness is checked at emitted English six-decimal precision. The original
in-memory flow definition is preserved.

Native min/design/max stays unchanged through eleven irregular points. For more
points, the emitted file switches to user-defined, retains the three requested
minimum/design/maximum flows, and adds exactly enough helpers to reach the point
count. It does not also generate the native eleven-level list. Loaded files
truthfully report the serialized user-defined mode. Endpoint probes showed native
HY-8 can replace the minimum with a nearby design flow, so conversion retains all
three requests rather than reproducing that loss.

The earlier generated GUI review fixture remains unchanged for native-failure
comparison. Regenerating it now applies the workaround, so crossings named
`Original-3Q` retain three requests but have six serialized calculation flows.

Executed validation after this change: `python -m pytest tests -q` passed with
153 passed, one optional GUI fixture skipped, and four legacy parity tests
deselected. Ruff check/format, strict Pyright on `src/run_hy8`, and
`git diff --check` passed. The user's staged wheel files were not modified;
this source change is not included in the previously retained wheel.

## Definition of done

Issue #2 is complete when:

- intentional free and submerged roadway cases can be authored and executed;
- `WEIRCOEFF` has a verified HY-8 8.0.1.2 contract and SI public representation;
- user-defined coefficient behaviour is understood under submergence;
- constant/irregular roadway profile contracts reflect actual HY-8 behaviour;
- existing culvert-only workflows have an explicit safe unexpected-overtopping policy;
- GUI-authored roadway input can round-trip through the supported reader/writer with
  equivalent HY-8 execution;
- source/wheel identity is sufficient for the downstream external-validation record;
- unit/config/executable tests cover the supported behaviour;
- documentation states both the supported capability and its remaining limits;
- all executed validation checks are recorded honestly.
