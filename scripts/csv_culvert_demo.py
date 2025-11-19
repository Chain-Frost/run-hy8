"""Evaluate culvert crossings from the CSV list using HY-8."""

from __future__ import annotations

import csv
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

ROOT_PATH: Path = Path(__file__).resolve().parent.parent
SRC_PATH: Path = ROOT_PATH / "src"
src_str: str = str(SRC_PATH)
if src_str not in sys.path:
    sys.path.insert(0, src_str)

from run_hy8.hydraulics import HydraulicsResult
from run_hy8.classes_references import UnitSystem
from run_hy8.models import (
    CulvertBarrel,
    CulvertCrossing,
    FlowDefinition,
    Hy8Project,
    RoadwayProfile,
)
from run_hy8.type_helpers import (
    CulvertMaterial,
    CulvertShape,
    InletEdgeType,
    InletType,
    FlowMethod,
)

DEFAULT_CSV: Path = Path(__file__).resolve().parent / "culvert-list.csv"
# Hard-coded configuration; edit these to suit each run.
CSV_PATH: Path = DEFAULT_CSV
CROSSING_NAME: str | None = None
HY8_EXE: str | None = None
KEEP_WORKSPACE: bool = True
WORKSPACE_PATH: Path = Path("C:/Temp/hy8")
INLET_INVERT = 0.15
OUTLET_INVERT = 0.0
BARREL_LENGTH = 30.0
ROADWAY_ELEVATION = 20.0
ROADWAY_WIDTH = 10.0
TAILWATER = 0.0

RESULTS_OUTPUT: Path = Path(__file__).resolve().parent / "culvert-results.csv"
RESULT_FIELDNAMES: list[str] = [
    "Crossing",
    "Adopted Flow (m^3/s)",
    "Barrels",
    "Diameter (m)",
    "Barrel Shape",
    "Barrel Material",
    "Inlet Type",
    "Inlet Edge Type",
    "Span (m)",
    "Rise (m)",
    "Barrel Length (m)",
    "Inlet Invert Elev (m)",
    "Outlet Invert Elev (m)",
    "Roadway Width (m)",
    "Roadway Elevation (m)",
    "Tailwater Elevation (m)",
    "Status",
    "Error Message",
    "Computed Flow (m^3/s)",
    "Headwater Elevation (m)",
    "HW:D ratio",
    "Outlet Velocity (m/s)",
    "Flow Type",
    "Overtopping",
    "q_from_hw (m^3/s)",
    "Flow Error (m^3/s)",
    "hw_from_q Workspace",
    "q_from_hw Workspace",
]


@dataclass(slots=True)
class CrossingInputs:
    """Geometry inputs shared across all rows."""

    inlet_invert: float = 0.15
    outlet_invert: float = 0.0
    length: float = 30.0
    roadway_elevation: float = 20.0
    roadway_width: float = 10.0
    tailwater_elevation: float = 0.0


@dataclass(slots=True)
class CrossingOutcome:
    crossing: str
    adopted_flow: str
    barrels: str
    diameter: str
    barrel_shape: str | None
    barrel_material: str | None
    inlet_type: str | None
    inlet_edge_type: str | None
    span: float | None
    rise: float | None
    barrel_length: float | None
    inlet_invert_elev: float | None
    outlet_invert_elev: float | None
    roadway_width: float | None
    roadway_elevation: float | None
    tailwater_elevation: float | None
    status: str
    error_message: str | None
    computed_flow: float | None
    headwater: float | None
    headwater_ratio: float | None
    velocity: float | None
    flow_type: str | None
    overtopping: bool | None
    backcheck_flow: float | None
    flow_error: float | None
    hw_workspace: Path | None
    q_workspace: Path | None

    @staticmethod
    def _format(value: float | None) -> str:
        return "" if value is None else f"{value:.4f}"

    def to_row(self) -> dict[str, str]:
        return {
            "Crossing": self.crossing,
            "Adopted Flow (m^3/s)": self.adopted_flow,
            "Barrels": self.barrels,
            "Diameter (m)": self.diameter,
            "Barrel Shape": self.barrel_shape or "",
            "Barrel Material": self.barrel_material or "",
            "Inlet Type": self.inlet_type or "",
            "Inlet Edge Type": self.inlet_edge_type or "",
            "Span (m)": self._format(self.span),
            "Rise (m)": self._format(self.rise),
            "Barrel Length (m)": self._format(self.barrel_length),
            "Inlet Invert Elev (m)": self._format(self.inlet_invert_elev),
            "Outlet Invert Elev (m)": self._format(self.outlet_invert_elev),
            "Roadway Width (m)": self._format(self.roadway_width),
            "Roadway Elevation (m)": self._format(self.roadway_elevation),
            "Tailwater Elevation (m)": self._format(self.tailwater_elevation),
            "Status": self.status,
            "Error Message": self.error_message or "",
            "Computed Flow (m^3/s)": self._format(self.computed_flow),
            "Headwater Elevation (m)": self._format(self.headwater),
            "HW:D ratio": self._format(self.headwater_ratio),
            "Outlet Velocity (m/s)": self._format(self.velocity),
            "Flow Type": self.flow_type or "",
            "Overtopping": ("Yes" if self.overtopping else ("No" if self.overtopping is not None else "")),
            "q_from_hw (m^3/s)": self._format(self.backcheck_flow),
            "Flow Error (m^3/s)": self._format(self.flow_error),
            "hw_from_q Workspace": str(self.hw_workspace) if self.hw_workspace else "",
            "q_from_hw Workspace": str(self.q_workspace) if self.q_workspace else "",
        }


def load_rows(csv_path: Path) -> list[dict[str, str]]:
    if not csv_path.exists():
        raise FileNotFoundError(f"Culvert CSV not found: {csv_path}")
    with csv_path.open(newline="", encoding="utf-8-sig") as handle:
        reader: csv.DictReader[str] = csv.DictReader(handle)
        return [row for row in reader if row.get("Crossing")]


def select_rows(rows: list[dict[str, str]], name: str | None) -> list[dict[str, str]]:
    if name:
        for row in rows:
            if row["Crossing"].strip() == name:
                return [row]
        raise ValueError(f"Crossing '{name}' not found in CSV.")
    selected: list[dict[str, str]] = []
    for row in rows:
        try:
            value = float(row["Adopted Flow"])
        except (KeyError, TypeError, ValueError):
            continue
        if value > 0:
            selected.append(row)
    if not selected:
        raise ValueError("No rows with a positive adopted flow were found.")
    return selected


def sanitize_workspace_name(name: str) -> str:
    cleaned: str = "".join(ch if ch.isalnum() or ch in {" ", "-", "_"} else "_" for ch in name.strip())
    return cleaned or "crossing"


def workspace_for_crossing(root: Path | None, name: str) -> Path | None:
    if not root:
        return None
    workspace: Path = root / sanitize_workspace_name(name)
    workspace.mkdir(parents=True, exist_ok=True)
    return workspace


def enum_label(value: Any) -> str:
    if value is None:
        return ""
    name = getattr(value, "name", str(value))
    return name.replace("_", " ").title()


def normalize_field(row: dict[str, str], key: str) -> str:
    value = row.get(key)
    if not isinstance(value, str):
        return ""
    return value.strip()


def build_crossing(
    row: dict[str, str],
    inputs: CrossingInputs,
    flow_value: float,
) -> tuple[Hy8Project, CulvertCrossing, float, int, CulvertBarrel]:
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
    return project, crossing, diameter, barrels, barrel


def hw_from_q(
    project: Hy8Project,
    crossing: CulvertCrossing,
    flow: float,
    hy8: Path | None,
    *,
    keep_files: bool,
    workspace: Path | None,
) -> HydraulicsResult:
    return crossing.hw_from_q(
        q=flow,
        hy8=hy8,
        project=project,
        workspace=workspace,
        keep_files=keep_files,
    )


def solve_headwater_with_q_from_hw(
    project: Hy8Project,
    crossing: CulvertCrossing,
    flow: float,
    *,
    hy8: Path | None,
    bounds: tuple[float, float],
    q_hint: float,
    keep_files: bool,
    workspace: Path | None,
    iterations: int = 12,
    tolerance: float = 1e-3,
) -> HydraulicsResult:
    lower_hw, upper_hw = bounds
    if not upper_hw > lower_hw:
        raise ValueError("Upper headwater bound must exceed the inlet invert.")

    def run(hw: float) -> HydraulicsResult:
        return crossing.q_from_hw(
            hw=hw,
            q_hint=q_hint,
            hy8=hy8,
            project=project,
            workspace=workspace,
            keep_files=keep_files,
        )

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


def write_results(outcomes: list[CrossingOutcome], path: Path) -> None:
    if not outcomes:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer: csv.DictWriter[str] = csv.DictWriter(handle, fieldnames=RESULT_FIELDNAMES)
        writer.writeheader()
        for outcome in outcomes:
            writer.writerow(outcome.to_row())


def make_failure_outcome(row: dict[str, str], error: Exception) -> CrossingOutcome:
    crossing_name: str = normalize_field(row, "Crossing") or "<unknown>"
    return CrossingOutcome(
        crossing=crossing_name,
        adopted_flow=normalize_field(row, "Adopted Flow"),
        barrels=normalize_field(row, "Barrels"),
        diameter=normalize_field(row, "Diameter (m)"),
        barrel_shape=None,
        barrel_material=None,
        inlet_type=None,
        inlet_edge_type=None,
        span=None,
        rise=None,
        barrel_length=None,
        inlet_invert_elev=None,
        outlet_invert_elev=None,
        roadway_width=None,
        roadway_elevation=None,
        tailwater_elevation=None,
        status="Failed",
        error_message=str(error),
        computed_flow=None,
        headwater=None,
        headwater_ratio=None,
        velocity=None,
        flow_type=None,
        overtopping=None,
        backcheck_flow=None,
        flow_error=None,
        hw_workspace=None,
        q_workspace=None,
    )


def run_crossing(
    row: dict[str, str],
    inputs: CrossingInputs,
    hy8_path: Path | None,
    *,
    keep_workspace: bool,
    workspace_root: Path | None,
) -> CrossingOutcome:
    adopted_flow = normalize_field(row, "Adopted Flow")
    barrels_value = normalize_field(row, "Barrels")
    diameter_value = normalize_field(row, "Diameter (m)")
    flow_value = float(adopted_flow)
    project, crossing, diameter, _, primary_barrel = build_crossing(row, inputs, flow_value)
    workspace: Path | None = workspace_for_crossing(root=workspace_root, name=crossing.name)
    barrel_length = max(0.0, primary_barrel.outlet_invert_station - primary_barrel.inlet_invert_station)
    roadway_width = crossing.roadway.width
    roadway_elevation = crossing.roadway.elevations[0] if crossing.roadway.elevations else None
    tailwater_elevation = crossing.tailwater.constant_elevation

    print(f"Crossing: {crossing.name}")
    print(f"  Adopted flow (m^3/s): {flow_value:.4f}")

    hw_result: HydraulicsResult = hw_from_q(
        project=project,
        crossing=crossing,
        flow=flow_value,
        hy8=hy8_path,
        keep_files=keep_workspace,
        workspace=workspace,
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
        workspace=workspace,
    )
    flow_error: float = abs(backcheck.computed_flow - flow_value)
    print(f"  q_from_hw back-check (m^3/s): {backcheck.computed_flow:.4f} (|error|={flow_error:.4f})")
    if keep_workspace:
        if hw_result.workspace:
            print(f"  hw_from_q workspace kept at: {hw_result.workspace}")
        if backcheck.workspace:
            print(f"  q_from_hw workspace kept at: {backcheck.workspace}")
    print()

    hw_row = hw_result.row
    flow_type = hw_row.flow_type if hw_row else None
    overtopping = bool(hw_row and hw_row.overtopping)
    return CrossingOutcome(
        crossing=crossing.name,
        adopted_flow=adopted_flow,
        barrels=barrels_value,
        diameter=diameter_value,
        barrel_shape=enum_label(primary_barrel.shape),
        barrel_material=enum_label(primary_barrel.material),
        inlet_type=enum_label(primary_barrel.inlet_type),
        inlet_edge_type=enum_label(primary_barrel.inlet_edge_type),
        span=primary_barrel.span,
        rise=primary_barrel.rise,
        barrel_length=barrel_length,
        inlet_invert_elev=primary_barrel.inlet_invert_elevation,
        outlet_invert_elev=primary_barrel.outlet_invert_elevation,
        roadway_width=roadway_width,
        roadway_elevation=roadway_elevation,
        tailwater_elevation=tailwater_elevation,
        status="Success",
        error_message=None,
        computed_flow=hw_result.computed_flow,
        headwater=hw_level,
        headwater_ratio=hw_ratio,
        velocity=velocity,
        flow_type=flow_type,
        overtopping=overtopping,
        backcheck_flow=backcheck.computed_flow,
        flow_error=flow_error,
        hw_workspace=hw_result.workspace,
        q_workspace=backcheck.workspace,
    )


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
    hy8_path: Path | None = Path(HY8_EXE) if HY8_EXE else None

    rows_to_run: list[dict[str, str]] = select_rows(rows=rows, name=CROSSING_NAME)
    workspace_root: Path | None = WORKSPACE_PATH if KEEP_WORKSPACE else None
    if workspace_root:
        workspace_root.mkdir(parents=True, exist_ok=True)

    results: list[CrossingOutcome] = []
    had_errors = False
    for row in rows_to_run:
        try:
            outcome = run_crossing(
                row=row,
                inputs=inputs,
                hy8_path=hy8_path,
                keep_workspace=KEEP_WORKSPACE,
                workspace_root=workspace_root,
            )
            results.append(outcome)
        except Exception as exc:  # pragma: no cover - best effort across rows
            crossing_name: str = row.get("Crossing", "<unknown>").strip()
            print(f"Skipping '{crossing_name}': {exc}", file=sys.stderr)
            results.append(make_failure_outcome(row, exc))
            had_errors = True
    if results:
        write_results(results, RESULTS_OUTPUT)
        print(f"Results saved to: {RESULTS_OUTPUT}")
    else:
        print("No successful crossings; results file not created.")
    if had_errors:
        raise SystemExit("One or more crossings failed; see stderr for details.")


if __name__ == "__main__":
    main()
