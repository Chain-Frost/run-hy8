"""Parsers and helpers for consuming HY-8 result files."""

from __future__ import annotations

import math
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Literal, TypedDict


ValueKey = Literal["flow", "headwater", "velocity"]
SummaryKey = Literal["roadway", "iterations"]

RST_DIALOG_RE: re.Pattern[str] = re.compile(pattern=r"Dialog:\s+Culvert Summary Table - (?P<name>.+)")
RST_VALUE_LABELS: dict[ValueKey, str] = {
    "flow": "Total Discharge (cms)",
    "headwater": "Headwater Elevation (m)",
    "velocity": "Outlet Velocity (m/s)",
}
SUMMARY_RE: re.Pattern[str] = re.compile(pattern=r"Dialog:\s+Summary of Flows at Crossing - (?P<name>.+)")
SUMMARY_LABELS: dict[SummaryKey, str] = {
    "roadway": "Roadway Discharge (cms)",
    "iterations": "Iterations",
}


class Hy8Series(TypedDict, total=False):
    flow: list[float]
    headwater: list[float]
    velocity: list[float]
    roadway: list[float]
    iterations: list[str]


def parse_rst(path: Path) -> dict[str, Hy8Series]:
    data: dict[str, Hy8Series] = {}
    summary_crossing: str | None = None
    capturing_culvert: str | None = None
    with path.open("r", encoding="utf-8", errors="ignore") as handle:
        for raw_line in handle:
            line: str = raw_line.strip()
            if not line:
                continue
            summary_match: re.Match[str] | None = SUMMARY_RE.match(string=line)
            if summary_match:
                crossing_name: str = summary_match.group("name").strip()
                summary_crossing = crossing_name
                capturing_culvert = None
                data.setdefault(crossing_name, Hy8Series())
                continue
            if summary_crossing:
                for key, label in SUMMARY_LABELS.items():
                    if line.startswith(label):
                        if key == "iterations":
                            data[summary_crossing][key] = parse_text_series(line)
                        else:
                            data[summary_crossing][key] = parse_series(line)
            culvert_match: re.Match[str] | None = RST_DIALOG_RE.match(line)
            if culvert_match:
                culvert_crossing: str | None = summary_crossing
                capturing_culvert = culvert_crossing
                if culvert_crossing:
                    data.setdefault(culvert_crossing, Hy8Series())
                continue
            if capturing_culvert is None:
                continue
            for key, label in RST_VALUE_LABELS.items():
                if line.startswith(label):
                    series: list[float] = parse_series(line)
                    data[capturing_culvert][key] = series
    return data


def parse_series(line: str) -> list[float]:
    parts: list[str] = line.split(",")[1:]
    values: list[float] = []
    for part in parts:
        part: str = part.strip()
        if not part or part.lower() == "nan":
            values.append(math.nan)
        else:
            try:
                values.append(float(part))
            except ValueError:
                values.append(math.nan)
    return values


def parse_text_series(line: str) -> list[str]:
    parts: list[str] = line.split(",")[1:]
    return [part.strip() for part in parts if part.strip()]


@dataclass(slots=True)
class FlowProfile:
    flow: float = math.nan
    headwater_depth: float = math.nan
    flow_type: str = ""
    overtopping: bool = False


@dataclass(slots=True)
class Hy8ResultRow:
    flow: float = math.nan
    headwater_elevation: float = math.nan
    velocity: float = math.nan
    roadway_discharge: float = math.nan
    iterations: str = ""
    headwater_depth: float = math.nan
    flow_type: str = ""
    overtopping: bool = False


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
        profiles = profiles or []
        self.rows: list[Hy8ResultRow] = []
        for idx, flow in enumerate(flows):
            head = headwaters[idx] if idx < len(headwaters) else math.nan
            vel = velocities[idx] if idx < len(velocities) else math.nan
            roadway_val = roadway[idx] if idx < len(roadway) else math.nan
            iteration = iterations[idx] if idx < len(iterations) else ""
            profile: FlowProfile | None = nearest_profile(profiles, flow)
            row: Hy8ResultRow = Hy8ResultRow(
                flow=flow,
                headwater_elevation=head,
                velocity=vel,
                roadway_discharge=roadway_val,
                iterations=iteration,
                headwater_depth=profile.headwater_depth if profile else math.nan,
                flow_type=profile.flow_type if profile else "",
                overtopping=profile.overtopping if profile else False,
            )
            if iteration and "overtopping" in iteration.lower():
                row.overtopping = True
            self.rows.append(row)

    def nearest(self, target: float) -> Hy8ResultRow | None:
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
        values: list[float] = [row.roadway_discharge for row in self.rows if not math.isnan(row.roadway_discharge)]
        return max(values) if values else 0.0


def parse_rsql(path: Path) -> dict[str, list[FlowProfile]]:
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
    "Hy8ResultRow",
    "Hy8Results",
    "parse_rst",
    "parse_rsql",
]
