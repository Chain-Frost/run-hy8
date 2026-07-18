"""Evaluate circular culverts from a GIS layer using HY-8."""

from __future__ import annotations

import csv
import math
import sys
from concurrent.futures import Future, ProcessPoolExecutor, as_completed
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import geopandas as gpd
from pandas import DataFrame
from run_hy8.classes_references import UnitSystem
from run_hy8.hydraulics import FlowSearchError, HydraulicsResult
from run_hy8.hy8_path import resolve_hy8_path
from run_hy8.models import CulvertBarrel, CulvertCrossing, FlowDefinition, Hy8Project, RoadwayProfile
from run_hy8.results import Hy8ResultRow
from run_hy8.type_helpers import CulvertMaterial, CulvertShape, FlowMethod, InletEdgeType, InletType

INPUT_GIS_FILE = Path(
    r"Q:\BGER\PER\RP20181.498 GD AND FORTESCUE RIVER GAP RAIL HYDROLOGY MDL - RTIO\TUFLOW_MLGD\model\gis\GD02\1d_nwk_GD02_001_L.gpkg"
)
INPUT_LAYER: str | None = None
CROSSING_NAME: str | None = None
HY8_EXE: str | None = None
KEEP_WORKSPACE: bool = True
WORKSPACE_PATH: Path = Path("C:/Temp/hy8")
RESULTS_OUTPUT: Path = Path(__file__).resolve().parent / "culvert-results-1dnwk-GD2-Brenda.csv"
MAX_WORKERS = 10
CROSSING_LIMIT = 0
ROADWAY_WIDTH = 10.0
ROADWAY_FREEBOARD = 50.0
DEFAULT_BARRELS = 1
DEFAULT_MANNING_N = 0.024
MINIMUM_SEED_FLOW = 0.05
HEADWATER_RATIOS: tuple[float, ...] = (1.5, 2.0)

TYPE_FIELD = "Type"
NAME_FIELD = "ID"
LENGTH_FIELD = "Len_or_ANA"
MANNING_FIELD = "n_nF_Cd"
US_INVERT_FIELD = "US_Invert"
DS_INVERT_FIELD = "DS_Invert"
DIAMETER_FIELDS: tuple[str, ...] = ("Width_or_D", "Width_or_Diameter", "Width_or_Dia")
BARRELS_FIELDS: tuple[str, ...] = ("Number_of", "num_barrels", "Barrels")

RESULT_FIELDNAMES: list[str] = [
    "Crossing",
    "Source Row",
    "Source Type",
    "Barrels",
    "Diameter (m)",
    "Barrel Length (m)",
    "Manning n",
    "Inlet Invert Elev (m)",
    "Outlet Invert Elev (m)",
    "Tailwater Elevation (m)",
    "Status",
    "Error Message",
    "Headwater (HW:D = 1.50) (m)",
    "HW:D (HW:D = 1.50)",
    "Computed Flow (HW:D = 1.50) (m^3/s)",
    "Outlet Velocity (HW:D = 1.50) (m/s)",
    "Flow Type (HW:D = 1.50)",
    "Overtopping (HW:D = 1.50)",
    "Workspace (HW:D = 1.50)",
    "Headwater (HW:D = 2.00) (m)",
    "HW:D (HW:D = 2.00)",
    "Computed Flow (HW:D = 2.00) (m^3/s)",
    "Outlet Velocity (HW:D = 2.00) (m/s)",
    "Flow Type (HW:D = 2.00)",
    "Overtopping (HW:D = 2.00)",
    "Workspace (HW:D = 2.00)",
]


@dataclass(slots=True)
class CrossingRecord:
    source_row: int
    crossing: str
    source_type: str
    diameter: float
    length: float
    manning_n: float
    inlet_invert: float
    outlet_invert: float
    barrels: int = DEFAULT_BARRELS
    precheck_error: str | None = None


@dataclass(slots=True)
class ScenarioOutcome:
    headwater: float | None = None
    headwater_ratio: float | None = None
    computed_flow: float | None = None
    velocity: float | None = None
    flow_type: str | None = None
    overtopping: bool | None = None
    workspace: Path | None = None


@dataclass(slots=True)
class CrossingOutcome:
    crossing: str
    source_row: int
    source_type: str
    barrels: int | None
    diameter: float | None
    barrel_length: float | None
    manning_n: float | None
    inlet_invert_elev: float | None
    outlet_invert_elev: float | None
    tailwater_elevation: float | None
    status: str
    error_message: str | None
    hw_1p5: ScenarioOutcome
    hw_2p0: ScenarioOutcome

    @staticmethod
    def _format(value: float | int | None, places: int = 4) -> str:
        if value is None:
            return ""
        if isinstance(value, int):
            return str(value)
        return f"{value:.{places}f}"

    def to_row(self) -> dict[str, str]:
        return {
            "Crossing": self.crossing,
            "Source Row": str(self.source_row),
            "Source Type": self.source_type,
            "Barrels": self._format(self.barrels, places=0),
            "Diameter (m)": self._format(self.diameter, places=3),
            "Barrel Length (m)": self._format(self.barrel_length),
            "Manning n": self._format(self.manning_n, places=4),
            "Inlet Invert Elev (m)": self._format(self.inlet_invert_elev),
            "Outlet Invert Elev (m)": self._format(self.outlet_invert_elev),
            "Tailwater Elevation (m)": self._format(self.tailwater_elevation),
            "Status": self.status,
            "Error Message": self.error_message or "",
            "Headwater (HW:D = 1.50) (m)": self._format(self.hw_1p5.headwater),
            "HW:D (HW:D = 1.50)": self._format(self.hw_1p5.headwater_ratio),
            "Computed Flow (HW:D = 1.50) (m^3/s)": self._format(self.hw_1p5.computed_flow),
            "Outlet Velocity (HW:D = 1.50) (m/s)": self._format(self.hw_1p5.velocity),
            "Flow Type (HW:D = 1.50)": self.hw_1p5.flow_type or "",
            "Overtopping (HW:D = 1.50)": (
                "Yes" if self.hw_1p5.overtopping else ("No" if self.hw_1p5.overtopping is not None else "")
            ),
            "Workspace (HW:D = 1.50)": str(self.hw_1p5.workspace) if self.hw_1p5.workspace else "",
            "Headwater (HW:D = 2.00) (m)": self._format(self.hw_2p0.headwater),
            "HW:D (HW:D = 2.00)": self._format(self.hw_2p0.headwater_ratio),
            "Computed Flow (HW:D = 2.00) (m^3/s)": self._format(self.hw_2p0.computed_flow),
            "Outlet Velocity (HW:D = 2.00) (m/s)": self._format(self.hw_2p0.velocity),
            "Flow Type (HW:D = 2.00)": self.hw_2p0.flow_type or "",
            "Overtopping (HW:D = 2.00)": (
                "Yes" if self.hw_2p0.overtopping else ("No" if self.hw_2p0.overtopping is not None else "")
            ),
            "Workspace (HW:D = 2.00)": str(self.hw_2p0.workspace) if self.hw_2p0.workspace else "",
        }


def sanitize_workspace_name(name: str) -> str:
    cleaned = "".join(ch if ch.isalnum() or ch in {" ", "-", "_"} else "_" for ch in name.strip())
    return cleaned or "crossing"


def workspace_for_crossing(root: Path | None, source_row: int, name: str) -> Path | None:
    if root is None:
        return None
    workspace = root / f"{source_row:04d}_{sanitize_workspace_name(name)}"
    workspace.mkdir(parents=True, exist_ok=True)
    return workspace


def workspace_for_scenario(root: Path | None, scenario: str) -> Path | None:
    if root is None:
        return None
    workspace = root / sanitize_workspace_name(scenario)
    workspace.mkdir(parents=True, exist_ok=True)
    return workspace


def read_gis_records(path: Path, *, layer: str | None = None) -> list[dict[str, Any]]:
    if not path.exists():
        raise FileNotFoundError(f"GIS file not found: {path}")
    kwargs: dict[str, Any] = {}
    if layer:
        kwargs["layer"] = layer
    gdf: DataFrame = gpd.read_file(path, **kwargs) # pyright: ignore[reportUnknownMemberType]
    if gdf.empty:
        raise ValueError(f"No features found in GIS file: {path}")
    gdf = gdf.where(gdf.notna(), None)
    records: list[dict[str, Any]] = gdf.to_dict(orient="records") # pyright: ignore[reportAssignmentType]
    return records


def normalize_text(value: Any) -> str:
    if value is None:
        return ""
    text: str = str(value).strip()
    return "" if text.lower() == "none" else text


def optional_float(value: Any, *, default: float | None = None) -> float | None:
    if value is None or value == "":
        return default
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        return default
    if math.isnan(numeric):
        return default
    return numeric


def require_float(row: dict[str, Any], field_name: str) -> float:
    value = optional_float(row.get(field_name))
    if value is None:
        raise ValueError(f"Missing or invalid '{field_name}'.")
    return value


def first_present_value(row: dict[str, Any], field_names: tuple[str, ...]) -> tuple[str, Any]:
    for field_name in field_names:
        if field_name in row and row.get(field_name) not in (None, ""):
            return field_name, row.get(field_name)
    joined: str = ", ".join(field_names)
    raise ValueError(f"Missing required field. Expected one of: {joined}.")


def crossing_name_from_row(row: dict[str, Any], source_row: int) -> str:
    name: str = normalize_text(row.get(NAME_FIELD))
    return name or f"culvert_{source_row:04d}"


def row_to_record(row: dict[str, Any], source_row: int) -> CrossingRecord:
    source_type: str = normalize_text(row.get(TYPE_FIELD)).upper()
    if source_type != "C":
        raise ValueError(f"Unsupported culvert type '{source_type or '<blank>'}'. Only 'C' is supported.")

    _, diameter_raw = first_present_value(row=row, field_names=DIAMETER_FIELDS)
    diameter: float | None = optional_float(value=diameter_raw)
    if diameter is None or diameter <= 0:
        raise ValueError("Missing or invalid diameter field.")

    length: float = require_float(row=row, field_name=LENGTH_FIELD)
    if length <= 0:
        raise ValueError(f"'{LENGTH_FIELD}' must be greater than zero.")

    inlet_invert: float = require_float(row=row, field_name=US_INVERT_FIELD)
    outlet_invert: float = require_float(row=row, field_name=DS_INVERT_FIELD)

    manning_n: float | None = optional_float(value=row.get(MANNING_FIELD), default=DEFAULT_MANNING_N)
    if manning_n is None or manning_n <= 0:
        raise ValueError(f"Missing or invalid '{MANNING_FIELD}'.")

    barrels:int = DEFAULT_BARRELS
    try:
        _, barrels_raw = first_present_value(row, BARRELS_FIELDS)
    except ValueError:
        barrels_raw = None
    if barrels_raw not in (None, ""):
        try:
            barrels = int(float(barrels_raw))
        except (TypeError, ValueError) as exc:
            raise ValueError("Missing or invalid barrel count field.") from exc
        if barrels <= 0:
            raise ValueError("Barrel count must be greater than zero.")

    return CrossingRecord(
        source_row=source_row,
        crossing=crossing_name_from_row(row, source_row),
        source_type=source_type,
        diameter=diameter,
        length=length,
        manning_n=manning_n,
        inlet_invert=inlet_invert,
        outlet_invert=outlet_invert,
        barrels=barrels,
    )


def load_records(path: Path, *, layer: str | None = None) -> list[CrossingRecord]:
    raw_rows = read_gis_records(path=path, layer=layer)
    records: list[CrossingRecord] = []
    for source_row, row in enumerate(raw_rows, start=1):
        try:
            record: CrossingRecord = row_to_record(row, source_row)
        except ValueError as exc:
            name: str = crossing_name_from_row(row, source_row)
            record = CrossingRecord(
                source_row=source_row,
                crossing=name,
                source_type=normalize_text(row.get(TYPE_FIELD)).upper(),
                diameter=math.nan,
                length=math.nan,
                manning_n=math.nan,
                inlet_invert=math.nan,
                outlet_invert=math.nan,
                precheck_error=str(exc),
            )
        records.append(record)
    return records


def select_records(records: list[CrossingRecord], name: str | None) -> list[CrossingRecord]:
    if name:
        filtered: list[CrossingRecord] = [record for record in records if record.crossing == name]
        if not filtered:
            raise ValueError(f"Crossing '{name}' not found in GIS input.")
        return filtered
    return records


def limit_crossings(records: list[CrossingRecord], limit: int) -> list[CrossingRecord]:
    if limit <= 0:
        return records
    return records[:limit]


def build_crossing(record: CrossingRecord) -> tuple[Hy8Project, CulvertCrossing]:
    if record.source_type != "C":
        raise ValueError(f"Unsupported culvert type '{record.source_type or '<blank>'}'. Only 'C' is supported.")
    if not math.isfinite(record.diameter) or record.diameter <= 0:
        raise ValueError("Diameter must be greater than zero.")
    if not math.isfinite(record.length) or record.length <= 0:
        raise ValueError("Barrel length must be greater than zero.")
    if not math.isfinite(record.manning_n) or record.manning_n <= 0:
        raise ValueError("Manning n must be greater than zero.")
    if not math.isfinite(record.inlet_invert) or not math.isfinite(record.outlet_invert):
        raise ValueError("Inlet and outlet invert elevations are required.")

    project = Hy8Project(title=f"GIS demo - {record.crossing}", units=UnitSystem.SI, exit_loss_option=0)
    crossing = CulvertCrossing(name=record.crossing)
    project.crossings.append(crossing)

    crossing.flow = FlowDefinition(method=FlowMethod.USER_DEFINED, user_values=[MINIMUM_SEED_FLOW])
    crossing.tailwater.set_constant(elevation=record.outlet_invert, invert=record.outlet_invert)

    roadway: RoadwayProfile = crossing.roadway
    roadway.width = ROADWAY_WIDTH
    roadway.stations = [0.0, ROADWAY_WIDTH]
    roadway_elevation: float = record.inlet_invert + ROADWAY_FREEBOARD
    roadway.elevations = [roadway_elevation, roadway_elevation]

    barrel = CulvertBarrel(
        name=f"{record.crossing} Barrel",
        span=record.diameter,
        rise=record.diameter,
        shape=CulvertShape.CIRCLE,
        material=CulvertMaterial.CONCRETE,
        number_of_barrels=record.barrels,
        inlet_invert_station=0.0,
        inlet_invert_elevation=record.inlet_invert,
        outlet_invert_station=record.length,
        outlet_invert_elevation=record.outlet_invert,
        inlet_type=InletType.STRAIGHT,
        inlet_edge_type=InletEdgeType.THIN_EDGE_PROJECTING,
    )
    barrel.manning_n_top = record.manning_n
    barrel.manning_n_bottom = record.manning_n
    crossing.culverts.clear()
    crossing.culverts.append(barrel)

    errors: list[str] = crossing.validate()
    if errors:
        raise ValueError("; ".join(errors))
    return project, crossing


def seed_flow_hint(record: CrossingRecord) -> float:
    area: float = math.pi * (record.diameter**2) / 4.0
    return max(area * max(record.barrels, 1), MINIMUM_SEED_FLOW)


def to_scenario_outcome(result: HydraulicsResult, record: CrossingRecord) -> ScenarioOutcome:
    row: Hy8ResultRow | None = result.row
    if row is None:
        return ScenarioOutcome(
            headwater=result.computed_headwater,
            computed_flow=result.computed_flow,
            workspace=result.workspace,
        )
    return ScenarioOutcome(
        headwater=result.computed_headwater,
        headwater_ratio=(result.computed_headwater - record.inlet_invert) / record.diameter,
        computed_flow=result.computed_flow,
        velocity=row.velocity,
        flow_type=row.flow_type,
        overtopping=bool(row.overtopping),
        workspace=result.workspace,
    )


def describe_scenario(label: str, outcome: ScenarioOutcome) -> None:
    print(f"  {label}:")
    if outcome.computed_flow is None and outcome.headwater is None:
        print("    Result unavailable.")
        return
    if outcome.headwater is not None:
        print(f"    Headwater elevation (m): {outcome.headwater:.4f}")
    if outcome.computed_flow is not None:
        print(f"    Computed flow (m^3/s): {outcome.computed_flow:.4f}")
    if outcome.velocity is not None:
        print(f"    Outlet velocity (m/s): {outcome.velocity:.4f}")
    if outcome.flow_type:
        print(f"    Flow type: {outcome.flow_type}")
    if outcome.overtopping:
        print("    Warning: HY-8 indicates overtopping.")


def make_failure_outcome(
    record: CrossingRecord,
    error: Exception,
    *,
    status: str = "Failed",
) -> CrossingOutcome:
    return CrossingOutcome(
        crossing=record.crossing,
        source_row=record.source_row,
        source_type=record.source_type,
        barrels=record.barrels,
        diameter=record.diameter if math.isfinite(record.diameter) else None,
        barrel_length=record.length if math.isfinite(record.length) else None,
        manning_n=record.manning_n if math.isfinite(record.manning_n) else None,
        inlet_invert_elev=record.inlet_invert if math.isfinite(record.inlet_invert) else None,
        outlet_invert_elev=record.outlet_invert if math.isfinite(record.outlet_invert) else None,
        tailwater_elevation=record.outlet_invert if math.isfinite(record.outlet_invert) else None,
        status=status,
        error_message=str(error),
        hw_1p5=ScenarioOutcome(),
        hw_2p0=ScenarioOutcome(),
    )


def run_crossing(
    record: CrossingRecord,
    *,
    hy8_path: Path | None,
    keep_workspace: bool,
    workspace_root: Path | None,
) -> CrossingOutcome:
    if record.precheck_error:
        return make_failure_outcome(record, ValueError(record.precheck_error))

    project, crossing = build_crossing(record=record)
    q_hint: float = seed_flow_hint(record=record)
    crossing_workspace: Path | None = workspace_for_crossing(root=workspace_root, source_row=record.source_row, name=record.crossing)

    print(f"Crossing: {record.crossing}")
    print(f"  Source row: {record.source_row}")
    print(f"  Diameter (m): {record.diameter:.3f}")
    print(f"  Barrel length (m): {record.length:.3f}")
    print(f"  Manning n: {record.manning_n:.4f}")
    print(f"  Tailwater elevation (m): {record.outlet_invert:.4f}")

    outcomes: dict[float, ScenarioOutcome] = {}
    error_messages: list[str] = []
    status = "Success"

    for ratio in HEADWATER_RATIOS:
        label: str = f"HW:D = {ratio:.2f}"
        scenario_workspace: Path | None = workspace_for_scenario(root=crossing_workspace, scenario=label)
        target_headwater: float = record.inlet_invert + (ratio * record.diameter)
        try:
            result: HydraulicsResult = crossing.q_from_hw(
                hw=target_headwater,
                q_hint=q_hint,
                hy8=hy8_path,
                project=project,
                keep_files=keep_workspace,
                workspace=scenario_workspace,
            )
            outcome: ScenarioOutcome = to_scenario_outcome(result=result, record=record)
            outcomes[ratio] = outcome
        except FlowSearchError as exc:
            status = "Failed"
            error_messages.append(f"{label} search failed: {exc}")
            outcomes[ratio] = ScenarioOutcome()
        describe_scenario(label=label, outcome=outcomes[ratio])

    print()

    return CrossingOutcome(
        crossing=record.crossing,
        source_row=record.source_row,
        source_type=record.source_type,
        barrels=record.barrels,
        diameter=record.diameter,
        barrel_length=record.length,
        manning_n=record.manning_n,
        inlet_invert_elev=record.inlet_invert,
        outlet_invert_elev=record.outlet_invert,
        tailwater_elevation=record.outlet_invert,
        status=status,
        error_message="; ".join(error_messages) if error_messages else None,
        hw_1p5=outcomes.get(1.5, ScenarioOutcome()),
        hw_2p0=outcomes.get(2.0, ScenarioOutcome()),
    )


def write_results(outcomes: list[CrossingOutcome], path: Path) -> None:
    if not outcomes:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer: csv.DictWriter[str] = csv.DictWriter(handle, fieldnames=RESULT_FIELDNAMES)
        writer.writeheader()
        for outcome in outcomes:
            writer.writerow(outcome.to_row())


def _crossing_worker(
    payload: tuple[CrossingRecord, str | None, bool, str | None],
) -> CrossingOutcome:
    record, hy8_str, keep_workspace, workspace_str = payload
    hy8_path: Path | None = Path(hy8_str) if hy8_str else None
    workspace_root: Path | None = Path(workspace_str) if workspace_str else None
    try:
        return run_crossing(
            record=record,
            hy8_path=hy8_path,
            keep_workspace=keep_workspace,
            workspace_root=workspace_root,
        )
    except Exception as exc:  # pragma: no cover - worker best effort
        return make_failure_outcome(record=record, error=exc)


def main() -> None:
    hy8_path: Path = Path(HY8_EXE) if HY8_EXE else resolve_hy8_path()
    workspace_root: Path | None = WORKSPACE_PATH if KEEP_WORKSPACE else None
    if workspace_root:
        workspace_root.mkdir(parents=True, exist_ok=True)

    records: list[CrossingRecord] = load_records(path=INPUT_GIS_FILE, layer=INPUT_LAYER)
    records_to_run: list[CrossingRecord] = select_records(records=records, name=CROSSING_NAME)
    records_to_run = limit_crossings(records=records_to_run, limit=CROSSING_LIMIT)

    hy8_str: str | None = str(hy8_path) if hy8_path else None
    workspace_str: str | None = str(workspace_root) if workspace_root else None
    payloads: list[tuple[CrossingRecord, str | None, bool, str | None]] = [(record, hy8_str, KEEP_WORKSPACE, workspace_str) for record in records_to_run]

    results: list[CrossingOutcome | None] = [None] * len(payloads)
    had_errors = False
    if payloads:
        max_workers: int = min(MAX_WORKERS, len(payloads)) or 1
        with ProcessPoolExecutor(max_workers=max_workers) as executor:
            futures: dict[Future[CrossingOutcome], int] = {executor.submit(_crossing_worker, payload): index for index, payload in enumerate(payloads)}
            for future in as_completed(futures):
                index: int = futures[future]
                outcome: CrossingOutcome = future.result()
                results[index] = outcome
                if outcome.status != "Success":
                    print(
                        f"Crossing '{outcome.crossing}' failed: {outcome.error_message or 'unknown error'}",
                        file=sys.stderr,
                    )
                    had_errors = True

    completed: list[CrossingOutcome] = [result for result in results if result]
    if completed:
        write_results(outcomes=completed, path=RESULTS_OUTPUT)
        print(f"Results saved to: {RESULTS_OUTPUT}")
    else:
        print("No results were generated.")
    if had_errors:
        raise SystemExit("One or more crossings failed; see stderr for details.")


if __name__ == "__main__":
    main()
