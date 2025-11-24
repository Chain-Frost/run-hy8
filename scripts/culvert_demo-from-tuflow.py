"""Evaluate culvert crossings from the Excel list using HY-8."""

from __future__ import annotations

# 3. Inside a script (last resort)
# At the very top of your script, before any imports:
# This suppresses writing .pyc for imports after that line. It does not prevent Python from using existing .pyc files if they are already present.
import sys
from pathlib import Path

# sys.dont_write_bytecode = True
# this is to run it from within the repo and not use installed library.
# ROOT_PATH: Path = Path(__file__).resolve().parent.parent
# SRC_PATH: Path = ROOT_PATH / "src"
# src_str: str = str(SRC_PATH)
# if src_str not in sys.path:
#     sys.path.insert(0, src_str)

import csv
import math
import shutil
import tempfile
from concurrent.futures import ProcessPoolExecutor, as_completed
from dataclasses import dataclass

from typing import Any, LiteralString
import pandas as pd
from pandas import DataFrame
from run_hy8.writer import Hy8FileWriter
from run_hy8.hydraulics import HydraulicsResult, FlowSearchError
from run_hy8.classes_references import UnitSystem
from run_hy8.models import (
    CulvertBarrel,
    CulvertCrossing,
    FlowDefinition,
    Hy8Project,
    RoadwayProfile,
)
from run_hy8.executor import Hy8Executable
from run_hy8.hy8_path import resolve_hy8_path
from run_hy8.results import FlowProfile, Hy8ResultRow, Hy8Results, Hy8Series, parse_rst, parse_rsql
from run_hy8.type_helpers import (
    CulvertMaterial,
    CulvertShape,
    InletEdgeType,
    InletType,
    FlowMethod,
)


DEFAULT_EXCEL: Path = Path(__file__).resolve().parent / "Rev A Report Culverts.xlsx"
# Hard-coded configuration; edit these to suit each run.
EXCEL_PATH: Path = DEFAULT_EXCEL
CROSSING_NAME: str | None = None
HY8_EXE: str | None = None
KEEP_WORKSPACE: bool = True
WORKSPACE_PATH: Path = Path("C:/Temp/hy8")
ROADWAY_WIDTH = 10.0
DEFAULT_INLET_INVERT = 0.15
DEFAULT_OUTLET_INVERT = 0.0
DEFAULT_BARREL_LENGTH = 30.0
DEFAULT_TAILWATER = 0.0
HEADWALL_RATIO_MULTIPLIER = 1.5
MAX_WORKERS = 10
MINIMUM_SCENARIO_FLOW = 1e-4
PROJECT_OUTPUT_DIR: Path = Path(__file__).resolve().parent / "hy8-projects"
CROSSING_LIMIT = 10  # Set to >0 to process only the first N crossings

RESULTS_OUTPUT: Path = Path(__file__).resolve().parent / "culvert-results.csv"
MINIMUM_SEED_FLOW = 1e-3

FLOW_DS_TW_PREFIX = "Q @ DS_h TW"
FLOW_ZERO_TW_PREFIX = "Q @ Invert TW"
HW_DATA_PREFIX = "HW = US_h"
HW_RATIO_PREFIX: str = f"HW:D = {HEADWALL_RATIO_MULTIPLIER:.2f}"
HW_DATA_LABEL: LiteralString = f"{HW_DATA_PREFIX}, {FLOW_DS_TW_PREFIX}"
HW_RATIO_LABEL: str = f"{HW_RATIO_PREFIX}, {FLOW_ZERO_TW_PREFIX}"

RESULT_FIELDNAMES: list[str] = [
    "Crossing",
    "AEP",
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
    "US Headwater (m)",
    "Status",
    "Error Message",
    f"Computed Flow ({FLOW_DS_TW_PREFIX}) (m^3/s)",
    f"Headwater ({FLOW_DS_TW_PREFIX}) (m)",
    f"HW:D ({FLOW_DS_TW_PREFIX})",
    f"Outlet Velocity ({FLOW_DS_TW_PREFIX}) (m/s)",
    f"Flow Type ({FLOW_DS_TW_PREFIX})",
    f"Overtopping ({FLOW_DS_TW_PREFIX})",
    f"Workspace ({FLOW_DS_TW_PREFIX})",
    f"Computed Flow ({FLOW_ZERO_TW_PREFIX}) (m^3/s)",
    f"Headwater ({FLOW_ZERO_TW_PREFIX}) (m)",
    f"HW:D ({FLOW_ZERO_TW_PREFIX})",
    f"Outlet Velocity ({FLOW_ZERO_TW_PREFIX}) (m/s)",
    f"Flow Type ({FLOW_ZERO_TW_PREFIX})",
    f"Overtopping ({FLOW_ZERO_TW_PREFIX})",
    f"Workspace ({FLOW_ZERO_TW_PREFIX})",
    f"Headwater ({HW_DATA_PREFIX}) (m)",
    f"HW:D ({HW_DATA_PREFIX})",
    f"Computed Flow ({HW_DATA_LABEL}) (m^3/s)",
    f"Outlet Velocity ({HW_DATA_LABEL}) (m/s)",
    f"Flow Type ({HW_DATA_LABEL})",
    f"Overtopping ({HW_DATA_LABEL})",
    f"Workspace ({HW_DATA_LABEL})",
    f"Headwater ({HW_RATIO_PREFIX}) (m)",
    f"HW:D ({HW_RATIO_PREFIX})",
    f"Computed Flow ({HW_RATIO_LABEL}) (m^3/s)",
    f"Outlet Velocity ({HW_RATIO_LABEL}) (m/s)",
    f"Flow Type ({HW_RATIO_LABEL})",
    f"Overtopping ({HW_RATIO_LABEL})",
    f"Workspace ({HW_RATIO_LABEL})",
]


@dataclass(slots=True)
class CrossingInputs:
    """Geometry inputs shared across all rows."""

    inlet_invert: float
    outlet_invert: float
    length: float
    roadway_elevation: float
    roadway_width: float = ROADWAY_WIDTH
    tailwater_elevation: float = 0.0


def inputs_from_row(row: dict[str, Any], *, tailwater: float) -> CrossingInputs:
    def get_value(key: str, default: float) -> float:
        value = row.get(key, default)
        try:
            return float(value)
        except (TypeError, ValueError):
            return default

    inlet_invert = get_value("US Invert", DEFAULT_INLET_INVERT)
    outlet_invert = get_value("DS Invert", DEFAULT_OUTLET_INVERT)
    length = get_value("Length", DEFAULT_BARREL_LENGTH)
    roadway_elevation = inlet_invert + 50.0
    return CrossingInputs(
        inlet_invert=inlet_invert,
        outlet_invert=outlet_invert,
        length=length,
        roadway_elevation=roadway_elevation,
        roadway_width=ROADWAY_WIDTH,
        tailwater_elevation=tailwater,
    )


@dataclass(slots=True)
class FixedFlowScenario:
    """Metadata for a single fixed-flow HY-8 evaluation."""

    flow: float
    label: str
    row: dict[str, Any]
    ds_tailwater: float
    zero_tailwater: float


@dataclass(slots=True)
class ScenarioOutcome:
    """Hydraulic metrics for an individual scenario."""

    computed_flow: float | None = None
    headwater: float | None = None
    headwater_ratio: float | None = None
    velocity: float | None = None
    flow_type: str | None = None
    overtopping: bool | None = None
    workspace: Path | None = None


@dataclass(slots=True)
class CrossingOutcome:
    crossing: str
    aep: str
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
    us_headwater: float | None
    status: str
    error_message: str | None
    q_tailwater: ScenarioOutcome
    q_zero_tailwater: ScenarioOutcome
    hw_data_tailwater: ScenarioOutcome
    hw_ratio_no_tailwater: ScenarioOutcome

    @staticmethod
    def _format(value: float | None) -> str:
        return "" if value is None else f"{value:.4f}"

    @staticmethod
    def _format_diameter(value: str | None) -> str:
        if not value:
            return ""
        try:
            return f"{float(value):.3f}"
        except ValueError:
            return value

    def to_row(self) -> dict[str, str]:
        row: dict[str, str] = {
            "Crossing": self.crossing,
            "AEP": self.aep,
            "Adopted Flow (m^3/s)": self.adopted_flow,
            "Barrels": self.barrels,
            "Diameter (m)": self._format_diameter(self.diameter),
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
            "US Headwater (m)": self._format(self.us_headwater),
            "Status": self.status,
            "Error Message": self.error_message or "",
            f"Computed Flow ({FLOW_DS_TW_PREFIX}) (m^3/s)": self._format(self.q_tailwater.computed_flow),
            f"Headwater ({FLOW_DS_TW_PREFIX}) (m)": self._format(self.q_tailwater.headwater),
            f"HW:D ({FLOW_DS_TW_PREFIX})": self._format(self.q_tailwater.headwater_ratio),
            f"Outlet Velocity ({FLOW_DS_TW_PREFIX}) (m/s)": self._format(self.q_tailwater.velocity),
            f"Flow Type ({FLOW_DS_TW_PREFIX})": self.q_tailwater.flow_type or "",
            f"Overtopping ({FLOW_DS_TW_PREFIX})": (
                "Yes" if self.q_tailwater.overtopping else ("No" if self.q_tailwater.overtopping is not None else "")
            ),
            f"Workspace ({FLOW_DS_TW_PREFIX})": str(self.q_tailwater.workspace) if self.q_tailwater.workspace else "",
            f"Computed Flow ({FLOW_ZERO_TW_PREFIX}) (m^3/s)": self._format(self.q_zero_tailwater.computed_flow),
            f"Headwater ({FLOW_ZERO_TW_PREFIX}) (m)": self._format(self.q_zero_tailwater.headwater),
            f"HW:D ({FLOW_ZERO_TW_PREFIX})": self._format(self.q_zero_tailwater.headwater_ratio),
            f"Outlet Velocity ({FLOW_ZERO_TW_PREFIX}) (m/s)": self._format(self.q_zero_tailwater.velocity),
            f"Flow Type ({FLOW_ZERO_TW_PREFIX})": self.q_zero_tailwater.flow_type or "",
            f"Overtopping ({FLOW_ZERO_TW_PREFIX})": (
                "Yes"
                if self.q_zero_tailwater.overtopping
                else ("No" if self.q_zero_tailwater.overtopping is not None else "")
            ),
            f"Workspace ({FLOW_ZERO_TW_PREFIX})": (
                str(self.q_zero_tailwater.workspace) if self.q_zero_tailwater.workspace else ""
            ),
            f"Headwater ({HW_DATA_PREFIX}) (m)": self._format(self.hw_data_tailwater.headwater),
            f"HW:D ({HW_DATA_PREFIX})": self._format(self.hw_data_tailwater.headwater_ratio),
            f"Computed Flow ({HW_DATA_LABEL}) (m^3/s)": self._format(self.hw_data_tailwater.computed_flow),
            f"Outlet Velocity ({HW_DATA_LABEL}) (m/s)": self._format(self.hw_data_tailwater.velocity),
            f"Flow Type ({HW_DATA_LABEL})": self.hw_data_tailwater.flow_type or "",
            f"Overtopping ({HW_DATA_LABEL})": (
                "Yes"
                if self.hw_data_tailwater.overtopping
                else ("No" if self.hw_data_tailwater.overtopping is not None else "")
            ),
            f"Workspace ({HW_DATA_LABEL})": (
                str(self.hw_data_tailwater.workspace) if self.hw_data_tailwater.workspace else ""
            ),
            f"Headwater ({HW_RATIO_PREFIX}) (m)": self._format(self.hw_ratio_no_tailwater.headwater),
            f"HW:D ({HW_RATIO_PREFIX})": self._format(self.hw_ratio_no_tailwater.headwater_ratio),
            f"Computed Flow ({HW_RATIO_LABEL}) (m^3/s)": self._format(self.hw_ratio_no_tailwater.computed_flow),
            f"Outlet Velocity ({HW_RATIO_LABEL}) (m/s)": self._format(self.hw_ratio_no_tailwater.velocity),
            f"Flow Type ({HW_RATIO_LABEL})": self.hw_ratio_no_tailwater.flow_type or "",
            f"Overtopping ({HW_RATIO_LABEL})": (
                "Yes"
                if self.hw_ratio_no_tailwater.overtopping
                else ("No" if self.hw_ratio_no_tailwater.overtopping is not None else "")
            ),
            f"Workspace ({HW_RATIO_LABEL})": (
                str(self.hw_ratio_no_tailwater.workspace) if self.hw_ratio_no_tailwater.workspace else ""
            ),
        }
        return row


def _select_result_row(results: Hy8Results, target_flow: float) -> Hy8ResultRow:
    """Return the row whose discharge best matches the requested target."""

    best: Hy8ResultRow | None = None
    best_delta: float = float("inf")
    for row in results.rows:
        if math.isnan(row.flow):
            continue
        delta: float = abs(row.flow - target_flow)
        if delta < best_delta:
            best_delta = delta
            best = row
    if best is None:
        raise ValueError("HY-8 output did not include any usable rows.")
    return best


def load_rows(excel_path: Path) -> list[dict[str, Any]]:
    if not excel_path.exists():
        raise FileNotFoundError(f"Culvert Excel workbook not found: {excel_path}")
    df = pd.read_excel(excel_path, sheet_name="Maximums")  # pyright: ignore[reportUnknownMemberType]
    df = df.rename(
        columns={
            "Chan ID": "Crossing",
            "Q": "Adopted Flow (m^3/s)",
            "num_barrels": "Barrels",
            "Height": "Diameter (m)",
        }
    )
    df["Crossing"] = df["Crossing"].fillna("").astype(str).str.strip()  # pyright: ignore[reportUnknownMemberType]
    df["aep_text"] = df["aep_text"].fillna("").astype(str).str.strip()  # pyright: ignore[reportUnknownMemberType]
    df: DataFrame = df[df["Crossing"].astype(bool)]
    df = df.sort_values(  # pyright: ignore[reportUnknownMemberType]
        ["Crossing", "aep_text", "Adopted Flow (m^3/s)"], ascending=[True, True, False]
    )
    grouped: DataFrame = df.groupby(  # pyright: ignore[reportUnknownMemberType]
        ["Crossing", "aep_text"], as_index=False
    ).first()
    grouped = grouped.where(pd.notna(grouped), None)  # pyright: ignore[reportUnknownMemberType]
    records: list[dict[str, Any]] = grouped.to_dict(  # pyright: ignore[reportAssignmentType, reportUnknownMemberType]
        orient="records"
    )
    return records


def select_rows(rows: list[dict[str, Any]], name: str | None) -> list[dict[str, Any]]:
    def matches(row: dict[str, Any], target: str) -> bool:
        base = normalize_field(row, "Crossing")
        label = crossing_label(row)
        return target == base or target == label

    filtered: list[dict[str, Any]] = []
    if name:
        for row in rows:
            if matches(row, name):
                if _flow_value(row) > 0:
                    filtered.append(row)
        if not filtered:
            raise ValueError(f"Crossing '{name}' not found in Excel input.")
        return filtered

    for row in rows:
        if _flow_value(row) > 0:
            filtered.append(row)
    if not filtered:
        raise ValueError("No rows with a positive adopted flow were found.")
    return filtered


def sanitize_workspace_name(name: str) -> str:
    cleaned: str = "".join(ch if ch.isalnum() or ch in {" ", "-", "_"} else "_" for ch in name.strip())
    return cleaned or "crossing"


def workspace_for_crossing(root: Path | None, name: str) -> Path | None:
    if not root:
        return None
    workspace: Path = root / sanitize_workspace_name(name)
    workspace.mkdir(parents=True, exist_ok=True)
    return workspace


def workspace_for_scenario(root: Path | None, scenario: str) -> Path | None:
    if not root:
        return None
    workspace: Path = root / sanitize_workspace_name(scenario)
    workspace.mkdir(parents=True, exist_ok=True)
    return workspace


def set_tailwater(crossing: CulvertCrossing, elevation: float) -> None:
    crossing.tailwater.set_constant(elevation=elevation, invert=elevation)


def run_fixed_flow_scenarios(
    rows: list[dict[str, Any]],
    *,
    hy8_path: Path | None,
    workspace_root: Path | None,
    keep_workspace: bool,
) -> dict[str, tuple[ScenarioOutcome, ScenarioOutcome]]:
    """Run the fixed-flow headwater scenarios for all rows of a crossing."""

    if not rows:
        return {}
    crossing_name: str = normalize_field(rows[0], "Crossing")
    flows: list[FixedFlowScenario] = []
    for row in rows:
        flow: float = _flow_value(row=row)
        label: str = aep_flow_label(aep_text=normalize_field(row=row, key="aep_text"))
        ds_tailwater: float | None = optional_float_value(row=row, key="DS_h", default=DEFAULT_TAILWATER)
        invert_tailwater: float | None = optional_float_value(row=row, key="DS Invert", default=ds_tailwater)
        ds_value: float = ds_tailwater if ds_tailwater is not None else DEFAULT_TAILWATER
        zero_value: float = invert_tailwater if invert_tailwater is not None else ds_value
        flows.append(
            FixedFlowScenario(
                flow=flow,
                label=label,
                row=row,
                ds_tailwater=ds_value,
                zero_tailwater=zero_value,
            )
        )
    flows.sort(key=lambda item: item.flow)
    scenario_workspace: Path | None = workspace_for_scenario(root=workspace_root, scenario="Fixed Flow Runs")
    cleanup: bool = False
    if scenario_workspace is None:
        scenario_workspace = Path(tempfile.mkdtemp(prefix="hy8_fixed_flow_"))
        cleanup = not keep_workspace

    try:
        hy8_exec_path: Path = hy8_path or resolve_hy8_path()
        hy8_exec = Hy8Executable(exe_path=hy8_exec_path)

        def group_entries(attribute: str) -> list[tuple[float, list[FixedFlowScenario]]]:
            grouped: dict[float, list[FixedFlowScenario]] = {}
            for entry in flows:
                key = getattr(entry, attribute)
                grouped.setdefault(key, []).append(entry)
            return sorted(grouped.items(), key=lambda item: item[0])

        def run_tailwater_groups(
            groups: list[tuple[float, list[FixedFlowScenario]]],
            scenario_label: str,
        ) -> dict[str, ScenarioOutcome]:
            scenario_map: dict[str, ScenarioOutcome] = {}
            if not groups:
                return scenario_map
            for index, (tailwater_value, group_entries) in enumerate(groups, start=1):
                suffix: str = scenario_label if len(groups) == 1 else f"{scenario_label} #{index}"
                representative: FixedFlowScenario = group_entries[0]
                inputs: CrossingInputs = inputs_from_row(representative.row, tailwater=tailwater_value)
                project, base_crossing, diameter, _, _ = build_crossing(representative.row, inputs, representative.flow)
                base_crossing.name = f"{crossing_name} [{suffix}]"
                flow_def = FlowDefinition(method=FlowMethod.USER_DEFINED)
                for entry in sorted(group_entries, key=lambda item: item.flow):
                    flow_def.add_user_flow(value=entry.flow, label=entry.label)
                base_crossing.flow = flow_def
                hy8_file: Path = scenario_workspace / f"{sanitize_workspace_name(base_crossing.name)}.hy8"
                Hy8FileWriter(project=project).write(output_path=hy8_file, overwrite=True)
                hy8_exec.open_run_save(hy8_file=hy8_file)
                rst_map: dict[str, Hy8Series] = parse_rst(hy8_file.with_suffix(".rst"))
                rsql_map: dict[str, list[FlowProfile]] = parse_rsql(hy8_file.with_suffix(".rsql"))
                series: Hy8Series | None = rst_map.get(base_crossing.name)
                if not series:
                    raise ValueError(f"HY-8 results missing crossing '{base_crossing.name}'.")
                results = Hy8Results(series, rsql_map.get(base_crossing.name, []))
                for entry in group_entries:
                    row: Hy8ResultRow = _select_result_row(results, entry.flow)
                    headwater: float = row.headwater_elevation
                    ratio: float | None = (headwater - inputs.inlet_invert) / diameter if diameter else None
                    scenario_map[entry.label] = ScenarioOutcome(
                        computed_flow=row.flow,
                        headwater=headwater,
                        headwater_ratio=ratio,
                        velocity=row.velocity,
                        flow_type=row.flow_type,
                        overtopping=bool(row.overtopping),
                        workspace=hy8_file if keep_workspace else None,
                    )
            return scenario_map

        ds_results: dict[str, ScenarioOutcome] = run_tailwater_groups(group_entries("ds_tailwater"), FLOW_DS_TW_PREFIX)
        zero_results: dict[str, ScenarioOutcome] = run_tailwater_groups(
            group_entries("zero_tailwater"), FLOW_ZERO_TW_PREFIX
        )

        combined: dict[str, tuple[ScenarioOutcome, ScenarioOutcome]] = {}
        for entry in flows:
            label = entry.label
            combined[label] = (ds_results[label], zero_results[label])
        return combined
    finally:
        if cleanup and scenario_workspace.exists():
            shutil.rmtree(scenario_workspace, ignore_errors=True)


def run_fixed_flow_for_row(
    row: dict[str, Any],
    *,
    hy8_path: Path | None,
    workspace_root: Path | None,
    keep_workspace: bool,
) -> tuple[ScenarioOutcome, ScenarioOutcome]:
    label: str = aep_flow_label(aep_text=normalize_field(row=row, key="aep_text"))
    outcomes: dict[str, tuple[ScenarioOutcome, ScenarioOutcome]] = run_fixed_flow_scenarios(
        rows=[row],
        hy8_path=hy8_path,
        workspace_root=workspace_root,
        keep_workspace=keep_workspace,
    )
    return outcomes[label]


def enum_label(value: Any) -> str:
    if value is None:
        return ""
    name = getattr(value, "name", str(value))
    return name.replace("_", " ").title()


def normalize_field(row: dict[str, Any], key: str) -> str:
    value = row.get(key)
    if value is None:
        return ""
    return str(value).strip()


def crossing_label(row: dict[str, Any]) -> str:
    crossing: str = normalize_field(row=row, key="Crossing")
    aep: str = normalize_field(row=row, key="aep_text")
    return f"{crossing} ({aep})" if aep else crossing


def limit_crossings(rows: list[dict[str, Any]], limit: int) -> list[dict[str, Any]]:
    if limit <= 0:
        return rows
    ordered_names: list[str] = []
    for row in rows:
        name = normalize_field(row, "Crossing")
        if name not in ordered_names:
            ordered_names.append(name)
        if len(ordered_names) >= limit:
            break
    allowed: set[str] = set(ordered_names)
    return [row for row in rows if normalize_field(row, "Crossing") in allowed]


def _flow_value(row: dict[str, Any]) -> float:
    try:
        value = float(row.get("Adopted Flow (m^3/s)", 0.0) or 0.0)
    except (TypeError, ValueError):
        value = 0.0
    return max(value, 0.0)


def _flow_seed_hint(value: float, barrel: CulvertBarrel | None) -> float:
    """Return a non-zero flow to seed headwater solves when the adopted flow is missing."""

    if value and value > MINIMUM_SEED_FLOW:
        return value
    area: float | None = None
    if barrel:
        span: float = max(barrel.span or 0.0, 0.0)
        rise: float = max(barrel.rise or span, 0.0)
        if barrel.shape is CulvertShape.CIRCLE:
            diameter: float = span if span > 0 else rise
            area = math.pi * (diameter**2) / 4.0
        else:
            area = span * rise
        barrels: int = barrel.number_of_barrels or 0
        area *= max(barrels, 1)
    if area is None or area <= 0:
        area = 1.0
    return max(area, MINIMUM_SEED_FLOW)


def _safe_flow(value: float | None) -> float | None:
    """Clamp flow values used for output artifacts."""

    if value is None:
        return None
    try:
        flow = float(value)
    except (TypeError, ValueError):
        return None
    if math.isnan(flow) or flow <= 0:
        return None
    return max(flow, MINIMUM_SCENARIO_FLOW)


def optional_float_value(row: dict[str, Any], key: str, default: float | None = None) -> float | None:
    value = row.get(key, default)
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def tailwater_values(row: dict[str, Any]) -> tuple[float, float]:
    ds_invert = optional_float_value(row, "DS Invert", DEFAULT_OUTLET_INVERT)
    ds_tailwater = optional_float_value(row, "DS_h")
    tailwater_value = (
        ds_tailwater if ds_tailwater is not None else (ds_invert if ds_invert is not None else DEFAULT_TAILWATER)
    )
    zero_tailwater = ds_invert if ds_invert is not None else tailwater_value
    return tailwater_value, zero_tailwater


def aep_flow_label(aep_text: str) -> str:
    cleaned: str = aep_text.strip().lower().rstrip("p")
    try:
        numeric = float(cleaned)
        label: str = f"{numeric:g}p"
    except ValueError:
        label = aep_text.strip() or "flow"
    return label.replace(" ", "")


def build_crossing(
    row: dict[str, Any],
    inputs: CrossingInputs,
    flow_value: float,
) -> tuple[Hy8Project, CulvertCrossing, float, int, CulvertBarrel]:
    crossing_name: str = crossing_label(row)
    try:
        barrels = int(float(row["Barrels"]))
        diameter = float(row["Diameter (m)"])
    except (KeyError, TypeError, ValueError) as exc:
        raise ValueError(f"Crossing '{crossing_name}' is missing barrel or diameter data: {exc}") from exc

    project = Hy8Project(title=f"Excel demo - {crossing_name}", units=UnitSystem.SI, exit_loss_option=0)
    crossing: CulvertCrossing = CulvertCrossing(name=crossing_name)
    project.crossings.append(crossing)

    initial_flow: float = flow_value if flow_value > 0 else 0.0
    flow_def = FlowDefinition(method=FlowMethod.USER_DEFINED, user_values=[initial_flow])
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


def create_project_crossing(
    row: dict[str, Any],
    *,
    scenario_label: str,
    tailwater: float,
    flow: float | None,
) -> CulvertCrossing | None:
    """Build a standalone crossing for inclusion in the final HY-8 project."""

    safe_flow: float | None = _safe_flow(value=flow)
    if safe_flow is None:
        return None
    inputs: CrossingInputs = inputs_from_row(row, tailwater=tailwater)
    _, crossing, _, _, _ = build_crossing(row, inputs, safe_flow)
    crossing.name = f"{crossing_label(row)} - {scenario_label}"
    flow_def = FlowDefinition(method=FlowMethod.USER_DEFINED)
    label: str | None = normalize_field(row=row, key="aep_text") or None
    flow_def.add_user_flow(value=safe_flow, label=label)
    crossing.flow = flow_def
    crossing.tailwater.set_constant(elevation=tailwater, invert=tailwater)
    return crossing


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


def compute_metrics(result: HydraulicsResult, diameter: float, inlet_invert: float) -> tuple[float, float, float]:
    hw_level: float = result.computed_headwater
    hw_ratio: float = (hw_level - inlet_invert) / diameter if diameter else float("nan")
    velocity: float = result.row.velocity if result.row else float("nan")
    return hw_level, hw_ratio, velocity


def to_scenario_outcome(
    result: HydraulicsResult,
    diameter: float,
    inlet_invert: float,
) -> ScenarioOutcome:
    hw_level, hw_ratio, velocity = compute_metrics(result=result, diameter=diameter, inlet_invert=inlet_invert)
    hw_row: Hy8ResultRow | None = result.row
    flow_type: str | None = hw_row.flow_type if hw_row else None
    overtopping = bool(hw_row and hw_row.overtopping)
    return ScenarioOutcome(
        computed_flow=result.computed_flow,
        headwater=hw_level,
        headwater_ratio=hw_ratio,
        velocity=velocity,
        flow_type=flow_type,
        overtopping=overtopping,
        workspace=result.workspace,
    )


def describe_scenario(label: str, outcome: ScenarioOutcome) -> None:
    print(f"  {label}:")
    if outcome.computed_flow is None and outcome.headwater is None:
        print("    Result unavailable.")
        return
    if outcome.computed_flow is not None:
        print(f"    Computed flow (m^3/s): {outcome.computed_flow:.4f}")
    if outcome.headwater is not None:
        print(f"    Headwater elevation (m): {outcome.headwater:.4f}")
    if outcome.headwater_ratio is not None:
        print(f"    HW:D ratio: {outcome.headwater_ratio:.4f}")
    if outcome.velocity is not None:
        print(f"    Outlet velocity (m/s): {outcome.velocity:.4f}")
    if outcome.flow_type:
        print(f"    Flow type: {outcome.flow_type}")
    if outcome.overtopping:
        print("    Warning: HY-8 indicates overtopping.")


def write_results(outcomes: list[CrossingOutcome], path: Path) -> None:
    if not outcomes:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer: csv.DictWriter[str] = csv.DictWriter(handle, fieldnames=RESULT_FIELDNAMES)
        writer.writeheader()
        for outcome in outcomes:
            writer.writerow(outcome.to_row())


def write_final_hy8_project(
    crossing_name: str,
    rows: list[dict[str, Any]],
    outcomes: list[CrossingOutcome],
) -> Path | None:
    """Create and save a consolidated HY-8 project for the crossing."""

    project = Hy8Project(title=f"{crossing_name} Results", units=UnitSystem.SI, exit_loss_option=0)
    for row, outcome in zip(rows, outcomes):
        if not outcome:
            continue
        tailwater_value, zero_tailwater = tailwater_values(row)
        scenario_entries: list[tuple[str, float, float | None]] = [
            (FLOW_DS_TW_PREFIX, tailwater_value, outcome.q_tailwater.computed_flow),
            (FLOW_ZERO_TW_PREFIX, zero_tailwater, outcome.q_zero_tailwater.computed_flow),
            (HW_DATA_LABEL, tailwater_value, outcome.hw_data_tailwater.computed_flow),
            (HW_RATIO_LABEL, zero_tailwater, outcome.hw_ratio_no_tailwater.computed_flow),
        ]
        for label, tailwater, flow in scenario_entries:
            crossing: CulvertCrossing | None = create_project_crossing(
                row=row,
                scenario_label=label,
                tailwater=tailwater,
                flow=flow,
            )
            if crossing:
                project.crossings.append(crossing)
    if not project.crossings:
        return None
    PROJECT_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    path: Path = PROJECT_OUTPUT_DIR / f"{sanitize_workspace_name(name=crossing_name)}.hy8"
    Hy8FileWriter(project=project).write(output_path=path, overwrite=True)
    print(f"Final HY-8 project saved: {path}")
    return path


def make_failure_outcome(row: dict[str, Any], error: Exception) -> CrossingOutcome:
    crossing_name: str = normalize_field(row, "Crossing") or "<unknown>"
    return CrossingOutcome(
        crossing=crossing_name,
        aep=normalize_field(row, "aep_text"),
        adopted_flow=normalize_field(row, "Adopted Flow (m^3/s)"),
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
        us_headwater=None,
        status="Failed",
        error_message=str(error),
        q_tailwater=ScenarioOutcome(),
        q_zero_tailwater=ScenarioOutcome(),
        hw_data_tailwater=ScenarioOutcome(),
        hw_ratio_no_tailwater=ScenarioOutcome(),
    )


def run_crossing(
    row: dict[str, Any],
    hy8_path: Path | None,
    *,
    keep_workspace: bool,
    workspace_root: Path | None,
    fixed_flow_overrides: tuple[ScenarioOutcome, ScenarioOutcome] | None = None,
) -> CrossingOutcome:
    base_crossing_name: str = normalize_field(row=row, key="Crossing") or "<unknown>"
    crossing_name: str = crossing_label(row=row)
    aep_text: str = normalize_field(row=row, key="aep_text")
    flow_value: float = _flow_value(row=row)

    def optional_float(key: str, default: float | None = None) -> float | None:
        value = row.get(key, default)
        try:
            return float(value)
        except (TypeError, ValueError):
            return default

    ds_invert = optional_float("DS Invert", DEFAULT_OUTLET_INVERT)
    ds_tailwater = optional_float("DS_h")
    tailwater_value = (
        ds_tailwater if ds_tailwater is not None else (ds_invert if ds_invert is not None else DEFAULT_TAILWATER)
    )
    zero_tailwater = ds_invert if ds_invert is not None else tailwater_value
    us_headwater = optional_float("US_h")
    inputs = inputs_from_row(row, tailwater=tailwater_value)

    project, crossing, diameter, _, primary_barrel = build_crossing(row, inputs, flow_value)
    flow_hint = _flow_seed_hint(flow_value, primary_barrel)
    workspace: Path | None = workspace_for_crossing(root=workspace_root, name=crossing.name)
    barrel_length = max(0.0, primary_barrel.outlet_invert_station - primary_barrel.inlet_invert_station)
    roadway_width = crossing.roadway.width
    roadway_elevation = crossing.roadway.elevations[0] if crossing.roadway.elevations else None
    status = "Success"
    error_messages: list[str] = []

    print(f"Crossing: {crossing.name}")
    if aep_text:
        print(f"  AEP: {aep_text}")
    print(f"  Adopted flow (m^3/s): {flow_value:.4f}")
    if flow_value <= 0:
        print("  Warning: Adopted flow is non-positive; using {:.4f} m^3/s to seed headwater solves.".format(flow_hint))

    scenario_workspaces: dict[str, Path | None] = {
        HW_DATA_LABEL: workspace_for_scenario(workspace, HW_DATA_LABEL),
        HW_RATIO_LABEL: workspace_for_scenario(workspace, HW_RATIO_LABEL),
    }

    if fixed_flow_overrides:
        q_tailwater, q_zero_tailwater = fixed_flow_overrides
    else:
        q_tailwater, q_zero_tailwater = run_fixed_flow_for_row(
            row,
            hy8_path=hy8_path,
            workspace_root=workspace,
            keep_workspace=keep_workspace,
        )
    describe_scenario(label=FLOW_DS_TW_PREFIX, outcome=q_tailwater)
    describe_scenario(label=FLOW_ZERO_TW_PREFIX, outcome=q_zero_tailwater)

    if us_headwater is None:
        raise ValueError(f"Crossing '{crossing_name}' is missing a US headwater level.")
    set_tailwater(crossing=crossing, elevation=tailwater_value)
    hw_data_tailwater: ScenarioOutcome = ScenarioOutcome()
    try:
        hw_data_result: HydraulicsResult = crossing.q_from_hw(
            hw=us_headwater,
            q_hint=flow_hint,
            hy8=hy8_path,
            project=project,
            keep_files=keep_workspace,
            workspace=scenario_workspaces[HW_DATA_LABEL],
        )
        hw_data_tailwater = to_scenario_outcome(
            result=hw_data_result, diameter=diameter, inlet_invert=inputs.inlet_invert
        )
    except FlowSearchError as exc:
        status = "Failed"
        error_messages.append(f"{HW_DATA_LABEL} search failed: {exc}")
    describe_scenario(HW_DATA_LABEL, hw_data_tailwater)

    ratio_headwater = inputs.inlet_invert + (HEADWALL_RATIO_MULTIPLIER * diameter)
    set_tailwater(crossing, zero_tailwater)
    hw_ratio_no_tailwater: ScenarioOutcome = ScenarioOutcome()
    try:
        hw_ratio_result: HydraulicsResult = crossing.q_from_hw(
            hw=ratio_headwater,
            q_hint=flow_hint,
            hy8=hy8_path,
            project=project,
            keep_files=keep_workspace,
            workspace=scenario_workspaces[HW_RATIO_LABEL],
        )
        hw_ratio_no_tailwater = to_scenario_outcome(
            result=hw_ratio_result, diameter=diameter, inlet_invert=inputs.inlet_invert
        )
    except FlowSearchError as exc:
        status = "Failed"
        error_messages.append(f"{HW_RATIO_LABEL} search failed: {exc}")
    describe_scenario(HW_RATIO_LABEL, hw_ratio_no_tailwater)
    print()

    error_message: str | None = "; ".join(error_messages) if error_messages else None

    return CrossingOutcome(
        crossing=base_crossing_name,
        aep=aep_text,
        adopted_flow=normalize_field(row, "Adopted Flow (m^3/s)"),
        barrels=normalize_field(row, "Barrels"),
        diameter=normalize_field(row, "Diameter (m)"),
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
        tailwater_elevation=tailwater_value,
        us_headwater=us_headwater,
        status=status,
        error_message=error_message,
        q_tailwater=q_tailwater,
        q_zero_tailwater=q_zero_tailwater,
        hw_data_tailwater=hw_data_tailwater,
        hw_ratio_no_tailwater=hw_ratio_no_tailwater,
    )


def _crossing_worker(
    payload: tuple[list[int], list[dict[str, Any]], str | None, bool, str | None],
) -> tuple[list[int], list[CrossingOutcome], str | None]:
    indices, rows, hy8_str, keep_workspace, workspace_str = payload
    hy8_path = Path(hy8_str) if hy8_str else None
    workspace_root = Path(workspace_str) if workspace_str else None
    try:
        outcomes = run_crossing_group(
            rows=rows,
            hy8_path=hy8_path,
            keep_workspace=keep_workspace,
            workspace_root=workspace_root,
        )
        return indices, outcomes, None
    except Exception as exc:  # pragma: no cover - worker best effort
        failures = [make_failure_outcome(row, exc) for row in rows]
        return indices, failures, str(exc)


def run_crossing_group(
    rows: list[dict[str, Any]],
    hy8_path: Path | None,
    *,
    keep_workspace: bool,
    workspace_root: Path | None,
) -> list[CrossingOutcome]:
    if not rows:
        return []
    crossing_workspace = workspace_for_crossing(workspace_root, normalize_field(rows[0], "Crossing"))
    fixed_flow_map = run_fixed_flow_scenarios(
        rows,
        hy8_path=hy8_path,
        workspace_root=crossing_workspace,
        keep_workspace=keep_workspace,
    )
    outcomes: list[CrossingOutcome] = []
    for row in rows:
        label = aep_flow_label(normalize_field(row, "aep_text"))
        fixed_outcomes = fixed_flow_map.get(label)
        outcome = run_crossing(
            row=row,
            hy8_path=hy8_path,
            keep_workspace=keep_workspace,
            workspace_root=workspace_root,
            fixed_flow_overrides=fixed_outcomes,
        )
        outcomes.append(outcome)
    crossing_name = normalize_field(rows[0], "Crossing") or "crossing"
    write_final_hy8_project(crossing_name, rows, outcomes)
    return outcomes


def main() -> None:
    rows: list[dict[str, Any]] = load_rows(excel_path=EXCEL_PATH)
    hy8_path: Path | None = Path(HY8_EXE) if HY8_EXE else None

    rows_to_run: list[dict[str, Any]] = select_rows(rows=rows, name=CROSSING_NAME)
    rows_to_run = limit_crossings(rows_to_run, CROSSING_LIMIT)
    workspace_root: Path | None = WORKSPACE_PATH if KEEP_WORKSPACE else None
    if workspace_root:
        workspace_root.mkdir(parents=True, exist_ok=True)

    hy8_str: str | None = str(hy8_path) if hy8_path else None
    workspace_str: str | None = str(workspace_root) if workspace_root else None
    grouped: dict[str, list[tuple[int, dict[str, Any]]]] = {}
    for index, row in enumerate(rows_to_run):
        key = normalize_field(row, "Crossing")
        grouped.setdefault(key, []).append((index, row))

    payloads: list[tuple[list[int], list[dict[str, Any]], str | None, bool, str | None]] = []
    for entries in grouped.values():
        indices = [index for index, _ in entries]
        group_rows = [row for _, row in entries]
        payloads.append((indices, group_rows, hy8_str, KEEP_WORKSPACE, workspace_str))

    results: list[CrossingOutcome | None] = [None] * len(rows_to_run)
    had_errors = False
    if payloads:
        max_workers = min(MAX_WORKERS, len(payloads)) or 1
        with ProcessPoolExecutor(max_workers=max_workers) as executor:
            futures = [executor.submit(_crossing_worker, payload) for payload in payloads]
            for future in as_completed(futures):
                indices, outcome_list, error_message = future.result()
                for idx, outcome in zip(indices, outcome_list):
                    results[idx] = outcome
                if error_message:
                    crossing_name: str = normalize_field(rows_to_run[indices[0]], "Crossing") or "<unknown>"
                    print(f"Skipping '{crossing_name}': {error_message}", file=sys.stderr)
                    had_errors = True

    completed = [result for result in results if result]
    if completed:
        write_results(completed, RESULTS_OUTPUT)
        print(f"Results saved to: {RESULTS_OUTPUT}")
    else:
        print("No successful crossings; results file not created.")
    if had_errors:
        raise SystemExit("One or more crossings failed; see stderr for details.")


if __name__ == "__main__":
    main()
