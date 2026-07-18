# Headwater and Flow Helpers

`CulvertCrossing` and `Hy8Project` provide helpers for running common HY-8
headwater and discharge calculations directly from the object model. Each
helper clones the input model, writes a temporary HY-8 project, runs HY-8,
parses the result files, and returns a `HydraulicsResult`. The original model is
not modified.

HY-8 must be installed and configured before using these methods. By default,
the helpers use the path resolved by `Hy8Executable`; pass `hy8=Path(...)` or an
existing `Hy8Executable` to override it for a call.

## Crossing helpers

Given a loaded project and one of its crossings:

```python
from pathlib import Path

from run_hy8 import load_project_from_hy8

project = load_project_from_hy8(Path("example.hy8"))
crossing = project.crossings[0]
```

### Headwater for a discharge

`hw_from_q` runs a single user-defined discharge and returns the matching HY-8
result row:

```python
result = crossing.hw_from_q(q=12.5, project=project)

print(result.computed_flow)
print(result.computed_headwater)
print(result.row)
```

Pass the parent `project` when available so the scenario inherits its unit
system, title metadata, and exit-loss option. A standalone crossing can instead
use the `units` and `exit_loss_option` keyword arguments; their defaults are SI
units and exit-loss option zero.

### Discharge for a headwater

`q_from_hw` searches for the discharge that produces a requested headwater
elevation:

```python
result = crossing.q_from_hw(
    hw=101.25,
    q_hint=12.5,
    project=project,
)

print(result.computed_flow)
print(result.computed_headwater)
```

The optional `q_hint` gives the adaptive search a useful starting point. The
helper samples seed flows, finds values that bracket the target headwater,
subdivides the bracket, and interpolates a final candidate. It raises
`FlowSearchError` when it cannot converge:

```python
from run_hy8.hydraulics import FlowSearchError

try:
    result = crossing.q_from_hw(hw=101.25, project=project)
except FlowSearchError as error:
    if error.best_sample is not None:
        print(error.best_sample.flow, error.best_sample.headwater)
    raise
```

### Discharge for an HW/D ratio

`q_for_hwd` converts a non-negative headwater-to-diameter ratio into a target
headwater elevation, then delegates to `q_from_hw`:

```python
result = crossing.q_for_hwd(
    hw_d_ratio=1.2,
    q_hint=12.5,
    project=project,
)
```

The calculation supports circular and box culverts. It uses the first culvert
definition's inlet invert and characteristic dimension:

- Circular culvert: span
- Box culvert: rise

Every culvert definition in the crossing must have the same shape. The first
definition supplies the characteristic dimension when same-shaped definitions
have different dimensions.

## Project helpers

The same methods are available on `Hy8Project`. They process every crossing in
project order and return an `OrderedDict[str, HydraulicsResult]`:

```python
headwaters = project.hw_from_q(q=12.5)
flows = project.q_from_hw(hw=101.25, q_hint=12.5)
ratio_flows = project.q_for_hwd(hw_d_ratio=1.2, q_hint=12.5)

for crossing_name, result in headwaters.items():
    print(crossing_name, result.computed_headwater)
```

Results normally use the crossing name as their key. Duplicate names receive a
suffix such as `"Crossing 1 (duplicate #2)"` so no result is overwritten.

## Result fields

Each call returns a `HydraulicsResult`, or an ordered mapping of them for a
project call. Its fields are:

- `crossing_name`: crossing reported by HY-8
- `requested_flow`: input discharge for `hw_from_q`, otherwise `None`
- `requested_headwater`: target elevation for `q_from_hw` and `q_for_hwd`
- `computed_flow`: discharge from the selected result row
- `computed_headwater`: headwater elevation from that row
- `row`: complete `Hy8ResultRow`, including any parsed profile data
- `workspace`: retained workspace path when `keep_files=True`

## Workspaces and retained files

Without a `workspace`, the helpers create a temporary directory and delete it
after the calculation. Set `keep_files=True` to retain that directory and
receive its path in `result.workspace`:

```python
result = crossing.hw_from_q(q=12.5, project=project, keep_files=True)
print(result.workspace)
```

To choose the location yourself, pass a directory:

```python
result = crossing.q_from_hw(
    hw=101.25,
    project=project,
    workspace=Path("hydraulics-runs"),
    keep_files=True,
)
```

Caller-supplied workspace directories are never deleted. Use separate
directories for concurrent calculations to avoid filename collisions.
