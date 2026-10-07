# Elliptical support: local validation feedback

Date: 7 October 2026 (Australia/Perth)
Repository: `E:\Github\run-hy8`
Branch: `feature/issue-5-elliptical-support`
HEAD at handoff: `99e945d2e5df6b3a93383f436ca4883c7711ab83`

## Outcome

The branch passes lint, formatting, strict type checking and tests that do not
require HY-8. Local HY-8 execution does **not** validate elliptical hydraulics:
eight executable tests fail. Preserve those failures until the cause is understood.
Serialization, exit code 0 and finite reports are insufficient acceptance evidence.

## Execution environment

- Windows, normal user Python 3.14.6; source tests use `PYTHONPATH=src`.
- Executable: `C:\Program Files\HY-8 8.00\HY864.exe`.
- File and product version: `8.0.1.2`.
- Installed and repository `ShapeDB.dat` SHA-256 both verified as
  `2479e9444feaff529313e18a1b26fc2de4f6b6c541db58477da6bebc602164a7`.

## Findings requiring investigation

### 1. Original fixture crashed HY-8

The original ellipse fixture inherited identical inlet/outlet stations from
`build_sample_project()`, giving it zero length. Both orientations crashed with
exit status `3221225477` (`0xC0000005`). A controlled probe with the same ellipse
and a 20 m outlet station completed with exit code 0. Changing dimensions alone
while retaining zero length still crashed.

`tests/test_elliptical.py::_ellipse_project` now supplies a 20 m length, tailwater
invert equal to the barrel outlet invert, tailwater elevation 0.2 m above that
invert, and min/design/max flows 0.2/1.0/2.0 m3/s. These fixture changes prevent
the original crash; they do not establish valid hydraulic output.

Consider whether production validation should reject zero-length elliptical
barrels before invoking HY-8. No such production fix was made in this review.

### 2. Finite reports contain zero culvert discharge

Round-trip execution covers both span/rise pairs `(1.524, 0.9652)` and
`(0.9652, 1.524)` and all three `EllipticalConcreteInlet` configurations.
The shape, inlet configuration and dimensions survive the round trip, and
reports contain finite values, but every reported barrel discharge is zero.

The tests now require at least one positive barrel discharge. All six
orientation/inlet combinations fail that assertion. Do not remove or weaken it
to obtain a passing test run.

### 3. Forward execution fails before inverse execution can be validated

Both `test_ellipse_inverse_helpers_with_local_hy8` cases fail during the initial
`hw_from_q(1.0)` call with `RoadwayOvertoppingError`. HY-8 reports the entire
requested 1.0 m3/s over the roadway and zero barrel flow. Consequently, the
inverse and HW/D helper assertions have not been reached successfully.

Additional probes reproduced zero barrel flow with user-defined flow lists,
with and without labels, and with a narrower 0.9/1.0/1.1 min/design/max range.
Lowering tailwater and changing roadway shape did not resolve the forward
failure. The issue is not established as exclusive to user-defined flows.

The cause remains unresolved. Compare a genuinely GUI-created elliptical
project with the generated project, including all geometry and initialization
cards. Confirm the native shape/material contract independently rather than
treating preservation of numeric cards as proof of correct hydraulic behavior.
Do not bypass the overtopping policy or classify this as an upstream HY-8 bug
without evidence.

## Latest local check results

| Check | Result |
| --- | --- |
| `python -m ruff check .` | Passed |
| `python -m ruff format --check .` | Passed; 72 files formatted |
| `python -m pyright src/run_hy8` | Passed; 0 errors, warnings or information messages |
| `git diff --check` | Passed |
| Tests excluding HY-8 and legacy parity | 143 passed, 38 deselected |
| Full source suite with coverage and local HY-8 | 168 passed, 8 failed, 1 skipped, 4 deselected |
| `python -m mkdocs build --strict` | Passed after validation-note update |
| Retained wheel verification before latest rebuild | Failed: `run_hy8/hydraulics.py` differed from source |
| Staged build and retained wheel verification after rebuild | Passed |
| Isolated installed-wheel smoke test | Passed |

The skipped test requires a GUI-created roadway fixture configured through
`HY8_ROADWAY_GUI_FIXTURE`. The four default deselections are legacy parity tests.
The standalone MkDocs build reported `docs/packaging.md` outside navigation as
an informational message; it did not fail strict mode.

## GitHub CI versus local results

The GitHub run inspected during this review was:
<https://github.com/Chain-Frost/run-hy8/actions/runs/37618814210>

It ran at commit `10241187a6fda199e6b49a892a85538743db22bb`, which is earlier
than the handoff HEAD. Lint, type checking and tests passed. **Verify retained
package artifact** failed, and **Verify package artifacts** was skipped.
The exact GitHub log error was not retrieved, so the later local wheel mismatch
must not be presented as a confirmed explanation of that historical CI failure.
This review reran checks locally; it did not trigger a new GitHub workflow run.

## Package and working-tree state

The latest rerun rebuilt `dist/run_hy8-2026.10.5.1-py3-none-any.whl` using
`python scripts/build_library.py --skip-pip`, then verified it and completed
the isolated-install smoke test. The rebuilt wheel SHA-256 is:

`399fb1a4936e8f147a3cc7262db184faf357eac3c7e93ae5dfeb656d222d5a4b`

Before writing this handoff, the wheel was the only working-tree modification.
This review did not commit or push it. The version number was not changed.
Treat the rebuilt wheel as a local validation artifact, not a validated release
of elliptical hydraulic support.

## Reproduction commands

Run from the repository in PowerShell:

```powershell
$env:PYTHONPATH = 'src'
python -m ruff check .
python -m ruff format --check .
python -m pyright src/run_hy8
python -m pytest tests/test_elliptical.py -m requires_hy8 -q --tb=short
python -m pytest tests --cov=src/run_hy8 --cov-report=xml -q --tb=short -rs
python -m pytest tests -m 'not requires_hy8 and not legacy_parity' -q
python scripts/verify_wheel.py
python scripts/smoke_test_installed_wheel.py
```

To retain a forward-run project and its reports for comparison, use
`crossing.hw_from_q(1.0, project=project, workspace=Path(...), keep_files=True)`.
The call currently raises, but the files remain available for inspection.

Acceptance requires positive and credible barrel flow, successful forward and
inverse execution in both orientations, and preserved inlet/dimension semantics.
Record the executable version, raw project/report evidence and final full-suite
results after the hydraulic cause is resolved.


## Follow-up after catalogue investigation

The historical failures above were retained and investigated on the same branch.
Subsequent comparison with the GUI-created `reference_docs/example-ellipse.hy8`
and the pinned `ShapeDB.dat` identified two project-contract defects that were
not represented in the original local run.

1. **Material codes are shape-contextual.** For `Elliptical`, ShapeDB lists
   `Steel or Aluminum` as material index 1 and `Concrete` as index 2. The
   original writer treated the internal `CulvertMaterial.CONCRETE` numeric
   value as a global file code and therefore wrote an incorrect ellipse
   material. The writer/reader now translate material codes by
   `(shape, material)` context.
2. **Ellipses are catalogue shapes.** The HY-8 8.0.1.2 database contains 23
   concrete ellipse sizes and 40 Steel-or-Aluminum sizes. A concrete
   `60 in x 38 in` selection has ShapeDB `Br/Tr/Cr/B` values of
   `51.6/51.6/16.43/19 in`. A controlled HY-8 executable probe showed:
   - zero `Br/Tr/Cr/B` -> zero barrel discharge;
   - changing `IRREGSIZE` alone -> still zero barrel discharge;
   - ShapeDB `Br/Tr/Cr/B` -> positive barrel discharge up to the requested
     2.0 m3/s.

The current branch therefore writes concrete ellipses only when their
`span/rise` pair matches a version-pinned ShapeDB catalogue entry. It does not
snap to a nearest size or create a rotated/reversed entry that HY-8 does not
list. `BARRELGEOMETRY` is populated from the matching catalogue row.

This follow-up does **not** supersede the requirement for a final local
Windows/HY-8 8.0.1.2 acceptance run. Once the hosted catalogue-backed
executable tests and normal CI are clean, rerun the reproduction commands above
against the then-current branch and record the new result separately from this
historical failing run.
