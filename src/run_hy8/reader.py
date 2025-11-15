"""Parsers for reading HY-8 project files."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from run_hy8.models import FlowDefinition, TailwaterDefinition

from .models import (
    CulvertBarrel,
    CulvertCrossing,
    CulvertMaterial,
    CulvertShape,
    FlowMethod,
    Hy8Project,
    RoadwaySurface,
    TailwaterType,
    UnitSystem,
)


def load_project_from_hy8(path: Path) -> Hy8Project:
    """Read a .hy8 file from disk and convert it into a Hy8Project."""
    parser: _Hy8Parser = _Hy8Parser.from_path(path=path)
    return parser.parse()


@dataclass
class _Hy8Card:
    key: str
    value: str


class _Hy8CardStream:
    """Iterates over HY-8 card/value pairs and exposes raw-line helpers."""

    def __init__(self, lines: list[str]) -> None:
        self._lines: list[str] = lines
        self._index = 0
        self._buffer: list[_Hy8Card] = []

    def next_card(self) -> _Hy8Card:
        if self._buffer:
            return self._buffer.pop()
        while self._index < len(self._lines):
            raw: str = self._lines[self._index]
            self._index += 1
            stripped: str = raw.strip()
            if not stripped:
                continue
            key, value = self._split_card(line=stripped)
            return _Hy8Card(key=key, value=value)
        raise StopIteration

    def push_back(self, card: _Hy8Card) -> None:
        self._buffer.append(card)

    def read_block(self, end_marker: str) -> list[str]:
        """Consume raw lines until `end_marker` is encountered (exclusive)."""
        contents: list[str] = []
        target: str = end_marker.strip().upper()
        while self._index < len(self._lines):
            raw: str = self._lines[self._index]
            self._index += 1
            stripped: str = raw.strip()
            if stripped.upper().startswith(target):
                trailing: str = stripped[len(end_marker) :].strip()
                if trailing:
                    self._buffer.append(_Hy8Card(key=end_marker, value=trailing))
                break
            contents.append(raw.rstrip("\n"))
        return contents

    def skip_until(self, target: str) -> None:
        """Skip raw lines until one matches the provided target text."""
        goal: str = target.strip().upper()
        while self._index < len(self._lines):
            raw: str = self._lines[self._index]
            self._index += 1
            if raw.strip().upper() == goal:
                break

    @staticmethod
    def _split_card(line: str) -> tuple[str, str]:
        if line.startswith("HY8PROJECTFILE"):
            return "HY8PROJECTFILE", line.removeprefix("HY8PROJECTFILE").strip()
        parts: list[str] = line.split(sep=None, maxsplit=1)
        if len(parts) == 1:
            return parts[0], ""
        return parts[0], parts[1]


class _Hy8Parser:
    """Stateful parser that converts HY-8 cards into Hy8Project instances."""

    def __init__(self, lines: Iterable[str], source: Path | None = None) -> None:
        self._lines: list[str] = list(lines)
        self._stream = _Hy8CardStream(lines=self._lines)
        self._source: Path | None = source

    @classmethod
    def from_path(cls, path: Path) -> "_Hy8Parser":
        text: str = path.read_text(encoding="utf-8", errors="ignore")
        return cls(text.splitlines(), source=path)

    def parse(self) -> Hy8Project:
        project = Hy8Project()
        self._consume_header()
        while True:
            try:
                card: _Hy8Card = self._stream.next_card()
            except StopIteration:
                break
            if card.key == "ENDPROJECTFILE":
                break
            if card.key == "STARTCROSSING":
                crossing: CulvertCrossing = self._parse_crossing(name=self._clean_string(raw=card.value))
                project.crossings.append(crossing)
                continue
            self._apply_project_card(project=project, card=card)
        return project

    def _consume_header(self) -> None:
        try:
            card: _Hy8Card = self._stream.next_card()
        except StopIteration as exc:  # pragma: no cover - defensive guard
            raise ValueError("HY-8 file is empty.") from exc
        if card.key != "HY8PROJECTFILE":
            raise ValueError(f"Expected HY8PROJECTFILE header, found '{card.key}'.")

    def _apply_project_card(self, project: Hy8Project, card: _Hy8Card) -> None:
        if card.key == "UNITS":
            project.units = (
                UnitSystem.SI if self._as_int(value=card.value) == UnitSystem.SI.project_flag else UnitSystem.ENGLISH
            )
        elif card.key == "EXITLOSSOPTION":
            project.exit_loss_option = self._as_int(value=card.value, default=0)
        elif card.key == "PROJTITLE":
            project.title = self._clean_string(raw=card.value)
        elif card.key == "PROJDESIGNER":
            project.designer = self._clean_string(raw=card.value)
        elif card.key == "STARTPROJNOTES":
            project.notes = self._collect_notes(inline_value=card.value, end_marker="ENDPROJNOTES")

    def _parse_crossing(self, name: str) -> CulvertCrossing:
        crossing = CulvertCrossing(name=name or "Crossing")
        pending_flow_values: list[float] = []
        while True:
            card: _Hy8Card = self._stream.next_card()
            key: str = card.key
            value: str = card.value
            if key == "ENDCROSSING":
                self._finalize_flow(crossing=crossing, user_values=pending_flow_values)
                return crossing
            if key == "STARTCROSSNOTES":
                crossing.notes = self._clean_string(raw=value)
            elif key == "DISCHARGERANGE":
                numbers: list[float] = self._floats(value=value, expected=3)
                if numbers:
                    crossing.flow.minimum = numbers[0]
                    if len(numbers) > 1:
                        crossing.flow.design = numbers[1]
                    if len(numbers) > 2:
                        crossing.flow.maximum = numbers[2]
            elif key == "DISCHARGEMETHOD":
                crossing.flow.method = (
                    FlowMethod.MIN_DESIGN_MAX if self._as_int(value=value) == 0 else FlowMethod.USER_DEFINED
                )
            elif key == "DISCHARGEXYUSER":
                pending_flow_values = self._read_flow_values(expected=self._as_int(value=value))
            elif key == "DISCHARGEXYUSER_Y" or key == "DISCHARGEXYUSER_NAME":
                # Residual cards when DISCHARGEXYUSER count is zero; ignore.
                continue
            elif key == "TAILWATERTYPE":
                crossing.tailwater.type = self._tailwater_type(value)
            elif key == "CHANNELGEOMETRY":
                numbers = self._floats(value=value, expected=5)
                if numbers:
                    tw: TailwaterDefinition = crossing.tailwater
                    tw.bottom_width = numbers[0]
                    if len(numbers) > 1:
                        tw.sideslope = numbers[1]
                    if len(numbers) > 2:
                        tw.channel_slope = numbers[2]
                    if len(numbers) > 3:
                        tw.manning_n = numbers[3]
                    if len(numbers) > 4:
                        tw.invert_elevation = numbers[4]
            elif key == "TWRATINGCURVE":
                stages: list[float] = self._floats(value=value)
                if stages:
                    crossing.tailwater.constant_elevation = stages[0]
            elif key == "RATINGCURVE":
                self._stream.skip_until(target="END RATINGCURVE")
            elif key == "ROADWAYSHAPE":
                crossing.roadway.shape = self._as_int(value=value, default=crossing.roadway.shape)
            elif key == "ROADWIDTH":
                crossing.roadway.width = self._as_float(value=value, default=crossing.roadway.width)
            elif key == "SURFACE":
                crossing.roadway.surface = self._roadway_surface(value=value)
            elif key in {"ROADWAYSECDATA", "ROADWAYPOINT"}:
                station_elev: list[float] = self._floats(value=value, expected=2)
                if len(station_elev) == 2:
                    crossing.roadway.stations.append(station_elev[0])
                    crossing.roadway.elevations.append(station_elev[1])
            elif key == "STARTCULVERT":
                culvert: CulvertBarrel = self._parse_culvert(name=self._clean_string(raw=value))
                crossing.culverts.append(culvert)
            elif key == "NUMCULVERTS":
                continue
            elif key == "CROSSGUID":
                crossing.uuid = self._clean_string(raw=value)

    def _parse_culvert(self, name: str) -> CulvertBarrel:
        culvert = CulvertBarrel(name=name)
        while True:
            card: _Hy8Card = self._stream.next_card()
            key: str = card.key
            value: str = card.value
            if key == "ENDCULVERT":
                return culvert
            if key == "CULVERTSHAPE":
                culvert.shape = self._culvert_shape(value=value)
            elif key == "CULVERTMATERIAL":
                culvert.material = self._culvert_material(value=value)
            elif key == "BARRELDATA":
                numbers = self._floats(value=value, expected=4)
                if len(numbers) >= 4:
                    culvert.span = numbers[0]
                    culvert.rise = numbers[1]
                    culvert.manning_n_top = numbers[2]
                    culvert.manning_n_bottom = numbers[3]
            elif key == "NUMBEROFBARRELS":
                culvert.number_of_barrels = self._as_int(value=value, default=culvert.number_of_barrels)
            elif key == "INVERTDATA":
                numbers: list[float] = self._floats(value=value, expected=4)
                if len(numbers) >= 4:
                    culvert.inlet_invert_station = numbers[0]
                    culvert.inlet_invert_elevation = numbers[1]
                    culvert.outlet_invert_station = numbers[2]
                    culvert.outlet_invert_elevation = numbers[3]
            elif key == "ROADCULVSTATION":
                culvert.roadway_station = self._as_float(value=value, default=culvert.roadway_station)
            elif key == "BARRELSPACING":
                culvert.barrel_spacing = self._as_float(value=value)
            elif key == "STARTCULVNOTES":
                culvert.notes = self._collect_notes(inline_value=value, end_marker="ENDCULVNOTES")

    def _collect_notes(self, inline_value: str, *, end_marker: str) -> str:
        lines: list[str] = []
        inline: str = self._clean_string(raw=inline_value)
        if inline:
            lines.append(inline)
        lines.extend(self._stream.read_block(end_marker))
        text: str = "\n".join(line.strip() for line in lines if line.strip())
        return text

    def _finalize_flow(self, crossing: CulvertCrossing, user_values: list[float]) -> None:
        flow: FlowDefinition = crossing.flow
        if flow.method is FlowMethod.MIN_DESIGN_MAX:
            return
        if not user_values:
            flow.method = FlowMethod.USER_DEFINED
            flow.user_values = []
            return
        increment: float | None = self._detect_increment(values=user_values)
        if increment is not None:
            flow.method = FlowMethod.MIN_MAX_INCREMENT
            flow.minimum = user_values[0]
            flow.maximum = user_values[-1]
            flow.increment = increment
            flow.user_values = []
        else:
            flow.method = FlowMethod.USER_DEFINED
            flow.user_values = list(user_values)

    def _read_flow_values(self, expected: int) -> list[float]:
        if expected <= 0:
            return []
        values: list[float] = []
        while len(values) < expected:
            card: _Hy8Card = self._stream.next_card()
            if card.key == "DISCHARGEXYUSER_Y":
                try:
                    values.append(float(card.value.split()[0]))
                except (IndexError, ValueError):
                    values.append(0.0)
            elif card.key == "DISCHARGEXYUSER_NAME":
                continue
            else:
                self._stream.push_back(card)
                break
        return values

    @staticmethod
    def _clean_string(raw: str) -> str:
        text: str = raw.strip()
        if text.startswith('"') and text.endswith('"') and len(text) >= 2:
            text = text[1:-1]
        return text.strip()

    @staticmethod
    def _floats(value: str, *, expected: int | None = None) -> list[float]:
        numbers: list[float] = []
        for token in value.split():
            try:
                numbers.append(float(token))
            except ValueError:
                continue
            if expected is not None and len(numbers) >= expected:
                break
        return numbers

    @staticmethod
    def _as_int(value: str, *, default: int = 0) -> int:
        try:
            return int(value.split()[0])
        except (IndexError, ValueError):
            return default

    @staticmethod
    def _as_float(value: str, *, default: float = 0.0) -> float:
        try:
            return float(value.split()[0])
        except (IndexError, ValueError):
            return default

    @staticmethod
    def _tailwater_type(value: str) -> TailwaterType:
        try:
            return TailwaterType(value=_Hy8Parser._as_int(value=value))
        except ValueError:
            return TailwaterType.CONSTANT

    @staticmethod
    def _roadway_surface(value: str) -> RoadwaySurface:
        index: int = _Hy8Parser._as_int(value=value, default=1)
        try:
            return RoadwaySurface(value=index)
        except ValueError:
            return RoadwaySurface.PAVED

    @staticmethod
    def _culvert_shape(value: str) -> CulvertShape:
        try:
            return CulvertShape(value=_Hy8Parser._as_int(value=value))
        except ValueError:
            return CulvertShape.CIRCLE

    @staticmethod
    def _culvert_material(value: str) -> CulvertMaterial:
        try:
            return CulvertMaterial(value=_Hy8Parser._as_int(value=value, default=1))
        except ValueError:
            return CulvertMaterial.CONCRETE

    @staticmethod
    def _detect_increment(values: list[float]) -> float | None:
        if len(values) < 3:
            return None
        deltas: list[float] = [values[idx + 1] - values[idx] for idx in range(len(values) - 1)]
        first: float = deltas[0]
        if abs(first) <= 0.0:
            return None
        tolerance: float = max(abs(first), 1.0) * 1e-6
        if all(abs(delta - first) <= tolerance for delta in deltas[1:]):
            return first
        return None
