# Roadway overtopping validation support

Date: 2026-10-05

Issue: #2

Branch: `feature/issue-2-roadway-overtopping-validation`

Baseline: `main` at `9d578a3a7045f0aa84698964f0fb64e7347fe309`

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
- the manual's stated irregular-profile range, believed to be 3–15 points;
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

- `ERROR` — unexpected non-trivial roadway discharge is treated as a failure;
- `WARN` — return the valid HY-8 result and emit a clear warning;
- `ALLOW` — return the result without an overtopping warning.

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
submerged-roadway condition. Use it to prove supported reader → writer → executable
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
