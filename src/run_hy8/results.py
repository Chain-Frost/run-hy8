"""Parsers and helpers for consuming HY-8 result files."""

from __future__ import annotations

import math
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal, TypedDict

ValueKey = Literal["flow", "headwater", "velocity"]
SummaryKey = Literal["roadway", "iterations"]

# Regex to find the start of a culvert summary table and capture the culvert name.
RST_DIALOG_RE: re.Pattern[str] = re.compile(pattern=r"Dialog:\s+Culvert Summary Table - (?P<name>.+)")
# Regex to find the water-surface table that contains full/free barrel lengths.
RST_PROFILE_RE: re.Pattern[str] = re.compile(pattern=r"Dialog:\s+Water Surface Profile Table - (?P<name>.+)")
# The zero-based culvert index is emitted immediately before each culvert table.
RST_CULVERT_INDEX_RE: re.Pattern[str] = re.compile(pattern=r"Culvert:\s+(?P<index>\d+)")
# HY-8 decorates some calculated depths with one or more asterisks. Preserve the
# marker separately while still making the numeric portion available to callers.
RST_REPORTED_VALUE_RE: re.Pattern[str] = re.compile(
    pattern=r"(?P<value>[+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[Ee][+-]?\d+)?)(?P<qualifier>\*+)?"
)
# Labels for numeric data series in the .rst file.
RST_VALUE_LABELS: dict[ValueKey, str] = {
    "flow": "Total Discharge (",
    "headwater": "Headwater Elevation (",
    "velocity": "Outlet Velocity (",
}
RST_TEXT_LABELS: dict[str, str] = {
    "flow_type": "Flow Type",
}
# Regex to find the start of a crossing summary and capture the crossing name.
SUMMARY_RE: re.Pattern[str] = re.compile(pattern=r"Dialog:\s+Summary of Flows at Crossing - (?P<name>.+)")
# Labels for summary data series in the .rst file.
SUMMARY_LABELS: dict[SummaryKey, str] = {
    "roadway": "Roadway Discharge (",
    "iterations": "Iterations",
}


class Hy8CulvertSeries(TypedDict, total=False):
    """Per-culvert result vectors collected from multiple HY-8 report tables."""

    index: int
    name: str
    discharge: list[float]
    inlet_control_depth: list[float]
    inlet_control_depth_qualifier: list[str]
    outlet_control_depth: list[float]
    outlet_control_depth_qualifier: list[str]
    full_length: list[float]
    full_length_qualifier: list[str]
    free_length: list[float]
    free_length_qualifier: list[str]
    outlet_velocity: list[float]
    flow_type: list[str]


class Hy8Series(TypedDict, total=False):
    """Normalized HY-8 result vectors keyed by crossing name."""

    flow: list[float]
    headwater: list[float]
    velocity: list[float]
    roadway: list[float]
    iterations: list[str]
    flow_type: list[str]
    culverts: list[Hy8CulvertSeries]


def parse_rst(path: Path) -> dict[str, Hy8Series]:
    """Parse a .rst report file into a dictionary of data series keyed by crossing name.

    The .rst file contains summary tables for each crossing. This function iterates
    through the file, identifies the current crossing, and extracts the comma-separated
    data for flow, headwater, velocity, etc.
    """
    data: dict[str, Hy8Series] = {}
    summary_crossing: str | None = None
    current_culvert_index: int | None = None
    current_culvert: Hy8CulvertSeries | None = None
    current_table: Literal["crossing", "culvert", "profile"] | None = None
    with path.open("r", encoding="utf-8", errors="ignore") as handle:
        for raw_line in handle:
            line: str = raw_line.strip()
            if not line:
                continue
            culvert_index_match: re.Match[str] | None = RST_CULVERT_INDEX_RE.fullmatch(string=line)
            if culvert_index_match:
                current_culvert_index = int(culvert_index_match.group("index"))
                continue
            # Check if we are in a "Summary of Flows" block.
            summary_match: re.Match[str] | None = SUMMARY_RE.match(string=line)
            if summary_match:
                crossing_name: str = summary_match.group("name").strip()
                summary_crossing = crossing_name
                current_culvert = None
                current_table = "crossing"
                data.setdefault(crossing_name, Hy8Series(culverts=[]))
                continue
            # If in a summary block, parse the roadway discharge and iteration counts.
            if summary_crossing and current_table == "crossing":
                if line.startswith(RST_VALUE_LABELS["flow"]):
                    data[summary_crossing]["flow"] = parse_series(line)
                elif line.startswith(RST_VALUE_LABELS["headwater"]):
                    data[summary_crossing]["headwater"] = parse_series(line)
                for key, label in SUMMARY_LABELS.items():
                    if line.startswith(label):
                        if key == "iterations":
                            data[summary_crossing][key] = parse_text_series(line)
                        else:
                            data[summary_crossing][key] = parse_series(line)
            # Check if we are in a "Culvert Summary Table" block.
            culvert_match: re.Match[str] | None = RST_DIALOG_RE.match(line)
            if culvert_match:
                current_table = "culvert"
                current_culvert = _get_culvert_series(
                    data=data,
                    crossing_name=summary_crossing,
                    culvert_index=current_culvert_index,
                    culvert_name=culvert_match.group("name").strip(),
                )
                continue
            profile_match: re.Match[str] | None = RST_PROFILE_RE.match(line)
            if profile_match:
                current_table = "profile"
                current_culvert = _get_culvert_series(
                    data=data,
                    crossing_name=summary_crossing,
                    culvert_index=current_culvert_index,
                    culvert_name=profile_match.group("name").strip(),
                )
                continue
            if line.startswith("Dialog:"):
                current_culvert = None
                current_table = None
                continue
            if current_culvert is None or summary_crossing is None:
                continue
            if current_table == "culvert":
                _parse_culvert_summary_line(
                    line=line,
                    crossing=data[summary_crossing],
                    culvert=current_culvert,
                )
            elif current_table == "profile":
                _parse_culvert_profile_line(line=line, culvert=current_culvert)
    return data


def _get_culvert_series(
    *,
    data: dict[str, Hy8Series],
    crossing_name: str | None,
    culvert_index: int | None,
    culvert_name: str,
) -> Hy8CulvertSeries | None:
    """Return the matching per-culvert collection, creating it when needed."""
    if crossing_name is None or culvert_index is None:
        return None
    crossing: Hy8Series = data.setdefault(crossing_name, Hy8Series(culverts=[]))
    culverts: list[Hy8CulvertSeries] = crossing.setdefault("culverts", [])
    for culvert in culverts:
        if culvert.get("index") == culvert_index:
            return culvert
    culvert = Hy8CulvertSeries(index=culvert_index, name=culvert_name)
    culverts.append(culvert)
    return culvert


def _parse_culvert_summary_line(*, line: str, crossing: Hy8Series, culvert: Hy8CulvertSeries) -> None:
    """Collect legacy crossing fields and culvert-specific summary fields."""
    if line.startswith("Culvert Discharge"):
        culvert["discharge"] = parse_series(line)
    elif line.startswith("Inlet Control Depth"):
        _store_reported_series(culvert, "inlet_control_depth", line)
    elif line.startswith("Outlet Control Depth"):
        _store_reported_series(culvert, "outlet_control_depth", line)
    elif line.startswith(RST_VALUE_LABELS["velocity"]):
        values: list[float] = parse_series(line)
        culvert["outlet_velocity"] = values
        # Preserve the established flat field. For multi-culvert crossings this
        # continues to represent the final culvert in the report.
        crossing["velocity"] = values
    elif line.startswith(RST_TEXT_LABELS["flow_type"]):
        values_text: list[str] = parse_text_series(line)
        culvert["flow_type"] = values_text
        crossing["flow_type"] = values_text


def _parse_culvert_profile_line(*, line: str, culvert: Hy8CulvertSeries) -> None:
    """Collect full and free barrel lengths from a water-surface profile table."""
    if line.startswith("Length Full"):
        _store_reported_series(culvert, "full_length", line)
    elif line.startswith("Length Free"):
        _store_reported_series(culvert, "free_length", line)


def _store_reported_series(
    culvert: Hy8CulvertSeries,
    key: Literal["inlet_control_depth", "outlet_control_depth", "full_length", "free_length"],
    line: str,
) -> None:
    """Store numeric HY-8 values alongside any asterisk qualifiers."""
    values, qualifiers = _parse_reported_series(line)
    culvert[key] = values
    if key == "inlet_control_depth":
        culvert["inlet_control_depth_qualifier"] = qualifiers
    elif key == "outlet_control_depth":
        culvert["outlet_control_depth_qualifier"] = qualifiers
    elif key == "full_length":
        culvert["full_length_qualifier"] = qualifiers
    else:
        culvert["free_length_qualifier"] = qualifiers


def parse_series(line: str) -> list[float]:
    """Convert a comma-separated value line from an HY-8 report into a list of floats.

    It handles 'nan' strings and empty parts by converting them to `math.nan`.
    The first part of the line (the label) is skipped.
    """
    parts: list[str] = line.split(",")[1:]
    values: list[float] = []
    for part in parts:
        stripped_part = part.strip()
        if not stripped_part or stripped_part.lower() == "nan":
            values.append(math.nan)
        else:
            try:
                values.append(float(stripped_part))
            except ValueError:
                values.append(math.nan)
    return values


def _parse_reported_series(line: str) -> tuple[list[float], list[str]]:
    """Parse numeric values and retain HY-8's trailing asterisk qualifiers."""
    parts: list[str] = line.split(",")[1:]
    values: list[float] = []
    qualifiers: list[str] = []
    for raw_part in parts:
        part: str = raw_part.strip()
        match: re.Match[str] | None = RST_REPORTED_VALUE_RE.fullmatch(part)
        if match is None:
            values.append(math.nan)
            qualifiers.append("")
            continue
        values.append(float(match.group("value")))
        qualifiers.append(match.group("qualifier") or "")
    return values, qualifiers


def parse_text_series(line: str) -> list[str]:
    """Return trimmed string entries from a HY-8 comma-separated line."""
    parts: list[str] = line.split(",")[1:]
    return [part.strip() for part in parts if part.strip()]


def _format_float(value: float, unit: str | None = None) -> str:
    """Format a float for display, handling NaN values."""
    if math.isnan(value):
        return "nan"
    formatted = f"{value:.3f}"
    return f"{formatted}{unit}" if unit else formatted


@dataclass(slots=True)
class FlowProfile:
    """Single flow profile row emitted by HY-8's .rsql output."""

    flow: float = math.nan
    headwater_depth: float = math.nan
    flow_type: str = ""
    overtopping: bool = False

    def __repr__(self) -> str:
        return (
            f"{self.__class__.__name__}(flow={_format_float(self.flow)} cms, "
            f"headwater_depth={_format_float(self.headwater_depth, ' m')}, "
            f"flow_type={self.flow_type!r}, overtopping={self.overtopping})"
        )

    def __str__(self) -> str:
        overtopping_note = " (overtopping)" if self.overtopping else ""
        return f"{_format_float(self.flow)} cms @ {self._present_depth()}{overtopping_note}"

    def _present_depth(self) -> str:
        return _format_float(self.headwater_depth, " m")


@dataclass(slots=True)
class Hy8CulvertResult:
    """HY-8 diagnostics for one culvert at one crossing flow."""

    index: int
    name: str
    discharge: float = math.nan
    inlet_control_depth: float = math.nan
    inlet_control_depth_qualifier: str = ""
    outlet_control_depth: float = math.nan
    outlet_control_depth_qualifier: str = ""
    full_length: float = math.nan
    full_length_qualifier: str = ""
    free_length: float = math.nan
    free_length_qualifier: str = ""
    outlet_velocity: float = math.nan
    flow_type: str = ""


def _culvert_result_list() -> list[Hy8CulvertResult]:
    """Return an empty, strictly typed per-row culvert collection."""
    return []


@dataclass(slots=True)
class Hy8ResultRow:
    """Merged .rst/.rsql row describing HY-8 results for a single flow."""

    flow: float = math.nan
    headwater_elevation: float = math.nan
    velocity: float = math.nan
    roadway_discharge: float = math.nan
    iterations: str = ""
    headwater_depth: float = math.nan
    flow_type: str = ""
    overtopping: bool = False
    culverts: list[Hy8CulvertResult] = field(default_factory=_culvert_result_list)

    def __repr__(self) -> str:
        return (
            f"{self.__class__.__name__}(flow={_format_float(self.flow)} cms, "
            f"headwater={_format_float(self.headwater_elevation, ' m')}, "
            f"velocity={_format_float(self.velocity, ' m/s')}, "
            f"roadway={_format_float(self.roadway_discharge)} cms, "
            f"overtopping={self.overtopping})"
        )

    def __str__(self) -> str:
        return (
            f"{_format_float(self.flow)} cms -> headwater {_format_float(self.headwater_elevation, ' m')}, "
            f"velocity {_format_float(self.velocity, ' m/s')}"
        )


class Hy8Results:
    """Aggregated HY-8 output that merges .rst and .rsql data."""

    def __init__(
        self,
        entry: Hy8Series,
        profiles: list[FlowProfile] | None = None,
    ) -> None:
        flows: list[float] = entry.get("flow") or []
        headwaters: list[float] = entry.get("headwater") or []
        velocities: list[float] = entry.get("velocity") or []
        roadway: list[float] = entry.get("roadway") or []
        iterations: list[str] = entry.get("iterations") or []
        flow_types: list[str] = entry.get("flow_type") or []
        culvert_series: list[Hy8CulvertSeries] = entry.get("culverts") or []
        profiles = profiles or []
        self.rows: list[Hy8ResultRow] = []
        for idx, flow in enumerate(flows):
            head = headwaters[idx] if idx < len(headwaters) else math.nan
            vel = velocities[idx] if idx < len(velocities) else math.nan
            roadway_val = roadway[idx] if idx < len(roadway) else math.nan
            iteration = iterations[idx] if idx < len(iterations) else ""
            profile: FlowProfile | None = nearest_profile(profiles, flow)
            flow_type_text: str = flow_types[idx] if idx < len(flow_types) else ""
            profile_type: str = profile.flow_type if profile else ""
            row: Hy8ResultRow = Hy8ResultRow(
                flow=flow,
                headwater_elevation=head,
                velocity=vel,
                roadway_discharge=roadway_val,
                iterations=iteration,
                headwater_depth=profile.headwater_depth if profile else math.nan,
                flow_type=flow_type_text or profile_type,
                overtopping=profile.overtopping if profile else False,
                culverts=[_culvert_result_at(culvert, idx) for culvert in culvert_series],
            )
            if iteration and "overtopping" in iteration.lower():
                # The .rst iteration string sometimes contains an "overtopping" note.
                row.overtopping = True
            self.rows.append(row)

    def __len__(self) -> int:
        return len(self.rows)

    def __repr__(self) -> str:
        range_label = self._flow_range_label() or "empty"
        return f"{self.__class__.__name__}(rows={len(self.rows)}, flows={range_label} cms)"

    def __str__(self) -> str:
        range_label = self._flow_range_label() or "empty"
        return f"{self.__class__.__name__} with {len(self)} rows (flows={range_label} cms)"

    def _flow_range_label(self) -> str | None:
        """Generate a string representing the min and max flow in the results."""
        flows = [row.flow for row in self.rows if not math.isnan(row.flow)]
        if not flows:
            return None
        return f"{_format_float(flows[0])}↔{_format_float(flows[-1])}"

    def nearest(self, target: float) -> Hy8ResultRow | None:
        """Return the result row whose flow is nearest to the target."""
        best_row: Hy8ResultRow | None = None
        best_delta = float("inf")
        for row in self.rows:
            if math.isnan(row.flow):
                continue
            delta: float = abs(row.flow - target)
            if delta < best_delta:
                best_delta: float = delta
                best_row = row
        return best_row

    def roadway_max(self) -> float:
        """Return the maximum reported roadway discharge."""
        values: list[float] = [row.roadway_discharge for row in self.rows if not math.isnan(row.roadway_discharge)]
        return max(values) if values else 0.0


def _culvert_result_at(series: Hy8CulvertSeries, index: int) -> Hy8CulvertResult:
    """Select one flow column from a culvert's parsed result vectors."""
    return Hy8CulvertResult(
        index=series.get("index", 0),
        name=series.get("name", ""),
        discharge=_float_at(series.get("discharge"), index),
        inlet_control_depth=_float_at(series.get("inlet_control_depth"), index),
        inlet_control_depth_qualifier=_text_at(series.get("inlet_control_depth_qualifier"), index),
        outlet_control_depth=_float_at(series.get("outlet_control_depth"), index),
        outlet_control_depth_qualifier=_text_at(series.get("outlet_control_depth_qualifier"), index),
        full_length=_float_at(series.get("full_length"), index),
        full_length_qualifier=_text_at(series.get("full_length_qualifier"), index),
        free_length=_float_at(series.get("free_length"), index),
        free_length_qualifier=_text_at(series.get("free_length_qualifier"), index),
        outlet_velocity=_float_at(series.get("outlet_velocity"), index),
        flow_type=_text_at(series.get("flow_type"), index),
    )


def _float_at(values: list[float] | None, index: int) -> float:
    """Return a numeric vector item or NaN when HY-8 omitted the column."""
    return values[index] if values is not None and index < len(values) else math.nan


def _text_at(values: list[str] | None, index: int) -> str:
    """Return a text vector item or an empty string when the column is absent."""
    return values[index] if values is not None and index < len(values) else ""


def parse_rsql(path: Path) -> dict[str, list[FlowProfile]]:
    """Parse a .rsql file into a dictionary of FlowProfile objects grouped by crossing name.

    The .rsql file contains detailed, line-by-line output for each flow profile
    calculation, which is more detailed than the summary in the .rst file.
    """
    data: dict[str, list[FlowProfile]] = {}
    if not path.exists():
        return data
    current_crossing: str | None = None
    current_profile: FlowProfile | None = None
    with path.open("r", encoding="utf-8", errors="ignore") as handle:
        for raw_line in handle:
            line: str = raw_line.strip()
            if not line:
                continue
            if line.startswith("Crossing:"):
                current_crossing = line.split(":", 1)[1].strip()
                continue
            if line.startswith("FlowProfileName:"):
                current_profile = FlowProfile()
                continue
            if current_profile is None or current_crossing is None:
                continue
            if line.startswith("EndFlowProfile"):
                data.setdefault(current_crossing, []).append(current_profile)
                current_profile = None
                continue
            if ":" not in line:
                continue
            raw_key, raw_value = line.split(":", 1)
            key: str = raw_key.strip()
            value: str = raw_value.strip()
            if key == "FlowProfileFlow":
                try:
                    current_profile.flow = float(value)
                except ValueError:
                    current_profile.flow = math.nan
            elif key == "HeadwaterToDepth":
                try:
                    current_profile.headwater_depth = float(value)
                except ValueError:
                    current_profile.headwater_depth = math.nan
            elif key == "FlowType":
                current_profile.flow_type = value
            elif key == "Overtops":
                current_profile.overtopping = value.lower() == "true"
    return data


def nearest_profile(profiles: list[FlowProfile], target: float) -> FlowProfile | None:
    """Return the profile whose flow is closest to the requested value."""
    best: FlowProfile | None = None
    best_delta = float("inf")
    for profile in profiles:
        if math.isnan(profile.flow):
            continue
        delta: float = abs(profile.flow - target)
        if delta < best_delta:
            best_delta: float = delta
            best = profile
    return best


__all__: list[str] = [
    "FlowProfile",
    "Hy8CulvertResult",
    "Hy8CulvertSeries",
    "Hy8ResultRow",
    "Hy8Results",
    "Hy8Series",
    "parse_rsql",
    "parse_rst",
]
