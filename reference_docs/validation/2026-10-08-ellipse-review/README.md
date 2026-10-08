# PR #7 local review acceptance evidence

Run date: 8 October 2026, Australia/Perth. Base commit:
`69ec68868899dd4c58f7e43b4b25c3199c36d51c`, plus the accompanying uncommitted
reader and regression changes. This validates the working tree, not a future
published commit. Keep the PR draft until the remaining acceptance items below
are resolved.

## Environment and validation

- Windows; Python 3.14.6; `PYTHONPATH=src`.
- Executable: `C:\Program Files\HY-8 8.00\HY864.exe`, file version `8.0.1.2`.
- Installed ShapeDB SHA-256:
  `2479e9444feaff529313e18a1b26fc2de4f6b6c541db58477da6bebc602164a7`.
- Full default suite: **345 passed, 1 skipped, 4 deselected**.
  The skip requires `HY8_ROADWAY_GUI_FIXTURE`; legacy comparisons are deselected.
- Supported executable selection (`requires_hy8 and not legacy_parity`):
  **41 passed, 1 skipped, 308 deselected**.
- All 63 catalogue rows in SI and English: **126 cases**, checking runtime data
  against the independently retained ShapeDB CSV, writer geometry, dimensions,
  material and Manning defaults, and SI-normalized reader output. Entire
  `test_ellipse_catalogue.py`: **142 passed** after adding the CSV comparisons.
- Ruff check, Ruff format (80 files), strict Pyright (zero errors/warnings),
  `git diff --check`, and strict MkDocs build passed. MkDocs reports the existing
  `packaging.md` navigation omission.
- Candidate build, retained-wheel verification and isolated installed-wheel
  smoke passed. Wheel: `run_hy8-2026.10.5.1-py3-none-any.whl`, SHA-256:
  `456aed5a32bf3452d38e1c08fa5a6d6afda6c9381d0dd6e6309c608d03e2c3ad`.
- An additional run with `-m requires_hy8` also selected the four legacy tests
  because an explicit marker overrides pytest's default marker filter: **41
  passed, 4 failed, 1 skipped, 304 deselected**. Those failures concern legacy
  output comparisons and an older constant-roadway fixture. They are outside
  the default supported suite; they were not repaired or hidden.

## Review items addressed

1. Local executable acceptance was run on this working tree, with representative
   raw artifacts retained here. The complete run artifacts and logs are in
   ignored `validation_artifacts/review-full/` and `review-full.log` locally.
2. Steel forward, inverse headwater and inverse HW/D regression now runs at
   20 m3/s. Flow tolerance is 0.02 m3/s and headwater tolerance is 0.01 m.
3. Steel numerical parity compares the independent GUI-created
   `reference_docs/example-ellipse.hy8` directly with its reader/writer
   reconstruction. It checks multiple flows, headwater, discharge, outlet
   velocity, roadway flow and exact flow/control state. Numeric tolerance is
   0.01 in SI report units, matching the final displayed report digit; flow
   partition tolerance is 0.02 m3/s. Both inputs and outputs are retained in
   [steel-gui-parity](steel-gui-parity/). This is serialization parity against
   independently created input, not validation of HY-8's equations.
4. The complete catalogue matrix passes in both unit systems. The reader
   intentionally returns SI regardless of the project display flag.
5. Both positive and reversed station directions ran successfully. Reversing
   the 20 m station difference retained positive 0.2 m3/s barrel flow and a
   reported free length of 20 m. Evidence is in
   [reversed-stations](reversed-stations/). Rejecting reversed stations is not
   supported by this observation; zero length remains rejected.

## Findings and outstanding acceptance

The GUI reference exposed an actual reader defect: `DISCHARGEMETHOD 0` projects
may retain an inactive `DISCHARGEXYUSER` table of two zeros. The reader previously
treated that inactive table as the selected range and rejected the project.
It now uses `DISCHARGERANGE` for range-mode projects. A non-executable regression
loads the unmodified GUI reference and checks 20/40/60 m3/s.

The original large steel fixture's 0.2-2 m3/s range caused local HY-8 access
violations (`3221225477`, `0xC0000005`) for all four inlet configurations.
The retained GUI reference uses 20-60 m3/s; all four configurations pass at
that range. This confirms acceptance at that range only. Low-flow steel HY-8
behavior remains unresolved and must not be advertised as validated. No
production flow restrictions were invented from this limited observation.

**Concrete quantitative parity remains open.** [concrete](concrete/) contains
generated input and positive-flow reports, but no independent GUI-created
concrete project/results were available. These artifacts are executable smoke
evidence, not independent numerical parity. Obtain a concrete catalogue case
created independently in HY-8, retain its provenance and results at multiple
flows, then compare headwater, discharge, velocity and control state using the
same report-precision tolerances. Do not manufacture the reference with this
writer or classify these generated results as independent.

No commit, push, merge, review reply or thread resolution was performed by this
local review action. Hosted CI has not run on these uncommitted changes.

## Reproduction

```powershell
$env:PYTHONPATH = 'src'
python -m pytest tests -q -ra --tb=short
python -m pytest tests -m 'requires_hy8 and not legacy_parity' -q -ra --tb=short
python -m pytest tests/test_ellipse_catalogue.py -q
python -m ruff check .
python -m ruff format --check .
python -m pyright src/run_hy8
python -m mkdocs build --strict
python scripts/build_library.py --skip-pip
python scripts/verify_wheel.py
python scripts/smoke_test_installed_wheel.py
git diff --check
```
