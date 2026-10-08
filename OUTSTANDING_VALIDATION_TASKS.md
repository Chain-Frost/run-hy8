# Outstanding validation tasks

Recorded 8 October 2026. These are future follow-up tasks, explicitly outside
PR #7 at the user's direction. They are not acceptance or merge gates for that
PR. Deferral does not establish validation for the unresolved cases.

Baseline evidence: [local ellipse review run](reference_docs/validation/2026-10-08-ellipse-review/README.md).
Record new executable versions, source commits, inputs, raw outputs, tolerances
and exact check results when completing each task; do not reuse historical
test counts as current results.

## VAL-001: Independent concrete ellipse numerical parity

- [ ] Create or obtain a concrete catalogue project independently in the HY-8
  GUI, recording creator/source, executable version and catalogue selection.
- [ ] Retain the independent `.hy8` and `.rst`/`.rsql` results at multiple flows.
- [ ] Compare library-generated results with the independent reference for
  headwater, barrel discharge, outlet velocity, roadway flow and control state.
- [ ] Check conservation of total flow between barrel and roadway. Document
  numeric tolerances from report precision; the current steel comparison uses
  0.01 in SI report units and 0.02 m3/s for flow partition.
- [ ] Add a reproducible regression and record the final local HY-8 results.

Completion requires numerical agreement with an independent input/reference,
positive meaningful barrel flow and retained provenance. Current generated
concrete reports are smoke evidence and cannot serve as the independent reference.

## VAL-002: Large steel ellipse low-flow HY-8 crashes

- [ ] Reproduce the 241 in x 156 in Steel-or-Aluminum ellipse failure at
  0.2-2 m3/s with HY-8 8.0.1.2 for all four straight inlet configurations.
- [ ] Retain failing inputs, command, return code and any outputs. The observed
  Windows return code was `3221225477` (`0xC0000005`).
- [ ] Compare with an independently GUI-created case at the same low flows;
  use controlled changes and source evidence to distinguish serialization
  defects from HY-8 executable behavior.
- [ ] Establish the affected geometry/flow/version scope. Implement a justified
  correction or document a demonstrated upstream limitation, with regressions.
- [ ] Rerun forward, inverse headwater and inverse HW/D checks for affected cases
  and the existing 20-60 m3/s steel acceptance range.

Completion requires an explained, reproducible outcome and appropriate behavior
for affected inputs. Raising the fixture flow or obtaining exit code zero alone
does not resolve this task. Current steel evidence covers 20-60 m3/s only.

## VAL-003: Optional roadway GUI fixture coverage

- [ ] Obtain the GUI-created roadway fixture with provenance and configure
  `HY8_ROADWAY_GUI_FIXTURE` to its local path.
- [ ] Run its executable regression, retain raw inputs/results and record
  numerical acceptance and test counts without the fixture-dependent skip.

## VAL-004: Legacy comparison follow-up

- [ ] Review the four legacy comparisons excluded from the default suite.
- [ ] Investigate the historical output differences and constant-roadway
  fixture validation failure, then update obsolete fixtures or document
  intentional differences with evidence.
- [ ] Run the legacy selection explicitly and record each result separately
  from supported package correctness checks.

The default suite's four deselections are intentional until this follow-up
establishes which legacy expectations remain applicable.
