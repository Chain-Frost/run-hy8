# Low-flow inverse acceptance: issue #19

Status: implementation and native source/installed-wheel acceptance complete;
review pending. Updated 2026-11-09; next review 2026-11-16
or when PR review arrives. Owner: maintainer. Branch: `fix/inverse-resolution-19`.
Delivery: one checked batch on that branch; current hosted results belong to its
[pull request](https://github.com/Chain-Frost/run-hy8/pulls?q=is%3Apr+head%3Afix%2Finverse-resolution-19),
whose description records the final commit and CI outcome separately from local
acceptance. Main and the installed published package remain unchanged.

## Scope and result

[Issue #19](https://github.com/Chain-Frost/run-hy8/issues/19) reproduces with
Windows Python 3.14.6, installed `run-hy8==2026.10.18.2`, and HY-8 8.0.1.2.
The first evaluated seed is 0.05 m3/s. The first six requested flows are
0.05, 0.1, 0.25, 0.5, 0.8482300376140988, and 1.0 m3/s. All are evaluated in
one native batch before the Python loop accepts its first sample. The returned
RST flow is 0.05 and headwater 43.56 m, against target 43.5636 m and constant
tailwater 43.5542 m. The displayed 0.0036 m residual passes the old 0.01 m stop.

The input is the exact retained, conditional EG11 model from
[ryan-tools #297](https://github.com/Chain-Frost/ryan-tools/pull/297): effective
diameter already reduced to approximately 0.8485281374 m, three equal-flow
concrete circular barrels, square-edge headwall, n=0.015, length 20 m,
inverts 43.35/42.75 m, standard losses, and deliberately assumed width
contraction 1.0 instead of unsupported source 0.9. No geometry reconstruction,
coefficient tuning, new TUFLOW simulation, or ten-pair campaign was performed.

| Requested Q (m3/s, whole crossing) | RST headwater (m) | PLT Headwater ordinate (m) |
| ---: | ---: | ---: |
| 0.05 | 43.56 | 43.5551 |
| 0.10 | 43.56 | 43.5581 |
| 0.149540795 | 43.56 | 43.5636 |
| 0.20 | 43.57 | 43.5742 |

RST cannot distinguish the first three candidates. The sampled PLT curve is
increasing and its 0.149540795 m3/s case has the target plotted headwater.
These ordinates have finer printed precision (four decimal places here),
not established numerical accuracy or global uniqueness. The PLT `Headwater`
series is distinct from the inlet barrel `Profile` ordinate. Its flow identity
is matched using the internal English-unit `FlowProfileFlow`, converted to SI;
the padded minimum-flow profile is not mistaken for the requested flow.
RST prints headwater and total discharge to two decimals in these SI cases;
the 0.8482300376 trial, for example, is returned as Q=0.85.

## Conservative acceptance repair

The public API keeps its 0.01 m SI headwater tolerance and RST result source.
It accepts a candidate only inside a sampled rising bracket whose endpoints
are outside the target tolerance band, and chooses the closest tested candidate
instead of the first seed. Distinct trial flows sharing a reported headwater
near the target raise `FlowSearchError`, preserving diagnostic `best_sample`.
Sampled headwater decreases fail closed before interpolation. An unbracketed
minimum seed cannot be accepted even if it matches the target. The same guards
apply to seeds, subdivisions, interpolation, and expansion.

Trial evaluations are deduplicated and capped at the existing 20-sample budget,
including batches; an exhausted or repeated interpolation candidate terminates
with an error. Public error targets retain the requested project's units.
This is conservative: some physically valid inverses now fail at coarse report
precision or the seed floor. It does not specify a relative Q tolerance, prove
global monotonicity, or detect every unsampled discontinuity. A validated PLT
parser and explicit discharge uncertainty contract remain possible follow-up
work; silently changing report source or shrinking tolerance is avoided here.

## Reproduction and provenance

The [retained evidence directory](https://github.com/Chain-Frost/run-hy8/tree/fix/inverse-resolution-19/reference_docs/validation/2026-11-09-inverse-resolution)
contains the exact input, native `.hy8/.rst/.rsql/.plt` outputs, ordered candidate
trace, versions, and SHA-256 manifests for published, source, and installed-wheel
runs. Local attributes preserve raw native file bytes in Git.

- Serialized input SHA-256: `b71007d8dc863703fd7177d05017aae9e1c2e101be3f416a02ccf02398a872cf`.
- HY-8 executable SHA-256: `0b1c5e7fb6b48be9c675b5486ae9a84346f436c5c649aa5ed09a1552267ee806`.
- The input bytes match the original retained artifact manifest. Original tutorial
  source hashes remain in the [immutable consumer evidence](https://github.com/Chain-Frost/ryan-tools/blob/0784d109f37552bf49368d483625560471a28aea/docs/validation_data/wp15-eg11-assumed-20261109/source-sha256.json);
  original source datasets were not re-read for this investigation.
- Candidate wheel: `run_hy8-2026.10.16.1-py3-none-any.whl`, SHA-256
  `98e52f599e3b30e0049e0d419e27abf9ee2d0617d416cb4fe28f711b92dd63d1`.
  This is a local verification build of main's declared version, not a release.
  Source-checkout distribution metadata reports stale egg-info `2026.10.5.1`;
  identify candidate code by `hydraulics_sha256`, not that metadata. The isolated
  wheel metadata is 2026.10.16.1 and its hydraulic source hash matches the candidate.

From repository root, with fresh output directories:

```powershell
# Installed published 2026.10.18.2; do not overwrite the user's installation.
Remove-Item Env:PYTHONPATH -ErrorAction SilentlyContinue
python reference_docs/validation/2026-11-09-inverse-resolution/reproduce.py --baseline --workspace validation_artifacts/issue19-published
# Candidate source
$env:PYTHONPATH='src'
python reference_docs/validation/2026-11-09-inverse-resolution/reproduce.py --workspace validation_artifacts/issue19-source
python -m pytest tests/test_inverse_resolution.py tests/test_roadway.py tests/test_elliptical.py -q
python scripts/build_library.py --skip-pip
python scripts/verify_wheel.py
python scripts/smoke_test_installed_wheel.py
# Install into a new target, preserving the published user installation.
python -m pip install --no-deps --target validation_artifacts/issue19-installed dist/run_hy8-2026.10.16.1-py3-none-any.whl
$env:PYTHONPATH=(Join-Path (Get-Location) 'validation_artifacts/issue19-installed')
python reference_docs/validation/2026-11-09-inverse-resolution/reproduce.py --workspace validation_artifacts/issue19-wheel
```

## Acceptance and handoff

- Focused source validation: **136 passed, 1 skipped**. The pre-existing optional
  GUI roadway fixture is missing; none of the issue #19 checks skip.
- Package tests (`python -m pytest tests -q`): **397 passed, 1 skipped,
  4 legacy-parity deselections**, including native circular and three ellipse
  inverse cases. New deterministic cases cover premature seed acceptance, flat
  and rounded headwaters, absent bracket, non-monotonicity, a step with no
  resolvable target, bounded search, and a genuinely resolvable curve.
- Published/source/isolated-wheel replay: published returns 0.05; both candidates
  raise the resolution error. Four forward RST/PLT pairs agree across all three;
  well-conditioned circular Q=1 inverse still returns Q=1.
- Ruff, strict Pyright on changed hydraulic code/new validation Python, verified
  wheel, isolated installed-wheel smoke, strict MkDocs, and diff whitespace checks
  pass. Hosted CI is recorded at delivery.
- A bare repository-root pytest invocation collected pre-existing ignored
  `validation_artifacts/gui-tools/win32comext/taskscheduler/test/test_addtask.py`
  and crashed with a Windows access violation during third-party collection.
  The explicit package `tests` run above excludes that unrelated installation;
  it was preserved untouched.

Next action: review the conservative acceptance contract and exact-head hosted
checks. No merge or release authorized. Keep `ryan-tools#102` open: these
conditional tutorial assumptions do not establish physical TUFLOW parity,
independent engineering acceptance, or full-blockage support. #298's forward
outlet-profile explanation remains a separate investigation.
