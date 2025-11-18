# Hydraulics Helper Strategy

## Objectives
- Add **methods directly on `Hy8Project` and `CulvertCrossing`** so downstream code can call `crossing.hw_from_q(...)` without extra helper objects.
- Each method is responsible for the entire HY-8 workflow: writing a temporary `.hy8`, running the HY-8 executable, parsing the emitted `.rst/.rsql`, and returning structured results.
- The public surface is limited to three operations:
  1. `hw_from_q(self, q: float, ...) -> HydraulicsResult`
  2. `q_from_hw(self, hw: float, q_hint: float | None = None, ...) -> HydraulicsResult`
  3. `q_for_hwd(self, hw_d_ratio: float, ...) -> HydraulicsResult`
- Project-level methods loop over `self.crossings`, call the per-crossing helpers, and return an `OrderedDict[str, HydraulicsResult]` following the crossing order.

## Execution Flow
1. Clone the desired project/crossing (respecting optional overrides for units/exit losses) so we can safely modify flow definitions for the scenario.
2. Write the temporary `.hy8` via `Hy8FileWriter` into a caller-supplied `workspace` (or a temporary directory).
3. Invoke HY-8 through `Hy8Executable`:
   - `hw_from_q`: single-run `-OpenRunSave` using the requested discharge.
   - `q_from_hw`: bracket flows (maybe by reusing the crossing's existing definition), run HY-8 for each candidate until we straddle the target headwater, then interpolate between the two most recent runs.
   - `q_for_hwd`: translate the ratio -> headwater elevation or depth before delegating to `q_from_hw`.
4. Parse `.rst/.rsql` with the existing `Hy8Results` helpers.
5. Return a `HydraulicsResult` containing the numeric answer plus the final `Hy8ResultRow`. Intermediate runs (for `q_from_hw` / `q_for_hwd`) are discarded so only the converged run surfaces to the user.

## Data Dependencies
- HY-8 executable path: default to `Hy8Executable.default_path()` but allow callers to pass an explicit `Hy8Executable` or `Path`.
- Workspace: default to a temp directory and delete when done; allow callers to keep artifacts by passing their own `Path`.
- `CulvertCrossing` needs project metadata (units, exit-loss option). When invoked from a `Hy8Project` we pass the real values; standalone calls accept optional overrides (with conservative defaults) and construct a throwaway project containing only the crossing.
- Headwater-to-diameter conversion uses the first barrel's geometry. If barrels differ (shape/span/rise) we raise `ValueError` so the caller can clarify which geometry to use.

## Proposed Interfaces

### CulvertCrossing
```python
class CulvertCrossing:
    def hw_from_q(
        self,
        q: float,
        *,
        hy8: Hy8Executable | Path | None = None,
        project: Hy8Project | None = None,
        units: UnitSystem | None = None,
        exit_loss_option: int | None = None,
        workspace: Path | None = None,
        keep_files: bool = False,
    ) -> HydraulicsResult: ...

    def q_from_hw(
        self,
        hw: float,
        *,
        q_hint: float | None = None,
        hy8: Hy8Executable | Path | None = None,
        project: Hy8Project | None = None,
        units: UnitSystem | None = None,
        exit_loss_option: int | None = None,
        workspace: Path | None = None,
        keep_files: bool = False,
    ) -> HydraulicsResult: ...

    def q_for_hwd(
        self,
        hw_d_ratio: float,
        *,
        q_hint: float | None = None,
        hy8: Hy8Executable | Path | None = None,
        project: Hy8Project | None = None,
        units: UnitSystem | None = None,
        exit_loss_option: int | None = None,
        workspace: Path | None = None,
        keep_files: bool = False,
    ) -> HydraulicsResult: ...
```
- `hw_from_q` adjusts the cloned crossing's flow definition to a single user-defined discharge, runs HY-8 once, and returns that row (no interpolation).
- `q_from_hw` seeds flows with a deterministic bracket:
  - If `q_hint` is provided we evaluate `[0, 0.9*q_hint, q_hint, 1.1*q_hint, simple_flow_calc]`.
  - `simple_flow_calc = number_of_barrels * pi * diameter^2 / 4`, where `diameter` is derived from the barrel shape.
  - Without a hint we run `[0, simple_flow_calc / 2, simple_flow_calc]`.
  - Subsequent HY-8 runs bisect the gap around the latest bracket until the headwater straddles the target; we then interpolate between the final two runs.
- `q_for_hwd` multiplies the ratio by the characteristic diameter (span for circular, rise for box) to convert into a depth, adds the invert elevation to get headwater, accepts an optional `q_hint`, and calls `q_from_hw`.

### Hy8Project
```python
class Hy8Project:
    def hw_from_q(
        self,
        q: float,
        *,
        hy8: Hy8Executable | Path | None = None,
        workspace: Path | None = None,
        keep_files: bool = False,
    ) -> OrderedDict[str, HydraulicsResult]: ...

    def q_from_hw(
        self,
        hw: float,
        *,
        q_hint: float | None = None,
        hy8: Hy8Executable | Path | None = None,
        workspace: Path | None = None,
        keep_files: bool = False,
    ) -> OrderedDict[str, HydraulicsResult]: ...

    def q_for_hwd(
        self,
        hw_d_ratio: float,
        *,
        q_hint: float | None = None,
        hy8: Hy8Executable | Path | None = None,
        workspace: Path | None = None,
        keep_files: bool = False,
    ) -> OrderedDict[str, HydraulicsResult]: ...
```
- Project methods iterate through `self.crossings` in order, calling the crossing helper with the shared executable/workspace so repeated runs reuse the same temporary folder if possible.
- Results are keyed by `crossing.name`. If two crossings share a name we append an index (e.g., `"Crossing 1 (duplicate #2)"`) to keep the dict unique.

### Supporting Structures (in `run_hy8.hydraulics`)
- `HydraulicsResult`: dataclass containing:
  - `crossing_name`
  - `requested_flow` / `requested_headwater`
  - `computed_flow` / `computed_headwater`
  - `row: Hy8ResultRow | None`
  - `workspace: Path | None` (if `keep_files=True`)
- `_ScenarioConfig`: internal helper describing the temporary project, output paths, and HY-8 arguments for the current run.
- `_SeriesView`: cached flow/headwater arrays plus source rows for interpolation (`q_from_hw`, `q_for_hwd`).
- `_FlowSearch`: helper that stores the current bracket plus bookkeeping about the HY-8 rows gathered so far (used by `q_from_hw` and `q_for_hwd`).

## Flow Search Strategy
- `simple_flow_calc = number_of_barrels * pi * diameter^2 / 4`, where `diameter` is derived from the current barrel (span for circular, rise for box). We compute this once per helper invocation.
- When a `q_hint` is provided we evaluate `[0, 0.9*q_hint, q_hint, 1.1*q_hint, simple_flow_calc]`.
- Without a hint we evaluate `[0, simple_flow_calc / 2, simple_flow_calc]`.
- After the initial runs we check whether the last two headwater values straddle the target:
  - If yes, we interpolate between those two runs and stop.
  - If no, we bisect the larger gap (favoring the side closer to `q_hint` when provided) and run HY-8 again.
- Failures (no bracket found after a fixed number of runs, non-monotonic headwaters) raise `ValueError` so callers can inspect the intermediate rows (returned via `HydraulicsResult.row` when `keep_files=True`).

## Implementation Steps
1. Update `CulvertCrossing` and `Hy8Project` with the new method signatures (raising `NotImplementedError`).
2. Extend `run_hy8.hydraulics` with `HydraulicsResult` plus placeholder factories (`prepare_scenario`, `run_hy8_and_parse`, `solve_for_headwater`, etc.), all raising `NotImplementedError` for now.
3. Once the API is reviewed, implement the workflow end-to-end, including temporary file handling and HY-8 invocation.
4. Add regression tests that mock HY-8 execution to avoid shelling out during CI.
5. Document the new helpers in `README.md` once functionality is stable.
