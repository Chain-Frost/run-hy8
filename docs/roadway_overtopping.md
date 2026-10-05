# Roadway overtopping

Intentional free and submerged roadway inputs are supported. `validate()` checks input
geometry and format; acceptance of actual roadway flow is a separate result policy.

## Authoring a roadway

```python
from run_hy8 import RoadwayProfile, RoadwayShape, RoadwaySurface

roadway = RoadwayProfile(
    width=10.0,
    shape=RoadwayShape.CONSTANT,
    stations=[0.0, 20.0],
    elevations=[12.0, 12.0],
    surface=RoadwaySurface.USER_DEFINED,
    discharge_coefficient=1.6,
)
```

`discharge_coefficient` is always **SI**, in `m**0.5/s`, for `Q = C L H**1.5`.
It is required in `USER_DEFINED` mode. The installed HY-8 manual, section 3.3.1,
page 41, specifies English coefficients from 2.5 through 3.095, inclusive. The
corresponding SI range is **1.380217374184226 through 1.708709109240072**.
Non-finite coefficients are rejected. Automatic paved/gravel modes retain an
inactive saved coefficient, including zero, without treating it as selected.

`WEIRCOEFF` stores English coefficients regardless of the project's display flag:
`C_SI = C_English * sqrt(0.3048)`. For example, SI 1.6 is written as English
2.898094 after six-decimal card formatting. The reader applies the inverse
conversion and preserves the coefficient through model dictionaries and JSON
roadway configurations. It does not substitute a paved/gravel coefficient.

Existing model geometry/flow authoring conventions remain: SI projects use metres
and cubic metres per second; EN-authored projects use feet and cubic feet per second.
The coefficient is the explicit SI exception in both. Loaded `.hy8` projects are
converted to SI. Parsed result quantities are now normalized to SI even for English
reports; consumers that previously used raw English report numbers must adjust.

## Profile forms

`RoadwayShape.CONSTANT` writes flag 1 and requires exactly two endpoints with equal
elevations. Crest length is the station difference; `width` is the top width in the
direction of flow, a separate quantity.

`RoadwayShape.IRREGULAR` writes flag 2. It requires **3-5000 points**, matching HY-8
7.70 and later. The installed manual still says 3-15, but the official
[FHWA release history](https://www.fhwa.dot.gov/engineering/hydraulics/software/hy8/)
states that 7.70 increased the limit to 5000. An exploratory 5000-point saved-file
probe completed under 8.0.1.2 and retained all points. The focused hydraulic cases
use three points; this is not a claim that every larger profile has been validated.

Stations must be finite and strictly increasing, with positive horizontal extent;
duplicate stations, non-finite elevations and non-positive top width are rejected.
This adapter deliberately requires unambiguous positive-length intervals, rather
than attempting to reproduce undefined or ambiguous executable duplicate behavior.
For a linear slope, supply an explicit collinear middle point, for example
stations `[0, 10, 20]`, elevations `[12, 12.5, 13]`.
Numeric shape flags remain accepted, and dictionaries retain numeric shape flags;
configuration also accepts `"CONSTANT"` and `"IRREGULAR"`.

HY-8 8.0.1.2 `-OpenRunSave` crashes in the tested irregular cases when roadway
point count exceeds the active calculation-flow count. The writer now pads
**only irregular profiles** to that count, adding exactly the missing flows.
Six roadway points with three requested user flows therefore get three helpers;
an already sufficient list gets none. All requested flows and labels are retained.
Helpers split the largest flow interval, avoiding tiny discharges that collapse
at HY-8's six-decimal English input precision. They are labelled `dummy flow`
when the requested list has labels. Unrepresentable distinct padding raises an
error instead of writing duplicate helper flows.

Constant-profile serialization is unchanged, including its existing single-flow
padding to two entries. Additional helper rows and HY-8's roadway-activation row
can appear in saved reports, and remain subject to the selected overtopping policy.

Two flow styles are supported. **User-defined** directly supplies the active flow
list. **Min/design/max** writes native method 0: HY-8 expands the range to eleven
calculation flows, retaining the design flow in the generated list. Native
min/design/max succeeds for tested six- and eleven-point irregular roadways but
crashes for twelve points. A twelve-point roadway succeeds with twelve explicit
user flows. Both free and submerged conditions were checked. The separate
road-activation result row does not make twelve-point min/design/max safe.
Constant two-point roadways succeeded with both supported flow styles.

For irregular profiles with **more than eleven points**, the writer changes native
min/design/max to explicit user-defined mode in the emitted file. It starts with
the three requested minimum/design/maximum values and pads to exactly the roadway
point count. It does not add the native intermediate levels as well. Labels
identify the three requests and the helpers. Smaller irregular profiles retain
native min/design/max mode. The in-memory flow definition is not changed; loading
the emitted file correctly reports user-defined mode when conversion occurred.

`MIN_MAX_INCREMENT` exists as an enum member but is rejected by configuration
parsing and model validation; it is not an implemented flow style. Detailed
flow-style probe outcomes are saved in
`docs/validation_data/hy8_8_0_1_2_roadway_flow_styles.csv`. These probe outcomes
predate the workaround and describe the native executable's behavior.

## Accepting actual overtopping

High-level crossing/project `hw_from_q`, `q_from_hw` and `q_for_hwd` default to
`RoadwayOvertoppingPolicy.ERROR`. Pass an explicit policy for validation work:

```python
from run_hy8 import RoadwayOvertoppingPolicy

result = crossing.hw_from_q(
    20.0,
    roadway_overtopping=RoadwayOvertoppingPolicy.ALLOW,
    keep_files=True,
)
```

- `ERROR` raises `RoadwayOvertoppingError`, retaining `crossing_name` and parsed
  `results` on the exception.
- `WARN` returns the valid result and emits `RoadwayOvertoppingWarning`.
- `ALLOW` returns it without an overtopping warning.

The check uses the absolute **parsed roadway discharge** in every result row.
Discharges greater than **0.005 m3/s**, half the SI report increment, trigger the
policy; the threshold is a reporting policy, not an engineering design tolerance.
Water levels and the `Overtops` flag alone do not trigger it. Missing/non-finite
roadway discharge is a parsing failure under all policies, not an assumed zero.

Inverse searches propagate the selected policy through every executable batch,
including helper and intermediate flows. `ERROR` can therefore stop a search whose
final selected flow might be dry but whose exploratory batch overtops. Choose
`WARN` or `ALLOW` explicitly when that exploration is intentional. `WARN` may emit
warnings for multiple batches.

Constant tailwater at/above the lowest crest is serializable under every policy.
It does not establish actual roadway flow, so it is not a model-validation error.
Finite tailwater elevations and tailwater at/above its invert are still required.

The CLI offers the same policy when `build --run-exe` executes a project:

```powershell
python -m run_hy8 build --config roadway.json --output roadway.hy8 --overwrite --run-exe 'C:\Program Files\HY-8 8.00\HY864.exe' --roadway-overtopping allow
```

The low-level executable wrapper does not parse results or enforce policy. Call
`check_roadway_overtopping(results, crossing_name, policy)` after manual parsing.
Command-line HY-8 launches use a hidden window.

## Evidence and submergence limits

The [retained 24-case CSV](validation_data/hy8_8_0_1_2_roadway_adapter.csv) verifies
saved inputs and reader/writer executable report equivalence. It includes constant
and irregular free flow, submerged constant flow, all three surface modes,
coefficient endpoints and English/SI display variants. Each compares the saved
tailwater, profile, extent, top width, coefficient, culvert geometry, barrel count,
roughness and inlet configuration. Numeric input tolerances follow six-decimal
English card precision; report round-trips are exactly equal after parsing.

At 20 m3/s, constant crest 12 m, length 20 m and top width 10 m, the user-defined
SI coefficient 1.6 case reports HW 12.62 m and road flow 15.76 m3/s in free flow;
TW 12.9 m reports HW 12.94 m and road flow 19.27 m3/s. Changing the coefficient
from English 2.5 to 3.095 changes the user-defined results both free and submerged.
The same change leaves paved and gravel results unchanged within their report
precision. These are adapter observations, not solver calibration or external
validation of another hydraulic solver.

The manual's surface selector and saved `SURFACE` card offer mutually exclusive
paved, gravel or coefficient modes. No independent paved/gravel submergence
selector was found in the inspected saved cards. `USER_DEFINED` demonstrably
responds to tailwater, but **its exact submergence law remains unresolved**.
The API does not imply independently selectable paved/gravel correction with a
fixed coefficient. Downstream submerged comparisons requiring both should remain
`unsupported comparison` until equivalence is established.

## Result precision

HY-8 8.0.1.2 `.rst` reports observed here have two decimal places in the display
units. English flow increments are 0.01 cfs (0.00028316846592 m3/s); SI increments
are 0.01 m3/s. No rounding is added by the parser beyond conversion of the values
actually emitted.

`.rsql` observed values use about six significant figures and English flow storage
independently of display units. `FlowProfile.flow` is now converted to SI;
`raw_fields` retains emitted strings and precision. `HeadwaterToDepth` is **HW/D**,
available as `headwater_to_depth_ratio`, not a depth in metres. The retained
`headwater_depth` compatibility field is NaN because this file does not provide
that quantity. Result rows expose matching raw `profile_fields`; a selected
profile is not reused for a different discharge.

The inspected `.rsql` files do **not** contain roadway discharge or submergence
factors. No unrounded roadway result was available in these outputs; none is
inferred from rounded flow closure. Raw `.rst`, `.rsql`, `.hy8` and `.plt` files
are retained under the ignored validation workspace with hashes in the evidence.

## Runnable handoff

From the source checkout with normal user Python:

```powershell
$env:PYTHONPATH='src'
python scripts/validate_roadway.py --case constant-free
python scripts/validate_roadway.py --case irregular-free
python scripts/validate_roadway.py --case submerged
python scripts/validate_roadway.py --matrix --output validation_artifacts/roadway-matrix --csv docs/validation_data/hy8_8_0_1_2_roadway_adapter.csv
```

Each command executes, loads and verifies saved inputs, then writes/runs the
loaded project again and checks report equivalence. `identity.json` records the
actual import location, source-file hashes, checkout HEAD/status, Python, source
project version, installed distribution metadata and executable hash. Distribution
metadata alone is not proof of the imported source version.

Build and verify a wheel without replacing the user's installed package:

```powershell
python -m build --wheel --outdir validation_artifacts/wheels
python -m pip install --no-deps --target validation_artifacts/wheel-install-final validation_artifacts/wheels/run_hy8-2026.10.5.1-py3-none-any.whl
python -I scripts/verify_roadway_wheel.py --wheel validation_artifacts/wheels/run_hy8-2026.10.5.1-py3-none-any.whl --installed validation_artifacts/wheel-install-final --output validation_artifacts/wheel-verification-final.json
```

Use a fresh target directory for a later build. Verification checks every package
source file/typing marker against the wheel and installed files, confirms the
isolated import path/version, and runs a coefficient smoke test. Runtime
dependencies are explicitly exposed from the existing user site; the source
checkout is excluded from the import path.

The current artifact identifies an **uncommitted source snapshot**, not a release
built from a new committed revision. The [provenance record](validation_data/roadway_adapter_provenance.json)
records the base HEAD, exact source/wheel hashes and this limit. Commit/rebuild
identity and the GUI-authored reference fixture remain pending. The user will
create the latter separately; no GUI controls or interactive GUI automation form
part of this implementation. Once supplied:

```powershell
$env:HY8_ROADWAY_GUI_FIXTURE='C:\path\to\irregular-submerged.hy8'
python -m pytest tests/test_roadway.py -k gui_fixture -m requires_hy8 -q
```
