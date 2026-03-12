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

from run_hy8.results import FlowProfile, Hy8Series

from .classes_references import UnitSystem
from .executor import Hy8Executable
from .models import (
    CulvertBarrel,
    CulvertCrossing,
    FlowDefinition,
    Hy8Project,
)
from .type_helpers import CulvertShape, FlowMethod
from .results import Hy8ResultRow, Hy8Results, parse_rsql, parse_rst
from .writer import Hy8FileWriter

MINIMUM_SEED_FLOW: float = 0.05
SEED_SCALE_FACTORS: tuple[float, ...] = (0.1, 0.25, 0.5, 1.0, 1.5, 2.0)
STEP_FRACTION: float = 0.25
BRACKET_SUBDIVISIONS: int = 5
SEED_BATCH_SIZE: int = 6
FLOW_SEARCH_MAX_RUNS: int = 20
EXPANSION_FACTOR: float = 2.0


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


class FlowSearchError(RuntimeError):
    """Raised when the headwater search cannot converge on a discharge."""

    def __init__(self, message: str, *, best_sample: _FlowSample | None = None, target_headwater: float | None = None):
        self.best_sample = best_sample
        self.target_headwater = target_headwater
        super().__init__(message)


def _flow_sample_list() -> list[_FlowSample]:
    """Return an empty list that pyright can treat as list[_FlowSample]."""

    return []


@dataclass(slots=True)
class _FlowSearch:
    """Stateful helper that brackets target headwater values."""

    target_headwater: float
    simple_flow: float
    q_hint: float | None = None
    max_runs: int = FLOW_SEARCH_MAX_RUNS
    tolerance: float = 1e-2
    samples: list[_FlowSample] = field(default_factory=_flow_sample_list)

    def _baseline_flow(self) -> float:
        """Return the most reasonable flow estimate available."""

        if self.q_hint and self.q_hint > 0:
            return self.q_hint
        if self.simple_flow and self.simple_flow > 0:
            return self.simple_flow
        return 1.0

    def _normalize_seed(self, value: float) -> float:
        return max(MINIMUM_SEED_FLOW, value)

    def initial_candidates(self) -> list[float]:
        """Return the list of seed flows evaluated before adaptive bracketing."""

        seeds: set[float] = {MINIMUM_SEED_FLOW}
        baseline: float = self._baseline_flow()
        for factor in SEED_SCALE_FACTORS:
            seeds.add(self._normalize_seed(value=baseline * factor))
        if self.simple_flow and self.simple_flow > 0:
            for factor in (0.5, 1.0):
                seeds.add(self._normalize_seed(value=self.simple_flow * factor))
        if self.q_hint and self.q_hint > 0:
            seeds.add(self._normalize_seed(value=self.q_hint))
        return sorted(seeds)

    def _has_flow(self, candidate: float, *, epsilon: float = 1e-8) -> bool:
        return any(abs(sample.flow - candidate) <= epsilon for sample in self.samples)

    def subdivision_candidates(self, low: _FlowSample, high: _FlowSample) -> list[float]:
        """Return interior flows for evaluating an existing bracket."""

        if BRACKET_SUBDIVISIONS <= 1:
            return []
        span: float = high.flow - low.flow
        if span <= 0:
            return []
        step: float = span / BRACKET_SUBDIVISIONS
        candidates: list[float] = []
        for index in range(1, BRACKET_SUBDIVISIONS):
            guess: float = self._normalize_seed(value=low.flow + step * index)
            if not self._has_flow(candidate=guess):
                candidates.append(guess)
        if not candidates:
            midpoint: float = self._normalize_seed(value=(low.flow + high.flow) / 2)
            if not self._has_flow(candidate=midpoint):
                candidates.append(midpoint)
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
            if abs(self._delta(sample=sample)) <= self.tolerance:
                return sample
        return None

    def bracket(self) -> tuple[_FlowSample, _FlowSample] | None:
        """Return the low/high samples that straddle the target headwater."""

        ordered: list[_FlowSample] = sorted(
            (sample for sample in self.samples if not math.isnan(sample.headwater)),
            key=lambda sample: sample.flow,
        )
        best_pair: tuple[_FlowSample, _FlowSample] | None = None
        best_span: float = float("inf")
        for low, high in zip(ordered, ordered[1:]):
            low_delta: float = self._delta(sample=low)
            high_delta: float = self._delta(sample=high)
            if abs(low_delta) <= self.tolerance or abs(high_delta) <= self.tolerance:
                continue
            if low_delta == 0 or high_delta == 0 or low_delta * high_delta > 0:
                continue
            span: float = high.flow - low.flow
            if span <= 0:
                continue
            if span < best_span:
                best_span = span
                best_pair = (low, high)
        return best_pair

    def next_guess(self) -> float | None:
        """Return the next flow to evaluate when no bracket exists yet."""

        if len(self.samples) >= self.max_runs:
            return None
        lows: list[_FlowSample] = [s for s in self.samples if not math.isnan(s.headwater) and self._delta(s) <= 0]
        highs: list[_FlowSample] = [s for s in self.samples if not math.isnan(s.headwater) and self._delta(s) >= 0]
        if lows and highs:
            return (max(lows, key=lambda s: s.flow).flow + min(highs, key=lambda s: s.flow).flow) / 2
        if lows:
            base: float = max(lows, key=lambda s: s.flow).flow
            return max(base + MINIMUM_SEED_FLOW, base * EXPANSION_FACTOR)
        if highs:
            base = min(highs, key=lambda s: s.flow).flow
            return max(MINIMUM_SEED_FLOW, base / EXPANSION_FACTOR)
        return self._baseline_flow()

    def closest_sample(self) -> _FlowSample | None:
        """Return the recorded sample whose headwater is nearest to the target."""

        candidates = [sample for sample in self.samples if not math.isnan(sample.headwater)]
        if not candidates:
            return None
        return min(candidates, key=lambda sample: abs(self._delta(sample=sample)))


def _resolve_hy8_executable(hy8: Hy8Executable | Path | str | None) -> Hy8Executable:
    """Return a `Hy8Executable` instance regardless of caller input."""

    if isinstance(hy8, Hy8Executable):
        return hy8
    if hy8 is None:
        return Hy8Executable()
    return Hy8Executable(exe_path=Path(hy8))


def _prepare_workspace(base: Path | None, *, keep_files: bool) -> tuple[Path, bool]:
    """Create or reuse the workspace directory for HY-8 artifacts."""

    if base is not None:
        base = Path(base)
        base.mkdir(parents=True, exist_ok=True)
        logger.debug("Reusing workspace directory {path}", path=base)
        return base, False
    temp_dir = Path(tempfile.mkdtemp(prefix="run-hy8-"))
    logger.debug("Created temporary workspace directory {path}", path=temp_dir)
    if keep_files:
        return temp_dir, False
    return temp_dir, True


def _cleanup_workspace(path: Path, *, should_cleanup: bool) -> None:
    """Remove a temporary workspace unless the caller opted to keep files."""

    if should_cleanup and path.exists():
        logger.debug("Removing temporary workspace {path}", path=path)
        shutil.rmtree(path, ignore_errors=True)


def _clone_project_with_crossing(
    crossing: CulvertCrossing,
    project: Hy8Project | None,
    units: UnitSystem | None,
    exit_loss_option: int | None,
) -> tuple[Hy8Project, CulvertCrossing]:
    """Clone the crossing into a standalone project for HY-8 execution."""

    logger.debug("Cloning crossing {name} for HY-8 execution", name=crossing.name)
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
    scenario: str | None = None,
) -> Hy8Results:
    """Write the temporary project to disk, run HY-8, and parse the outputs."""

    scenario_suffix: str = f"_{scenario}" if scenario else ""
    hy8_file: Path = workspace / f"{crossing_name}{scenario_suffix}_run_{run_index:03d}.hy8"
    logger.info(
        "Writing HY-8 project {file} (iteration {iteration})",
        file=hy8_file,
        iteration=run_index,
    )
    Hy8FileWriter(project=project).write(output_path=hy8_file, overwrite=True)
    logger.info(
        "Running HY-8 for crossing {crossing} (iteration {iteration})",
        crossing=crossing_name,
        iteration=run_index,
    )
    hy8_exec.open_run_save(hy8_file=hy8_file)
    rst_path: Path = hy8_file.with_suffix(suffix=".rst")
    rsql_path: Path = hy8_file.with_suffix(suffix=".rsql")
    series: Hy8Series | None = parse_rst(path=rst_path).get(crossing_name)
    if not series:
        raise ValueError(f"HY-8 results did not contain crossing '{crossing_name}'.")
    profiles: list[FlowProfile] = parse_rsql(path=rsql_path).get(crossing_name, [])
    return Hy8Results(entry=series, profiles=profiles)


def _select_row_by_flow(results: Hy8Results, flow: float) -> Hy8ResultRow:
    """Return the HY-8 result row whose flow most closely matches `flow`."""

    best: Hy8ResultRow | None = None
    logger.debug(results)
    best_delta: float = float("inf")
    for row in results.rows:
        if math.isnan(row.flow):
            continue
        delta: float = abs(row.flow - flow)
        if delta < best_delta:
            best_delta = delta
            best = row
    if best is None:
        logger.error(f"{flow}, {results}")
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

    logger.info("Computing headwater for crossing {name} at flow {flow:.4f}", name=crossing.name, flow=q)
    hy8_exec: Hy8Executable = _resolve_hy8_executable(hy8=hy8)
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
            scenario="hw_from_q",
        )
        row: Hy8ResultRow = _select_row_by_flow(results=results, flow=q)
        logger.debug(
            "HY-8 returned headwater {headwater:.4f} for crossing {name} at flow {flow:.4f}",
            headwater=row.headwater_elevation,
            name=scenario_crossing.name,
            flow=row.flow,
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
    """Solve for the discharge that produces the requested headwater using adaptive HY-8 runs.

    Strategy:
    1. Evaluate a curated list of seed flows (near hints/geometry) to quickly span the solution space.
    2. As soon as a bracket (sample below HW and sample above HW) exists, subdivide that bracket so that
       several HY-8 runs are issued per iteration. Sampling the bracket densely is cheaper than bouncing
       between Python and HY-8 many times.
    3. Fall back to linear interpolation within the latest bracket once it has been densely sampled.
    """

    if math.isnan(hw):
        raise ValueError("Target headwater cannot be NaN.")
    logger.info(
        "Searching for discharge that yields HW={headwater:.4f} for crossing {name}",
        headwater=hw,
        name=crossing.name,
    )
    hy8_exec: Hy8Executable = _resolve_hy8_executable(hy8=hy8)
    scenario_project, scenario_crossing = _clone_project_with_crossing(
        crossing=crossing, project=project, units=units, exit_loss_option=exit_loss_option
    )
    workspace_path, should_cleanup = _prepare_workspace(base=workspace, keep_files=keep_files)
    try:
        simple_flow: float = _simple_flow_estimate(crossing=scenario_crossing)
        search = _FlowSearch(target_headwater=hw, simple_flow=simple_flow, q_hint=q_hint)
        run_count = 0
        final_row: Hy8ResultRow | None = None
        final_flow: float | None = None

        def finalize_if_close(sample: _FlowSample | None) -> bool:
            nonlocal final_row, final_flow
            if sample is None:
                return False
            if abs(sample.headwater - hw) <= search.tolerance:
                final_row = sample.row
                final_flow = sample.flow
                return True
            return False

        def run_flow_batch(flows: list[float], *, label: str) -> list[_FlowSample]:
            nonlocal run_count
            if not flows:
                return []
            run_count += 1
            logger.debug(
                "{label} batch [{flows}] for crossing {name} (iteration {iteration})",
                label=label,
                flows=", ".join(f"{value:.4f}" for value in flows),
                name=crossing.name,
                iteration=run_count,
            )
            definition = FlowDefinition(method=FlowMethod.USER_DEFINED)
            for flow_value in flows:
                definition.add_user_flow(value=flow_value)
            scenario_crossing.flow = definition
            results: Hy8Results = _write_and_run(
                project=scenario_project,
                crossing_name=scenario_crossing.name,
                hy8_exec=hy8_exec,
                workspace=workspace_path,
                run_index=run_count,
                scenario="q_from_hw",
            )
            samples: list[_FlowSample] = []
            for flow_value in flows:
                row: Hy8ResultRow = _select_row_by_flow(results=results, flow=flow_value)
                sample: _FlowSample = search.record(flow=flow_value, row=row)
                logger.debug(
                    "{label} result for crossing {name}: flow {flow:.4f} => headwater {headwater:.4f}",
                    label=label,
                    name=crossing.name,
                    flow=sample.flow,
                    headwater=sample.headwater,
                )
                samples.append(sample)
            return samples

        seeds: list[float] = search.initial_candidates()
        for offset in range(0, len(seeds), SEED_BATCH_SIZE):
            seed_batch: list[float] = seeds[offset : offset + SEED_BATCH_SIZE]
            samples = run_flow_batch(flows=seed_batch, label="Seed")
            for sample in samples:
                if finalize_if_close(sample=sample):
                    break
            if final_row:
                break
            if search.bracket():
                break
        while final_row is None:
            bracket: tuple[_FlowSample, _FlowSample] | None = search.bracket()
            if bracket:
                low, high = bracket
                if finalize_if_close(sample=low) or finalize_if_close(sample=high):
                    break
                logger.debug(
                    "Bracket for crossing {name}: low {low_flow:.4f} (HW {low_hw:.4f}) high {high_flow:.4f} (HW {high_hw:.4f})",
                    name=crossing.name,
                    low_flow=low.flow,
                    low_hw=low.headwater,
                    high_flow=high.flow,
                    high_hw=high.headwater,
                )
                subdivision_flows: list[float] = search.subdivision_candidates(low=low, high=high)
                if subdivision_flows:
                    samples = run_flow_batch(flows=subdivision_flows, label="Subdivision")
                    matched = False
                    for sample in samples:
                        if finalize_if_close(sample=sample):
                            matched = True
                            break
                    if matched:
                        break
                if final_row:
                    break
                bracket = search.bracket()
                if not bracket:
                    continue
                low, high = bracket
                if finalize_if_close(sample=low) or finalize_if_close(sample=high):
                    break
                slope: float = high.headwater - low.headwater
                if slope == 0:
                    guess: float = (low.flow + high.flow) / 2
                else:
                    guess = low.flow + ((hw - low.headwater) / slope) * (high.flow - low.flow)
                samples: list[_FlowSample] = run_flow_batch(flows=[guess], label="Interpolation")
                if samples:
                    matched = False
                    for sample in samples:
                        if finalize_if_close(sample=sample):
                            matched = True
                            break
                    if matched:
                        break
                if len(search.samples) >= search.max_runs:
                    break
                continue
            next_guess: float | None = search.next_guess()
            if next_guess is None:
                break
            samples = run_flow_batch(flows=[next_guess], label="Bisection")
            if not samples:
                break
            exact: _FlowSample | None = search.exact_match()
            if exact:
                final_row = exact.row
                final_flow = exact.flow
                break
        if final_row is None or final_flow is None:
            closest = search.closest_sample()
            message = "Unable to bracket the requested headwater."
            if closest:
                message += (
                    f" Closest sample flow {closest.flow:.4f} => HW {closest.headwater:.4f} "
                    f"(target {hw:.4f})."
                )
            raise FlowSearchError(message, best_sample=closest, target_headwater=hw)
        logger.info(
            "Crossing {name}: HW {headwater:.4f} achieved at flow {flow:.4f}",
            name=crossing.name,
            headwater=final_row.headwater_elevation,
            flow=final_flow,
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
        _cleanup_workspace(path=workspace_path, should_cleanup=should_cleanup and not keep_files and workspace is None)


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
    diameter: float = _characteristic_diameter(crossing=crossing)
    inlet_elevation: float = crossing.culverts[0].inlet_invert_elevation
    target_headwater: float = inlet_elevation + hw_d_ratio * diameter
    logger.info(
        "Searching for HW/D {ratio:.3f} (target HW {headwater:.4f}) for crossing {name}",
        ratio=hw_d_ratio,
        headwater=target_headwater,
        name=crossing.name,
    )
    result: HydraulicsResult = crossing_q_from_hw(
        crossing=crossing,
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
    logger.info("Running project-level headwater lookup for flow {flow:.4f}", flow=q)
    hy8_exec: Hy8Executable = _resolve_hy8_executable(hy8)
    base_workspace, should_cleanup = _prepare_workspace(workspace, keep_files=keep_files)
    results: OrderedDict[str, HydraulicsResult] = OrderedDict()
    name_counts: dict[str, int] = {}
    try:
        for index, crossing in enumerate(project.crossings, start=1):
            crossing_workspace: Path = base_workspace / f"crossing_{index:03d}"
            crossing_workspace.mkdir(parents=True, exist_ok=True)
            logger.debug("Project hw_from_q processing crossing {name} (#{index})", name=crossing.name, index=index)
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
    logger.info("Running project-level discharge search for HW={headwater:.4f}", headwater=hw)
    hy8_exec: Hy8Executable = _resolve_hy8_executable(hy8=hy8)
    base_workspace, should_cleanup = _prepare_workspace(base=workspace, keep_files=keep_files)
    results: OrderedDict[str, HydraulicsResult] = OrderedDict()
    name_counts: dict[str, int] = {}
    try:
        for index, crossing in enumerate(project.crossings, start=1):
            crossing_workspace: Path = base_workspace / f"crossing_{index:03d}"
            crossing_workspace.mkdir(parents=True, exist_ok=True)
            logger.debug("Project q_from_hw processing crossing {name} (#{index})", name=crossing.name, index=index)
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
    logger.info("Running project-level discharge search for HW/D ratio {ratio:.3f}", ratio=hw_d_ratio)
    hy8_exec: Hy8Executable = _resolve_hy8_executable(hy8=hy8)
    base_workspace, should_cleanup = _prepare_workspace(base=workspace, keep_files=keep_files)
    results: OrderedDict[str, HydraulicsResult] = OrderedDict()
    name_counts: dict[str, int] = {}
    try:
        for index, crossing in enumerate(project.crossings, start=1):
            crossing_workspace: Path = base_workspace / f"crossing_{index:03d}"
            crossing_workspace.mkdir(parents=True, exist_ok=True)
            logger.debug("Project q_for_hwd processing crossing {name} (#{index})", name=crossing.name, index=index)
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
