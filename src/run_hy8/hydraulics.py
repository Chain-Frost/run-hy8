"""Hydraulic helpers that run HY-8 scenarios on demand.

Each helper method owns the full HY-8 workflow:

1. Clone the requested `Hy8Project`/`CulvertCrossing` so we can modify flows safely.
2. Serialize the temporary project using `Hy8FileWriter`.
3. Run the HY-8 executable via `Hy8Executable`.
4. Parse the `.rst`/`.rsql` outputs into `Hy8Results`.
5. Reduce the parsed data to the flow/headwater combination requested by the caller.

Logging is routed through `loguru.logger`, which keeps the helpers lightweight
and aligns with the rest of the codebase—future contributors should follow the
same convention when expanding this module.
"""

from __future__ import annotations

import copy
import math
import shutil
import tempfile
from collections import OrderedDict
from dataclasses import dataclass, field
from pathlib import Path

from loguru import logger
from .executor import Hy8Executable
from .models import (
    CulvertBarrel,
    CulvertCrossing,
    CulvertShape,
    FlowDefinition,
    FlowMethod,
    Hy8Project,
    UnitSystem,
)
from .results import Hy8ResultRow, Hy8Results, parse_rsql, parse_rst
from .writer import Hy8FileWriter


@dataclass(slots=True)
class HydraulicsResult:
    """Structured payload returned to callers of the hydraulics helpers.

    Attributes:
        crossing_name: Name of the crossing that produced the result.
        requested_flow: Flow that the caller asked HY-8 to analyze.
        requested_headwater: Headwater elevation supplied by the caller.
        computed_flow: Flow that HY-8 reported in the final result row.
        computed_headwater: Headwater elevation reported by HY-8.
        row: The full `Hy8ResultRow` for the converged solution.
        workspace: Optional path to a workspace directory when the caller
            requested that temporary HY-8 artifacts be preserved.
    """

    crossing_name: str
    requested_flow: float | None = None
    requested_headwater: float | None = None
    computed_flow: float = float("nan")
    computed_headwater: float = float("nan")
    row: Hy8ResultRow | None = None
    workspace: Path | None = None


@dataclass(slots=True)
class _FlowSample:
    """Single HY-8 run captured during a flow search."""

    flow: float
    row: Hy8ResultRow

    @property
    def headwater(self) -> float:
        return self.row.headwater_elevation


def _flow_sample_list() -> list[_FlowSample]:
    """Return an empty list that pyright can treat as list[_FlowSample]."""

    return []


@dataclass(slots=True)
class _FlowSearch:
    """Stateful helper that brackets target headwater values."""

    target_headwater: float
    simple_flow: float
    q_hint: float | None = None
    max_runs: int = 12
    tolerance: float = 1e-4
    samples: list[_FlowSample] = field(default_factory=_flow_sample_list)

    def initial_candidates(self) -> list[float]:
        """Return the list of seed flows evaluated before adaptive bracketing."""

        base: list[float]
        if self.q_hint and self.q_hint > 0:
            base = [
                0.0,
                max(0.0, 0.9 * self.q_hint),
                max(0.0, self.q_hint),
                max(0.0, 1.1 * self.q_hint),
                max(0.0, self.simple_flow),
            ]
        else:
            half: float = self.simple_flow / 2 if self.simple_flow > 0 else 0.0
            base = [0.0, max(0.0, half), max(0.0, self.simple_flow)]
        seen: set[float] = set()
        candidates: list[float] = []
        for value in base:
            key: float = round(value, 6)
            if key in seen:
                continue
            seen.add(key)
            candidates.append(value)
        return candidates

    def record(self, flow: float, row: Hy8ResultRow) -> _FlowSample:
        """Record a single HY-8 run."""

        sample = _FlowSample(flow=flow, row=row)
        self.samples.append(sample)
        return sample

    def _delta(self, sample: _FlowSample) -> float:
        return sample.headwater - self.target_headwater

    def exact_match(self) -> _FlowSample | None:
        """Return a previously recorded sample whose headwater matches the target."""

        for sample in self.samples:
            if math.isnan(sample.headwater):
                continue
            if abs(self._delta(sample)) <= self.tolerance:
                return sample
        return None

    def bracket(self) -> tuple[_FlowSample, _FlowSample] | None:
        """Return the low/high samples that straddle the target headwater."""

        lows: list[_FlowSample] = []
        highs: list[_FlowSample] = []
        for sample in self.samples:
            if math.isnan(sample.headwater):
                continue
            delta = self._delta(sample)
            if delta <= 0:
                lows.append(sample)
            if delta >= 0:
                highs.append(sample)
        if not lows or not highs:
            return None
        low: _FlowSample = max(lows, key=lambda s: s.flow)
        high: _FlowSample = min(highs, key=lambda s: s.flow)
        if low.flow == high.flow and abs(self._delta(low)) > self.tolerance:
            return None
        return low, high

    def next_guess(self) -> float | None:
        """Return the next flow to evaluate when no bracket exists yet."""

        if len(self.samples) >= self.max_runs:
            return None
        lows: list[_FlowSample] = [s for s in self.samples if not math.isnan(s.headwater) and self._delta(s) <= 0]
        highs: list[_FlowSample] = [s for s in self.samples if not math.isnan(s.headwater) and self._delta(s) >= 0]
        if lows and highs:
            return (max(lows, key=lambda s: s.flow).flow + min(highs, key=lambda s: s.flow).flow) / 2
        if lows:
            base = max(lows, key=lambda s: s.flow).flow
            return base * 2 if base > 0 else self.simple_flow or 1.0
        if highs:
            base = min(highs, key=lambda s: s.flow).flow
            return base / 2
        return self.simple_flow or (self.q_hint or 1.0)


def _resolve_hy8_executable(hy8: Hy8Executable | Path | str | None) -> Hy8Executable:
    """Return a `Hy8Executable` instance regardless of caller input."""

    if isinstance(hy8, Hy8Executable):
        return hy8
    if hy8 is None:
        return Hy8Executable()
    return Hy8Executable(Path(hy8))


def _prepare_workspace(base: Path | None, *, keep_files: bool) -> tuple[Path, bool]:
    """Create or reuse the workspace directory for HY-8 artifacts."""

    if base is not None:
        base = Path(base)
        base.mkdir(parents=True, exist_ok=True)
        logger.debug("Reusing workspace directory %s", base)
        return base, False
    temp_dir = Path(tempfile.mkdtemp(prefix="run-hy8-"))
    logger.debug("Created temporary workspace directory %s", temp_dir)
    if keep_files:
        return temp_dir, False
    return temp_dir, True


def _cleanup_workspace(path: Path, *, should_cleanup: bool) -> None:
    """Remove a temporary workspace unless the caller opted to keep files."""

    if should_cleanup and path.exists():
        logger.debug("Removing temporary workspace %s", path)
        shutil.rmtree(path, ignore_errors=True)


def _clone_project_with_crossing(
    crossing: CulvertCrossing,
    project: Hy8Project | None,
    units: UnitSystem | None,
    exit_loss_option: int | None,
) -> tuple[Hy8Project, CulvertCrossing]:
    """Clone the crossing into a standalone project for HY-8 execution."""

    logger.debug("Cloning crossing %s for HY-8 execution", crossing.name)
    crossing_copy: CulvertCrossing = copy.deepcopy(crossing)
    if project:
        snapshot = Hy8Project(
            title=project.title,
            designer=project.designer,
            notes=project.notes,
            units=project.units,
            exit_loss_option=project.exit_loss_option,
        )
    else:
        snapshot = Hy8Project(
            title=crossing.name,
            designer="",
            notes="",
            units=units or UnitSystem.SI,
            exit_loss_option=exit_loss_option if exit_loss_option is not None else 0,
        )
    snapshot.crossings.append(crossing_copy)
    return snapshot, crossing_copy


def _write_and_run(
    project: Hy8Project,
    crossing_name: str,
    hy8_exec: Hy8Executable,
    *,
    workspace: Path,
    run_index: int,
) -> Hy8Results:
    """Write the temporary project to disk, run HY-8, and parse the outputs."""

    hy8_file: Path = workspace / f"{crossing_name}_run_{run_index:03d}.hy8"
    logger.info("Writing HY-8 project %s (iteration %s)", hy8_file, run_index)
    Hy8FileWriter(project).write(hy8_file, overwrite=True)
    logger.info("Running HY-8 for crossing %s (iteration %s)", crossing_name, run_index)
    hy8_exec.open_run_save(hy8_file)
    rst_path = hy8_file.with_suffix(".rst")
    rsql_path = hy8_file.with_suffix(".rsql")
    series = parse_rst(rst_path).get(crossing_name)
    if not series:
        raise ValueError(f"HY-8 results did not contain crossing '{crossing_name}'.")
    profiles = parse_rsql(rsql_path).get(crossing_name, [])
    return Hy8Results(series, profiles)


def _select_row_by_flow(results: Hy8Results, flow: float) -> Hy8ResultRow:
    """Return the HY-8 result row whose flow most closely matches `flow`."""

    best: Hy8ResultRow | None = None
    best_delta: float = float("inf")
    for row in results.rows:
        if math.isnan(row.flow):
            continue
        delta: float = abs(row.flow - flow)
        if delta < best_delta:
            best_delta = delta
            best = row
    if best is None:
        raise ValueError("HY-8 output did not include any valid flow rows.")
    return best


def _total_barrels(crossing: CulvertCrossing) -> int:
    """Return the number of barrels represented by the crossing."""

    total = 0
    for barrel in crossing.culverts:
        count: int = barrel.number_of_barrels if barrel.number_of_barrels > 0 else 1
        total += count
    return total if total > 0 else 1


def _characteristic_diameter(crossing: CulvertCrossing) -> float:
    """Return the characteristic diameter used for HW/D ratio calculations."""

    if not crossing.culverts:
        raise ValueError("At least one culvert barrel is required.")
    reference: CulvertBarrel = crossing.culverts[0]
    shape: CulvertShape = reference.shape
    diameter: float
    if shape is CulvertShape.CIRCLE:
        diameter = reference.span
    elif shape is CulvertShape.BOX:
        diameter = reference.rise
    else:
        raise NotImplementedError("Headwater ratio lookup is only supported for circle/box culverts.")
    if diameter <= 0:
        raise ValueError("Characteristic diameter must be greater than zero.")
    for barrel in crossing.culverts[1:]:
        if barrel.shape is not shape:
            raise ValueError("All barrels must share the same shape for headwater ratio calculations.")
    return diameter


def _simple_flow_estimate(crossing: CulvertCrossing) -> float:
    """Return a quick discharge estimate used to seed the flow search."""

    diameter: float = _characteristic_diameter(crossing=crossing)
    barrels: int = _total_barrels(crossing=crossing)
    area: float = math.pi * (diameter**2) / 4.0
    return area * barrels


def crossing_hw_from_q(
    crossing: CulvertCrossing,
    q: float,
    *,
    hy8: Hy8Executable | Path | str | None = None,
    project: Hy8Project | None = None,
    units: UnitSystem | None = None,
    exit_loss_option: int | None = None,
    workspace: Path | None = None,
    keep_files: bool = False,
) -> HydraulicsResult:
    """Run HY-8 once for a single discharge and return the resulting headwater."""

    logger.info("Computing headwater for crossing %s at flow %.4f", crossing.name, q)
    hy8_exec: Hy8Executable = _resolve_hy8_executable(hy8)
    scenario_project, scenario_crossing = _clone_project_with_crossing(
        crossing=crossing, project=project, units=units, exit_loss_option=exit_loss_option
    )
    scenario_crossing.flow = FlowDefinition(method=FlowMethod.USER_DEFINED, user_values=[q])
    workspace_path, should_cleanup = _prepare_workspace(base=workspace, keep_files=keep_files)
    try:
        results: Hy8Results = _write_and_run(
            project=scenario_project,
            crossing_name=scenario_crossing.name,
            hy8_exec=hy8_exec,
            workspace=workspace_path,
            run_index=1,
        )
        row: Hy8ResultRow = _select_row_by_flow(results=results, flow=q)
        logger.debug(
            "HY-8 returned headwater %.4f for crossing %s at flow %.4f",
            row.headwater_elevation,
            scenario_crossing.name,
            row.flow,
        )
        return HydraulicsResult(
            crossing_name=scenario_crossing.name,
            requested_flow=q,
            computed_flow=row.flow,
            computed_headwater=row.headwater_elevation,
            row=row,
            workspace=workspace_path if keep_files else None,
        )
    finally:
        _cleanup_workspace(path=workspace_path, should_cleanup=should_cleanup and not keep_files and workspace is None)


def crossing_q_from_hw(
    crossing: CulvertCrossing,
    hw: float,
    *,
    q_hint: float | None = None,
    hy8: Hy8Executable | Path | str | None = None,
    project: Hy8Project | None = None,
    units: UnitSystem | None = None,
    exit_loss_option: int | None = None,
    workspace: Path | None = None,
    keep_files: bool = False,
) -> HydraulicsResult:
    """Iteratively run HY-8 until the requested headwater is bracketed and interpolated."""

    if math.isnan(hw):
        raise ValueError("Target headwater cannot be NaN.")
    logger.info("Searching for discharge that yields HW=%.4f for crossing %s", hw, crossing.name)
    hy8_exec = _resolve_hy8_executable(hy8)
    scenario_project, scenario_crossing = _clone_project_with_crossing(crossing, project, units, exit_loss_option)
    workspace_path, should_cleanup = _prepare_workspace(workspace, keep_files=keep_files)
    try:
        simple_flow = _simple_flow_estimate(scenario_crossing)
        search = _FlowSearch(target_headwater=hw, simple_flow=simple_flow, q_hint=q_hint)
        run_count = 0
        final_row: Hy8ResultRow | None = None
        final_flow: float | None = None
        seeds = search.initial_candidates()
        for candidate in seeds:
            run_count += 1
            logger.debug("Seed flow %.4f for crossing %s (iteration %s)", candidate, crossing.name, run_count)
            scenario_crossing.flow = FlowDefinition(method=FlowMethod.USER_DEFINED, user_values=[candidate])
            results = _write_and_run(
                scenario_project,
                scenario_crossing.name,
                hy8_exec,
                workspace=workspace_path,
                run_index=run_count,
            )
            row = _select_row_by_flow(results, candidate)
            search.record(candidate, row)
            logger.debug(
                "Seed result for crossing %s: flow %.4f => headwater %.4f",
                crossing.name,
                candidate,
                row.headwater_elevation,
            )
            exact = search.exact_match()
            if exact:
                final_row = exact.row
                final_flow = exact.flow
                break
        while final_row is None:
            bracket = search.bracket()
            if bracket:
                low, high = bracket
                logger.debug(
                    "Bracket for crossing %s: low %.4f (HW %.4f) high %.4f (HW %.4f)",
                    crossing.name,
                    low.flow,
                    low.headwater,
                    high.flow,
                    high.headwater,
                )
                if abs(low.headwater - hw) <= search.tolerance:
                    final_row = low.row
                    final_flow = low.flow
                    break
                if abs(high.headwater - hw) <= search.tolerance:
                    final_row = high.row
                    final_flow = high.flow
                    break
                slope = high.headwater - low.headwater
                if slope == 0:
                    guess = (low.flow + high.flow) / 2
                else:
                    guess = low.flow + ((hw - low.headwater) / slope) * (high.flow - low.flow)
                run_count += 1
                logger.debug("Interpolated guess %.4f for crossing %s", guess, crossing.name)
                scenario_crossing.flow = FlowDefinition(method=FlowMethod.USER_DEFINED, user_values=[guess])
                results = _write_and_run(
                    scenario_project,
                    scenario_crossing.name,
                    hy8_exec,
                    workspace=workspace_path,
                    run_index=run_count,
                )
                row = _select_row_by_flow(results, guess)
                final_row = row
                final_flow = row.flow
                break
            next_guess = search.next_guess()
            if next_guess is None:
                break
            run_count += 1
            logger.debug("Bisected guess %.4f for crossing %s", next_guess, crossing.name)
            scenario_crossing.flow = FlowDefinition(method=FlowMethod.USER_DEFINED, user_values=[next_guess])
            results = _write_and_run(
                scenario_project,
                scenario_crossing.name,
                hy8_exec,
                workspace=workspace_path,
                run_index=run_count,
            )
            row = _select_row_by_flow(results, next_guess)
            search.record(next_guess, row)
            exact = search.exact_match()
            if exact:
                final_row = exact.row
                final_flow = exact.flow
                break
        if final_row is None or final_flow is None:
            raise ValueError("Unable to bracket the requested headwater.")
        logger.info(
            "Crossing %s: HW %.4f achieved at flow %.4f",
            crossing.name,
            final_row.headwater_elevation,
            final_flow,
        )
        return HydraulicsResult(
            crossing_name=scenario_crossing.name,
            requested_headwater=hw,
            computed_flow=final_flow,
            computed_headwater=final_row.headwater_elevation,
            row=final_row,
            workspace=workspace_path if keep_files else None,
        )
    finally:
        _cleanup_workspace(workspace_path, should_cleanup=should_cleanup and not keep_files and workspace is None)


def crossing_q_for_hwd(
    crossing: CulvertCrossing,
    hw_d_ratio: float,
    *,
    q_hint: float | None = None,
    hy8: Hy8Executable | Path | str | None = None,
    project: Hy8Project | None = None,
    units: UnitSystem | None = None,
    exit_loss_option: int | None = None,
    workspace: Path | None = None,
    keep_files: bool = False,
) -> HydraulicsResult:
    """Run HY-8 to find the discharge that produces the requested HW/D ratio."""
    if hw_d_ratio < 0:
        raise ValueError("Headwater-to-diameter ratio must be non-negative.")
    diameter = _characteristic_diameter(crossing)
    inlet_elevation = crossing.culverts[0].inlet_invert_elevation
    target_headwater = inlet_elevation + hw_d_ratio * diameter
    logger.info(
        "Searching for HW/D %.3f (target HW %.4f) for crossing %s",
        hw_d_ratio,
        target_headwater,
        crossing.name,
    )
    result = crossing_q_from_hw(
        crossing,
        hw=target_headwater,
        q_hint=q_hint,
        hy8=hy8,
        project=project,
        units=units,
        exit_loss_option=exit_loss_option,
        workspace=workspace,
        keep_files=keep_files,
    )
    result.requested_headwater = target_headwater
    return result


def _unique_crossing_key(name: str, counts: dict[str, int]) -> str:
    """Return a stable dictionary key when projects contain duplicate names."""
    if name not in counts:
        counts[name] = 1
        return name
    counts[name] += 1
    return f"{name} (duplicate #{counts[name]})"


def project_hw_from_q(
    project: Hy8Project,
    q: float,
    *,
    hy8: Hy8Executable | Path | str | None = None,
    workspace: Path | None = None,
    keep_files: bool = False,
) -> OrderedDict[str, HydraulicsResult]:
    """Compute headwaters for each project crossing at a fixed discharge."""
    logger.info("Running project-level headwater lookup for flow %.4f", q)
    hy8_exec: Hy8Executable = _resolve_hy8_executable(hy8)
    base_workspace, should_cleanup = _prepare_workspace(workspace, keep_files=keep_files)
    results: OrderedDict[str, HydraulicsResult] = OrderedDict()
    name_counts: dict[str, int] = {}
    try:
        for index, crossing in enumerate(project.crossings, start=1):
            crossing_workspace = base_workspace / f"crossing_{index:03d}"
            crossing_workspace.mkdir(parents=True, exist_ok=True)
            logger.debug("Project hw_from_q processing crossing %s (#%s)", crossing.name, index)
            result: HydraulicsResult = crossing.hw_from_q(
                q=q,
                hy8=hy8_exec,
                project=project,
                workspace=crossing_workspace,
                keep_files=keep_files,
            )
            key: str = _unique_crossing_key(name=crossing.name, counts=name_counts)
            results[key] = result
        return results
    finally:
        _cleanup_workspace(path=base_workspace, should_cleanup=should_cleanup and not keep_files and workspace is None)


def project_q_from_hw(
    project: Hy8Project,
    hw: float,
    *,
    q_hint: float | None = None,
    hy8: Hy8Executable | Path | str | None = None,
    workspace: Path | None = None,
    keep_files: bool = False,
) -> OrderedDict[str, HydraulicsResult]:
    """Compute discharges for each project crossing that reach the target headwater."""
    logger.info("Running project-level discharge search for HW=%.4f", hw)
    hy8_exec: Hy8Executable = _resolve_hy8_executable(hy8)
    base_workspace, should_cleanup = _prepare_workspace(workspace, keep_files=keep_files)
    results: OrderedDict[str, HydraulicsResult] = OrderedDict()
    name_counts: dict[str, int] = {}
    try:
        for index, crossing in enumerate(project.crossings, start=1):
            crossing_workspace = base_workspace / f"crossing_{index:03d}"
            crossing_workspace.mkdir(parents=True, exist_ok=True)
            logger.debug("Project q_from_hw processing crossing %s (#%s)", crossing.name, index)
            result: HydraulicsResult = crossing.q_from_hw(
                hw=hw,
                q_hint=q_hint,
                hy8=hy8_exec,
                project=project,
                workspace=crossing_workspace,
                keep_files=keep_files,
            )
            key: str = _unique_crossing_key(name=crossing.name, counts=name_counts)
            results[key] = result
        return results
    finally:
        _cleanup_workspace(path=base_workspace, should_cleanup=should_cleanup and not keep_files and workspace is None)


def project_q_for_hwd(
    project: Hy8Project,
    hw_d_ratio: float,
    *,
    q_hint: float | None = None,
    hy8: Hy8Executable | Path | str | None = None,
    workspace: Path | None = None,
    keep_files: bool = False,
) -> OrderedDict[str, HydraulicsResult]:
    """Compute discharges for each project crossing that satisfy the HW/D ratio."""
    logger.info("Running project-level discharge search for HW/D ratio %.3f", hw_d_ratio)
    hy8_exec: Hy8Executable = _resolve_hy8_executable(hy8)
    base_workspace, should_cleanup = _prepare_workspace(workspace, keep_files=keep_files)
    results: OrderedDict[str, HydraulicsResult] = OrderedDict()
    name_counts: dict[str, int] = {}
    try:
        for index, crossing in enumerate(project.crossings, start=1):
            crossing_workspace = base_workspace / f"crossing_{index:03d}"
            crossing_workspace.mkdir(parents=True, exist_ok=True)
            logger.debug("Project q_for_hwd processing crossing %s (#%s)", crossing.name, index)
            result: HydraulicsResult = crossing.q_for_hwd(
                hw_d_ratio=hw_d_ratio,
                q_hint=q_hint,
                hy8=hy8_exec,
                project=project,
                workspace=crossing_workspace,
                keep_files=keep_files,
            )
            key: str = _unique_crossing_key(name=crossing.name, counts=name_counts)
            results[key] = result
        return results
    finally:
        _cleanup_workspace(path=base_workspace, should_cleanup=should_cleanup and not keep_files and workspace is None)


__all__: list[str] = [
    "HydraulicsResult",
]
