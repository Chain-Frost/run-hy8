"""Helpers for loading `Hy8Project` instances from configuration files."""

from __future__ import annotations

import json
import warnings
from collections.abc import Mapping
from collections.abc import Sequence as ABCSequence
from pathlib import Path
from typing import Any, cast

from .classes_references import UnitSystem
from .inlet_configurations import default_inlet_configuration, parse_inlet_configuration
from .models import (
    CulvertBarrel,
    CulvertCrossing,
    FlowDefinition,
    Hy8Project,
    RoadwayProfile,
    TailwaterDefinition,
)
from .models.culvert_barrel import LegacyInletConfigurationWarning
from .type_helpers import (
    CulvertMaterial,
    CulvertShape,
    FlowMethod,
    InletEdgeType,
    InletEdgeType71,
    RoadwaySurface,
    TailwaterType,
    coerce_enum,
)

JSONMapping = Mapping[str, Any]


def load_project_from_json(path: Path) -> Hy8Project:
    """Read a JSON file from disk and create a `Hy8Project`."""
    raw_data: Any = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(raw_data, Mapping):
        msg = "Top-level JSON document must be an object."
        raise TypeError(msg)
    data: JSONMapping = cast(JSONMapping, raw_data)
    return project_from_mapping(data)


def project_from_mapping(config: JSONMapping) -> Hy8Project:
    """Build a Hy8Project from the parsed configuration mapping."""
    # Ensure the top-level 'project' key points to a dictionary.
    project_section_raw: Any = config.get("project", {})
    if not isinstance(project_section_raw, Mapping):
        msg = "Project section must be an object."
        raise TypeError(msg)
    project_section: JSONMapping = cast(JSONMapping, project_section_raw)

    # Initialize the project and populate top-level metadata.
    # Default values are used if keys are missing from the config.
    project = Hy8Project()
    project.title = str(project_section.get("title", ""))
    project.designer = str(project_section.get("designer", ""))
    project.notes = str(project_section.get("notes", ""))
    project.units = _parse_unit_system(project_section.get("units", UnitSystem.SI.cli_flag))
    project.exit_loss_option = int(project_section.get("exit_loss_option", 0))

    # Ensure the 'crossings' key points to a list.
    crossings_data_raw: Any = config.get("crossings", [])
    if not isinstance(crossings_data_raw, ABCSequence) or isinstance(crossings_data_raw, (str, bytes)):
        msg = "'crossings' section must be a list of crossing definitions"
        raise TypeError(msg)

    crossings_data_sequence: ABCSequence[Any] = cast(ABCSequence[Any], crossings_data_raw)
    crossings_data_raw_list: list[Any] = list(crossings_data_sequence)
    # Validate that each item in the crossings list is a dictionary.
    crossings_data_list: list[JSONMapping] = []
    for crossing_entry_raw in crossings_data_raw_list:
        crossing_entry: Any = crossing_entry_raw
        if not isinstance(crossing_entry, Mapping):
            msg = "Each crossing definition must be an object."
            raise TypeError(msg)
        crossings_data_list.append(cast(JSONMapping, crossing_entry))

    # Parse each crossing dictionary and add it to the project.
    for crossing_entry in crossings_data_list:
        project.crossings.append(_parse_crossing(crossing_entry))

    return project


def _parse_crossing(entry: JSONMapping) -> CulvertCrossing:
    """Convert a single crossing dictionary into a CulvertCrossing instance.

    Args:
        entry: The dictionary representing a single crossing's configuration.

    Returns:
        A populated CulvertCrossing object.
    """
    # A name is required for each crossing.
    name: str = _require_str(entry=entry, key="name", context="crossing")
    crossing = CulvertCrossing(name=name)
    crossing.notes = str(entry.get("notes", ""))
    if uuid := entry.get("uuid"):
        crossing.uuid = str(uuid)

    crossing.flow = _parse_flow(entry.get("flow", {}))
    crossing.tailwater = _parse_tailwater(entry.get("tailwater", {}))
    crossing.roadway = _parse_roadway(entry.get("roadway", {}))

    culvert_entries_raw: Any = entry.get("culverts", [])
    if not isinstance(culvert_entries_raw, ABCSequence) or isinstance(culvert_entries_raw, (str, bytes)):
        msg = f"Crossing '{name}' culverts must be a list"
        raise TypeError(msg)
    culvert_entries_sequence: ABCSequence[Any] = cast(ABCSequence[Any], culvert_entries_raw)
    culvert_entries_raw_list: list[Any] = list(culvert_entries_sequence)
    culvert_entries_list: list[JSONMapping] = []
    for culvert_entry_raw in culvert_entries_raw_list:
        culvert_entry: Any = culvert_entry_raw
        if not isinstance(culvert_entry, Mapping):
            msg = f"Culvert entries in crossing '{name}' must be objects."
            raise TypeError(msg)
        culvert_entries_list.append(cast(JSONMapping, culvert_entry))

    # Parse each culvert dictionary and add it to the crossing.
    for culvert_entry in culvert_entries_list:
        crossing.culverts.append(_parse_culvert(culvert_entry, crossing_name=name))

    return crossing


def _parse_flow(entry: JSONMapping) -> FlowDefinition:
    """Parse the flow block into a FlowDefinition with validation.

    Args:
        entry: The dictionary representing the flow configuration.

    Returns:
        A populated FlowDefinition object.
    """
    # Determine the flow method from the config, defaulting to USER_DEFINED.
    method_value = str(entry.get("method", FlowMethod.USER_DEFINED.value))
    try:
        method = FlowMethod(value=method_value)
    except ValueError as exc:
        msg = f"Unsupported flow method '{method_value}'"
        raise ValueError(msg) from exc

    if method is FlowMethod.MIN_MAX_INCREMENT:
        msg = "Flow method 'min-max-increment' is not supported by run-hy8."
        raise ValueError(msg)

    flow = FlowDefinition(method=method)
    # If user-defined flow values are present, parse them into a list of floats.
    if "user_values" in entry:
        values_raw: Any = entry.get("user_values", [])
        if not isinstance(values_raw, ABCSequence) or isinstance(values_raw, (str, bytes)):
            msg = "Flow 'user_values' must be a list of numbers"
            raise ValueError(msg)
        values_sequence: ABCSequence[Any] = cast(ABCSequence[Any], values_raw)
        values_list: list[Any] = list(values_sequence)
        flow.user_values = [float(value) for value in values_list]

    # If using min/design/max flows, parse those float values.
    if method is FlowMethod.MIN_DESIGN_MAX:
        flow.minimum = float(entry.get("minimum", flow.minimum))
        flow.design = float(entry.get("design", flow.design))
        flow.maximum = float(entry.get("maximum", flow.maximum))
    return flow


def _parse_tailwater(entry: JSONMapping) -> TailwaterDefinition:
    """Interpret a tailwater configuration dictionary.

    Note: This application only supports a constant tailwater elevation. Other
    types supported by the HY-8 GUI are explicitly disallowed.

    Args:
        entry: The dictionary representing the tailwater configuration.

    Returns:
        A populated TailwaterDefinition object.
    """
    requested_type: Any = entry.get("type")
    if requested_type is not None:
        requested_enum: TailwaterType = _parse_tailwater_type(value=requested_type)
        if requested_enum is not TailwaterType.CONSTANT:
            msg = (
                f"Tailwater type '{requested_enum.name}' is not supported by run-hy8. "
                "Configure a constant elevation or use the HY-8 GUI."
            )
            raise ValueError(msg)

    # Disallow fields related to more complex tailwater calculations.
    unsupported_fields: set[str] = {
        "bottom_width",
        "channel_slope",
        "manning_n",
        "rating_curve",
    } & entry.keys()
    if unsupported_fields:
        pretty: str = ", ".join(sorted(unsupported_fields))
        msg = f"Tailwater fields ({pretty}) are not supported by run-hy8. Use the HY-8 GUI for this configuration."
        raise ValueError(msg)

    tailwater = TailwaterDefinition()
    tailwater.constant_elevation = float(entry.get("constant_elevation", tailwater.constant_elevation))
    tailwater.invert_elevation = float(entry.get("invert_elevation", tailwater.invert_elevation))
    return tailwater


def _parse_roadway(entry: JSONMapping) -> RoadwayProfile:
    """Convert the roadway section from a dictionary into a RoadwayProfile object.

    Args:
        entry: The dictionary representing the roadway configuration.

    Returns:
        A populated RoadwayProfile object.
    """
    roadway = RoadwayProfile()
    roadway.width = float(entry.get("width", roadway.width))
    roadway.shape = int(entry.get("shape", roadway.shape))
    if "surface" not in entry:
        msg = "Roadway surface must be specified (paved, gravel, user_defined)."
        raise ValueError(msg)
    roadway_surface_value: Any = entry["surface"]
    roadway.surface = _parse_surface(roadway_surface_value)
    roadway.stations = [float(value) for value in entry.get("stations", [])]
    roadway.elevations = [float(value) for value in entry.get("elevations", [])]
    return roadway


def _parse_culvert(entry: JSONMapping, *, crossing_name: str) -> CulvertBarrel:
    """Create a CulvertBarrel from a serialized dictionary entry.

    Args:
        entry: The dictionary representing a single culvert barrel's configuration.
        crossing_name: The name of the parent crossing, for context in error messages.

    Returns:
        A populated CulvertBarrel object.
    """
    # A name is required for each culvert.
    name: str = _require_str(entry=entry, key="name", context=f"culvert in crossing '{crossing_name}'")
    culvert = CulvertBarrel(name=name)
    culvert.span = float(entry.get("span", culvert.span))
    culvert.rise = float(entry.get("rise", culvert.rise))
    culvert.shape = _parse_culvert_shape(entry.get("shape", culvert.shape.name))
    culvert.material = _parse_culvert_material(entry.get("material", culvert.material.name))
    raw_inlet_configuration: Any = entry.get("inlet_configuration")
    legacy_keys: set[str] = {"inlet_edge_type", "inlet_edge_type71"} & entry.keys()
    if legacy_keys:
        if raw_inlet_configuration is not None:
            warnings.warn(
                message="JSON fields inlet_edge_type and inlet_edge_type71 are deprecated. "
                "Use inlet_configuration with a HY-8 v8 semantic slug.",
                category=LegacyInletConfigurationWarning,
                stacklevel=3,
            )
            msg = "Do not combine inlet_configuration with deprecated inlet edge fields."
            raise ValueError(msg)
        if "inlet_edge_type" in entry:
            culvert.inlet_edge_type = coerce_enum(
                enum_cls=InletEdgeType,
                value=entry["inlet_edge_type"],
                default=InletEdgeType.THIN_EDGE_PROJECTING,
            )
        if "inlet_edge_type71" in entry:
            culvert.inlet_edge_type71 = coerce_enum(
                enum_cls=InletEdgeType71,
                value=entry["inlet_edge_type71"],
                default=InletEdgeType71.CODE_0,
            )
        culvert.inlet_configuration = culvert.resolved_inlet_configuration()
    elif raw_inlet_configuration is None:
        culvert.inlet_configuration = default_inlet_configuration(
            shape=culvert.shape,
            material=culvert.material,
        )
    else:
        culvert.inlet_configuration = parse_inlet_configuration(
            value=raw_inlet_configuration,
            shape=culvert.shape,
            material=culvert.material,
        )
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
    """Coerce a configuration string into the corresponding UnitSystem enum member.

    This function is flexible and accepts the enum name (e.g., "SI") or the
    CLI flag (e.g., "EN"), ignoring case and whitespace.

    Args:
        value: The raw value from the configuration.

    Returns:
        The matching UnitSystem enum member.
    """
    if isinstance(value, UnitSystem):
        return value
    normalized: str = str(value).strip().upper()
    for unit in UnitSystem:
        if unit.cli_flag.upper() == normalized or unit.name == normalized:
            return unit
    msg = f"Unsupported unit system '{value}'"
    raise ValueError(msg)


def _parse_surface(value: Any) -> RoadwaySurface:
    """Convert a roadway surface name from config into a RoadwaySurface enum member.

    Normalizes the input string by making it uppercase and replacing hyphens
    with underscores to match the enum member names (e.g., "user-defined" -> "USER_DEFINED").

    Args:
        value: The raw value from the configuration.

    Returns:
        The matching RoadwaySurface enum member.
    """
    normalized: str = str(value).strip().upper().replace("-", "_")
    try:
        return RoadwaySurface[normalized]
    except KeyError as exc:
        msg = f"Unsupported roadway surface '{value}'"
        raise ValueError(msg) from exc


def _parse_culvert_shape(value: Any) -> CulvertShape:
    """Convert a culvert shape name from config into a CulvertShape enum member.

    Normalizes the input string to uppercase to match enum member names.

    Args:
        value: The raw value from the configuration.

    Returns:
        The matching CulvertShape enum member.
    """
    normalized: str = str(value).strip().upper()
    try:
        return CulvertShape[normalized]
    except KeyError as exc:
        msg = f"Unsupported culvert shape '{value}'"
        raise ValueError(msg) from exc


def _parse_culvert_material(value: Any) -> CulvertMaterial:
    """Convert a culvert material name from config into a CulvertMaterial enum member.

    Normalizes the input string by making it uppercase and replacing spaces
    with underscores to match enum member names (e.g., "CONCRETE" -> "CONCRETE").

    Args:
        value: The raw value from the configuration.

    Returns:
        The matching CulvertMaterial enum member.
    """
    normalized: str = str(value).strip().upper().replace(" ", "_")
    try:
        return CulvertMaterial[normalized]
    except KeyError as exc:
        msg = f"Unsupported culvert material '{value}'"
        raise ValueError(msg) from exc


def _parse_tailwater_type(value: Any) -> TailwaterType:
    """Convert a tailwater type name from config into a TailwaterType enum member.

    Normalizes the input string by making it uppercase and replacing hyphens
    with underscores to match enum member names (e.g., "rating-curve" -> "RATING_CURVE").

    Args:
        value: The raw value from the configuration.

    Returns:
        The matching TailwaterType enum member.
    """
    normalized: str = str(value).strip().upper().replace("-", "_")
    try:
        return TailwaterType[normalized]
    except KeyError as exc:
        msg = f"Unsupported tailwater type '{value}'"
        raise ValueError(msg) from exc


def _require_str(entry: JSONMapping, key: str, context: str) -> str:
    """Fetch a mandatory string field or raise a contextual exception."""
    if key not in entry:
        msg = f"Missing required field '{key}' in {context}"
        raise ValueError(msg)
    value = entry[key]
    if not isinstance(value, str):
        msg = f"Field '{key}' in {context} must be a string"
        raise TypeError(msg)
    return value
