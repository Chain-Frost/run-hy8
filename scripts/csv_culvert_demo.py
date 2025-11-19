"""Evaluate culvert crossings from the CSV list using HY-8."""

from __future__ import annotations

import csv
import sys
from dataclasses import dataclass
from pathlib import Path


ROOT: Path = Path(__file__).resolve().parent.parent
SRC_ROOT: Path = ROOT / "src"
for candidate in (ROOT, SRC_ROOT):
    candidate_str = str(candidate)
    if candidate_str not in sys.path:
        sys.path.insert(0, candidate_str)

from run_hy8.models import RoadwayProfile
from ..src.run_hy8.hydraulics import HydraulicsResult
from ..src.run_hy8.classes_references import UnitSystem
from ..src.run_hy8.models import (
    CulvertBarrel,
    CulvertCrossing,
    CulvertMaterial,
    CulvertShape,
    FlowDefinition,
    FlowMethod,
    Hy8Project,
    InletEdgeType,
    InletType,
    RoadwayProfile,
)

DEFAULT_CSV: Path = Path(__file__).resolve().parent / "culvert-list.csv"


@dataclass(slots=True)
class CrossingInputs:
    """Geometry inputs shared across all rows."""

    inlet_invert: float = 0.15
    outlet_invert: float = 0.0
    length: float = 30.0
    roadway_elevation: float = 20.0
    roadway_width: float = 10.0
    tailwater_elevation: float = 0.0


# Hard-coded configuration; edit these to suit each run.
CSV_PATH: Path = DEFAULT_CSV
CROSSING_NAME: str | None = None
HY8_EXE: str | None = None
KEEP_WORKSPACE: bool = False
INLET_INVERT = 0.15
OUTLET_INVERT = 0.0
BARREL_LENGTH = 30.0
ROADWAY_ELEVATION = 20.0
ROADWAY_WIDTH = 10.0
TAILWATER = 0.0


def load_rows(csv_path: Path) -> list[dict[str, str]]:
    if not csv_path.exists():
        raise FileNotFoundError(f"Culvert CSV not found: {csv_path}")
    with csv_path.open(newline="", encoding="utf-8-sig") as handle:
        reader: csv.DictReader[str] = csv.DictReader(handle)
        return [row for row in reader if row.get("Crossing")]


def select_row(rows: list[dict[str, str]], name: str | None) -> dict[str, str]:
    if name:
        for row in rows:
            if row["Crossing"].strip() == name:
                return row
        raise ValueError(f"Crossing '{name}' not found in CSV.")
    for row in rows:
        try:
            value = float(row["Adopted Flow"])
        except (KeyError, TypeError, ValueError):
            continue
        if value > 0:
            return row
    raise ValueError("No rows with a positive adopted flow were found.")


def build_crossing(
    row: dict[str, str],
    inputs: CrossingInputs,
    flow_value: float,
) -> tuple[Hy8Project, CulvertCrossing, float]:
    crossing_name: str = row["Crossing"].strip()
    if flow_value <= 0:
        raise ValueError(f"Crossing '{crossing_name}' has a non-positive flow ({flow_value}).")
    barrels = int(float(row["Barrels"]))
    diameter = float(row["Diameter (m)"])

    project = Hy8Project(title=f"CSV demo - {crossing_name}", units=UnitSystem.SI, exit_loss_option=0)
    crossing: CulvertCrossing = CulvertCrossing(name=crossing_name)
    project.crossings.append(crossing)

    flow_def = FlowDefinition(method=FlowMethod.USER_DEFINED, user_values=[flow_value])
    crossing.flow = flow_def
    crossing.tailwater.set_constant(elevation=inputs.tailwater_elevation, invert=inputs.tailwater_elevation)
    roadway: RoadwayProfile = crossing.roadway
    roadway.width = inputs.roadway_width
    roadway.stations = [0.0, inputs.roadway_width]
    roadway.elevations = [inputs.roadway_elevation, inputs.roadway_elevation]

    barrel = CulvertBarrel(
        name=f"{crossing_name} Barrel",
        span=diameter,
        rise=diameter,
        shape=CulvertShape.CIRCLE,
        material=CulvertMaterial.CORRUGATED_STEEL,
        number_of_barrels=barrels,
        inlet_invert_station=0.0,
        inlet_invert_elevation=inputs.inlet_invert,
        outlet_invert_station=inputs.length,
        outlet_invert_elevation=inputs.outlet_invert,
        inlet_type=InletType.STRAIGHT,
        inlet_edge_type=InletEdgeType.THIN_EDGE_PROJECTING,
    )
    barrel.manning_n_top = 0.024
    barrel.manning_n_bottom = 0.024
    crossing.culverts.clear()
    crossing.culverts.append(barrel)

    errors: list[str] = crossing.validate()
    if errors:
        joined: str = "; ".join(errors)
        raise ValueError(f"Validation errors for '{crossing_name}': {joined}")
    return project, crossing, diameter


def hw_from_q(
    project: Hy8Project,
    crossing: CulvertCrossing,
    flow: float,
    hy8: Path | None,
    *,
    keep_files: bool,
) -> HydraulicsResult:
    return crossing.hw_from_q(q=flow, hy8=hy8, project=project, keep_files=keep_files)


def solve_headwater_with_q_from_hw(
    project: Hy8Project,
    crossing: CulvertCrossing,
    flow: float,
    *,
    hy8: Path | None,
    bounds: tuple[float, float],
    q_hint: float,
    keep_files: bool,
    iterations: int = 12,
    tolerance: float = 1e-3,
) -> HydraulicsResult:
    lower_hw, upper_hw = bounds
    if not upper_hw > lower_hw:
        raise ValueError("Upper headwater bound must exceed the inlet invert.")

    def run(hw: float) -> HydraulicsResult:
        return crossing.q_from_hw(hw=hw, q_hint=q_hint, hy8=hy8, project=project, keep_files=keep_files)

    low_result: HydraulicsResult = run(hw=lower_hw)
    if flow <= low_result.computed_flow + tolerance:
        return low_result

    high_result: HydraulicsResult = run(hw=upper_hw)
    if high_result.computed_flow + tolerance < flow:
        raise ValueError(
            f"Target flow {flow:.4f} m^3/s exceeds the capacity before overtopping "
            f"(max flow {high_result.computed_flow:.4f} m^3/s at HW {upper_hw:.3f} m)."
        )

    best_result: HydraulicsResult = high_result
    hw_min: float = lower_hw
    hw_max: float = upper_hw
    for _ in range(iterations):
        mid_hw: float = 0.5 * (hw_min + hw_max)
        result: HydraulicsResult = run(hw=mid_hw)
        best_result = result
        delta: float = result.computed_flow - flow
        if abs(delta) <= tolerance:
            break
        if delta < 0:
            hw_min = mid_hw
        else:
            hw_max = mid_hw
    return best_result


def compute_metrics(result: HydraulicsResult, diameter: float, inlet_invert: float) -> tuple[float, float, float]:
    hw_level: float = result.computed_headwater
    hw_ratio: float = (hw_level - inlet_invert) / diameter if diameter else float("nan")
    velocity: float = result.row.velocity if result.row else float("nan")
    return hw_level, hw_ratio, velocity


def describe(result: HydraulicsResult, hw_ratio: float, velocity: float) -> None:
    print(f"  Computed flow (m^3/s): {result.computed_flow:.4f}")
    print(f"  Headwater elevation (m): {result.computed_headwater:.4f}")
    print(f"  HW:D ratio: {hw_ratio:.4f}")
    print(f"  Outlet velocity (m/s): {velocity:.4f}")
    if result.row and result.row.flow_type:
        print(f"  Flow type: {result.row.flow_type}")
    if result.row and result.row.overtopping:
        print("  Warning: HY-8 indicates overtopping at this flow.")


def main() -> None:
    inputs = CrossingInputs(
        inlet_invert=INLET_INVERT,
        outlet_invert=OUTLET_INVERT,
        length=BARREL_LENGTH,
        roadway_elevation=ROADWAY_ELEVATION,
        roadway_width=ROADWAY_WIDTH,
        tailwater_elevation=TAILWATER,
    )

    rows: list[dict[str, str]] = load_rows(csv_path=CSV_PATH)
    row: dict[str, str] = select_row(rows=rows, name=CROSSING_NAME)

    flow_value = float(row["Adopted Flow"])
    if flow_value <= 0:
        raise SystemExit(f"Crossing '{row['Crossing']}' has a non-positive flow ({flow_value}).")

    project, crossing, diameter = build_crossing(row, inputs, flow_value)
    hy8_path: Path | None = Path(HY8_EXE) if HY8_EXE else None

    print(f"Crossing: {crossing.name}")
    print(f"  Adopted flow (m^3/s): {flow_value:.4f}")

    hw_result: HydraulicsResult = hw_from_q(
        project=project, crossing=crossing, flow=flow_value, hy8=hy8_path, keep_files=KEEP_WORKSPACE
    )
    hw_level, hw_ratio, velocity = compute_metrics(
        result=hw_result, diameter=diameter, inlet_invert=inputs.inlet_invert
    )
    describe(result=hw_result, hw_ratio=hw_ratio, velocity=velocity)

    backcheck: HydraulicsResult = crossing.q_from_hw(
        hw=hw_level,
        q_hint=flow_value,
        hy8=hy8_path,
        project=project,
        keep_files=True,
    )
    flow_error: float = abs(backcheck.computed_flow - flow_value)
    print(f"  q_from_hw back-check (m^3/s): {backcheck.computed_flow:.4f} (|error|={flow_error:.4f})")
    if KEEP_WORKSPACE:
        if hw_result.workspace:
            print(f"  hw_from_q workspace kept at: {hw_result.workspace}")
        if backcheck.workspace:
            print(f"  q_from_hw workspace kept at: {backcheck.workspace}")


if __name__ == "__main__":
    main()
