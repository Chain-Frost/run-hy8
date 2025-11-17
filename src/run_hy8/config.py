"""Helpers for loading `Hy8Project` instances from configuration files."""

from __future__ import annotations

from collections.abc import Mapping, Sequence as ABCSequence
from pathlib import Path
from typing import Any, cast

import json

from .models import (
    CulvertBarrel,
    CulvertCrossing,
    CulvertMaterial,
    CulvertShape,
    FlowDefinition,
    FlowMethod,
    Hy8Project,
    RoadwayProfile,
    RoadwaySurface,
    TailwaterDefinition,
    TailwaterType,
    UnitSystem,
)

JSONMapping = Mapping[str, Any]


def load_project_from_json(path: Path) -> Hy8Project:
    """Read a JSON file from disk and create a `Hy8Project`."""

    raw_data: Any = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(raw_data, Mapping):
        raise ValueError("Top-level JSON document must be an object.")
    data: JSONMapping = cast(JSONMapping, raw_data)
    return project_from_mapping(data)


def project_from_mapping(config: JSONMapping) -> Hy8Project:
    project_section_raw: Any = config.get("project", {})
    if not isinstance(project_section_raw, Mapping):
        raise ValueError("Project section must be an object.")
    project_section: JSONMapping = cast(JSONMapping, project_section_raw)

    project = Hy8Project()
    project.title = str(project_section.get("title", ""))
    project.designer = str(project_section.get("designer", ""))
    project.notes = str(project_section.get("notes", ""))
    project.units = _parse_unit_system(project_section.get("units", UnitSystem.ENGLISH.cli_flag))
    project.exit_loss_option = int(project_section.get("exit_loss_option", 0))

    crossings_data_raw: Any = config.get("crossings", [])
    if not isinstance(crossings_data_raw, ABCSequence) or isinstance(crossings_data_raw, (str, bytes)):
        raise ValueError("'crossings' section must be a list of crossing definitions")

    crossings_data_sequence: ABCSequence[Any] = cast(ABCSequence[Any], crossings_data_raw)
    crossings_data_raw_list: list[Any] = list(crossings_data_sequence)
    crossings_data_list: list[JSONMapping] = []
    for crossing_entry_raw in crossings_data_raw_list:
        crossing_entry: Any = crossing_entry_raw
        if not isinstance(crossing_entry, Mapping):
            raise ValueError("Each crossing definition must be an object.")
        crossings_data_list.append(cast(JSONMapping, crossing_entry))

    for crossing_entry in crossings_data_list:
        project.crossings.append(_parse_crossing(crossing_entry))

    return project


def _parse_crossing(entry: JSONMapping) -> CulvertCrossing:
    name = _require_str(entry, "name", "crossing")
    crossing = CulvertCrossing(name=name)
    crossing.notes = str(entry.get("notes", ""))
    if uuid := entry.get("uuid"):
        crossing.uuid = str(uuid)

    crossing.flow = _parse_flow(entry.get("flow", {}))
    crossing.tailwater = _parse_tailwater(entry.get("tailwater", {}))
    crossing.roadway = _parse_roadway(entry.get("roadway", {}))

    culvert_entries_raw: Any = entry.get("culverts", [])
    if not isinstance(culvert_entries_raw, ABCSequence) or isinstance(culvert_entries_raw, (str, bytes)):
        raise ValueError(f"Crossing '{name}' culverts must be a list")
    culvert_entries_sequence: ABCSequence[Any] = cast(ABCSequence[Any], culvert_entries_raw)
    culvert_entries_raw_list: list[Any] = list(culvert_entries_sequence)
    culvert_entries_list: list[JSONMapping] = []
    for culvert_entry_raw in culvert_entries_raw_list:
        culvert_entry: Any = culvert_entry_raw
        if not isinstance(culvert_entry, Mapping):
            raise ValueError(f"Culvert entries in crossing '{name}' must be objects.")
        culvert_entries_list.append(cast(JSONMapping, culvert_entry))
    for culvert_entry in culvert_entries_list:
        crossing.culverts.append(_parse_culvert(culvert_entry, crossing_name=name))

    return crossing


def _parse_flow(entry: JSONMapping) -> FlowDefinition:
    method_value = str(entry.get("method", FlowMethod.USER_DEFINED.value))
    try:
        method = FlowMethod(method_value)
    except ValueError as exc:
        raise ValueError(f"Unsupported flow method '{method_value}'") from exc

    if method is FlowMethod.MIN_MAX_INCREMENT:
        raise ValueError("Flow method 'min-max-increment' is not supported by run-hy8.")

    flow = FlowDefinition(method=method)
    if "user_values" in entry:
        values_raw: Any = entry.get("user_values", [])
        if not isinstance(values_raw, ABCSequence) or isinstance(values_raw, (str, bytes)):
            raise ValueError("Flow 'user_values' must be a list of numbers")
        values_sequence: ABCSequence[Any] = cast(ABCSequence[Any], values_raw)
        values_list: list[Any] = list(values_sequence)
        flow.user_values = [float(value) for value in values_list]
    if method is FlowMethod.MIN_DESIGN_MAX:
        flow.minimum = float(entry.get("minimum", flow.minimum))
        flow.design = float(entry.get("design", flow.design))
        flow.maximum = float(entry.get("maximum", flow.maximum))
    return flow


def _parse_tailwater(entry: JSONMapping) -> TailwaterDefinition:
    requested_type: Any = entry.get("type")
    if requested_type is not None:
        requested_enum = _parse_tailwater_type(requested_type)
        if requested_enum is not TailwaterType.CONSTANT:
            raise ValueError(
                f"Tailwater type '{requested_enum.name}' is not supported by run-hy8. "
                "Configure a constant elevation or use the HY-8 GUI."
            )

    unsupported_fields = {
        "bottom_width",
        "channel_slope",
        "manning_n",
        "rating_curve",
    } & entry.keys()
    if unsupported_fields:
        pretty = ", ".join(sorted(unsupported_fields))
        raise ValueError(
            f"Tailwater fields ({pretty}) are not supported by run-hy8. Use the HY-8 GUI for this configuration."
        )

    tailwater = TailwaterDefinition()
    tailwater.constant_elevation = float(entry.get("constant_elevation", tailwater.constant_elevation))
    tailwater.invert_elevation = float(entry.get("invert_elevation", tailwater.invert_elevation))
    return tailwater


def _parse_roadway(entry: JSONMapping) -> RoadwayProfile:
    roadway = RoadwayProfile()
    roadway.width = float(entry.get("width", roadway.width))
    roadway.shape = int(entry.get("shape", roadway.shape))
    if "surface" not in entry:
        raise ValueError("Roadway surface must be specified (paved, gravel, user_defined).")
    roadway_surface_value: Any = entry["surface"]
    roadway.surface = _parse_surface(roadway_surface_value)
    roadway.stations = [float(value) for value in entry.get("stations", [])]
    roadway.elevations = [float(value) for value in entry.get("elevations", [])]
    return roadway


def _parse_culvert(entry: JSONMapping, *, crossing_name: str) -> CulvertBarrel:
    name = _require_str(entry, "name", f"culvert in crossing '{crossing_name}'")
    culvert = CulvertBarrel(name=name)
    culvert.span = float(entry.get("span", culvert.span))
    culvert.rise = float(entry.get("rise", culvert.rise))
    culvert.shape = _parse_culvert_shape(entry.get("shape", culvert.shape.name))
    culvert.material = _parse_culvert_material(entry.get("material", culvert.material.name))
    culvert.number_of_barrels = int(entry.get("number_of_barrels", culvert.number_of_barrels))
    culvert.inlet_invert_station = float(entry.get("inlet_invert_station", culvert.inlet_invert_station))
    culvert.inlet_invert_elevation = float(entry.get("inlet_invert_elevation", culvert.inlet_invert_elevation))
    culvert.outlet_invert_station = float(entry.get("outlet_invert_station", culvert.outlet_invert_station))
    culvert.outlet_invert_elevation = float(entry.get("outlet_invert_elevation", culvert.outlet_invert_elevation))
    culvert.roadway_station = float(entry.get("roadway_station", culvert.roadway_station))
    spacing_value: Any = entry.get("barrel_spacing", culvert.barrel_spacing)
    if spacing_value is None:
        culvert.barrel_spacing = None
    else:
        culvert.barrel_spacing = float(spacing_value)
    culvert.notes = str(entry.get("notes", culvert.notes))
    return culvert


def _parse_unit_system(value: Any) -> UnitSystem:
    if isinstance(value, UnitSystem):
        return value
    normalized = str(value).strip().upper()
    for unit in UnitSystem:
        if unit.cli_flag.upper() == normalized or unit.name == normalized:
            return unit
    raise ValueError(f"Unsupported unit system '{value}'")


def _parse_surface(value: Any) -> RoadwaySurface:
    normalized = str(value).strip().upper().replace("-", "_")
    try:
        return RoadwaySurface[normalized]
    except KeyError as exc:
        raise ValueError(f"Unsupported roadway surface '{value}'") from exc


def _parse_culvert_shape(value: Any) -> CulvertShape:
    normalized = str(value).strip().upper()
    try:
        return CulvertShape[normalized]
    except KeyError as exc:
        raise ValueError(f"Unsupported culvert shape '{value}'") from exc


def _parse_culvert_material(value: Any) -> CulvertMaterial:
    normalized = str(value).strip().upper().replace(" ", "_")
    try:
        return CulvertMaterial[normalized]
    except KeyError as exc:
        raise ValueError(f"Unsupported culvert material '{value}'") from exc


def _parse_tailwater_type(value: Any) -> TailwaterType:
    normalized = str(value).strip().upper().replace("-", "_")
    try:
        return TailwaterType[normalized]
    except KeyError as exc:
        raise ValueError(f"Unsupported tailwater type '{value}'") from exc


def _require_str(entry: JSONMapping, key: str, context: str) -> str:
    if key not in entry:
        raise ValueError(f"Missing required field '{key}' in {context}")
    value = entry[key]
    if not isinstance(value, str):
        raise ValueError(f"Field '{key}' in {context} must be a string")
    return value
