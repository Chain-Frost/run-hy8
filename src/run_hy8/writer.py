"""Serialization helpers for .hy8 project files."""

from __future__ import annotations

import tempfile
from enum import Enum
from itertools import pairwise
from pathlib import Path
from typing import TextIO, cast

from .classes_references import UnitSystem
from .ellipse_catalogue import EllipticalCatalogueSize, find_ellipse_catalogue_size
from .inlet_configurations import resolve_v8_inlet_spec
from .material_codes import hy8_v8_material_code
from .models import (
    CulvertBarrel,
    CulvertCrossing,
    FlowDefinition,
    Hy8Project,
    RoadwayProfile,
    TailwaterDefinition,
)
from .type_helpers import (
    CulvertShape,
    FlowMethod,
    RoadwayShape,
    TailwaterType,
)
from .units import cms_to_cfs, feet_to_metres, metres_to_feet, weir_coefficient_to_english


class Hy8FileWriter:
    """Writes HY-8 project files (.hy8) from the internal object model.

    This class serializes a `Hy8Project` instance into the text-based .hy8
    format that the HY-8 executable can read. It handles unit conversions,
    validation, and the specific formatting required by the HY-8 GUI.
    """

    def __init__(self, project: Hy8Project, *, version: float = 80.0) -> None:
        """Initializes the writer with a project.

        Args:
            project: The `Hy8Project` instance to be written.
            version: The HY-8 version number to write in the file header.
        """
        if version != 80.0:
            msg = f"Unsupported HY-8 project version {version}; run-hy8 supports version 8 only."
            raise ValueError(msg)
        self.project: Hy8Project = project
        self.version: float = version

    def write(self, output_path: Path, *, overwrite: bool = True) -> Path:
        """Validate the project and write it to a .hy8 file on disk."""
        output_path = output_path.with_suffix(".hy8")
        errors: list[str] = self.project.validate()
        errors.extend(self._serialization_validation_errors())
        if errors:
            message: str = "HY-8 project validation failed:\n" + "\n".join(errors)
            raise ValueError(message)

        if output_path.exists() and not overwrite:
            msg = f"{output_path} already exists. Set overwrite=True to replace it."
            raise FileExistsError(msg)

        output_path.parent.mkdir(parents=True, exist_ok=True)
        temp_path: Path | None = None
        try:
            with tempfile.NamedTemporaryFile(
                mode="w",
                encoding="utf-8",
                newline="\n",
                dir=output_path.parent,
                prefix=f".{output_path.name}.",
                suffix=".tmp",
                delete=False,
            ) as handle:
                temp_path = Path(handle.name)
                self._write_project(cast(TextIO, handle))
            temp_path.replace(output_path)
        except BaseException:
            if temp_path is not None:
                temp_path.unlink(missing_ok=True)
            raise
        return output_path

    def _serialization_validation_errors(self) -> list[str]:
        """Return writer-specific validation errors that require project units."""
        errors: list[str] = []
        for crossing_index, crossing in enumerate(self.project.crossings, start=1):
            for culvert_index, culvert in enumerate(crossing.culverts, start=1):
                if culvert.shape is not CulvertShape.ELLIPTICAL:
                    continue
                try:
                    self._ellipse_catalogue_size(culvert)
                except ValueError as exc:
                    errors.append(
                        f"Crossing #{crossing_index} ({crossing.name}), "
                        f"culvert #{culvert_index} ({culvert.name}): {exc}"
                    )
        return errors

    def _ellipse_catalogue_size(self, culvert: CulvertBarrel) -> EllipticalCatalogueSize:
        """Resolve an ellipse catalogue row using the parent project's units."""
        span_m = feet_to_metres(culvert.span) if self.project.units is UnitSystem.ENGLISH else culvert.span
        rise_m = feet_to_metres(culvert.rise) if self.project.units is UnitSystem.ENGLISH else culvert.rise
        return find_ellipse_catalogue_size(
            span_m,
            rise_m,
            material=culvert.material,
        )

    def _write_project(self, handle: TextIO) -> None:
        """Write top-level project metadata and each crossing."""
        # The version number is written without a decimal if it's a whole number.
        version_value: float = self.version
        version_text: str = str(int(version_value)) if float(version_value).is_integer() else str(version_value)
        handle.write(f"HY8PROJECTFILE{version_text}\n")
        self._write_card(handle, "UNITS", self.project.units.project_flag)
        self._write_card(handle, "EXITLOSSOPTION", self.project.exit_loss_option)
        self._write_card(handle, "PROJTITLE", self.project.title)
        self._write_card(handle, "PROJDESIGNER", self.project.designer)
        self._write_card(handle, "STARTPROJNOTES", self.project.notes)
        self._write_card(handle, "ENDPROJNOTES")
        self._write_card(handle, "PROJDATE", self.project.project_timestamp_hours())
        self._write_card(handle, "NUMCROSSINGS", len(self.project.crossings))
        for crossing in self.project.crossings:
            self._write_crossing(handle=handle, crossing=crossing)
        handle.write("ENDPROJECTFILE")

    def _write_crossing(self, handle: TextIO, crossing: CulvertCrossing) -> None:
        """Serialize notes, flow, geometry, and culverts for a crossing."""
        self._write_card(handle, "STARTCROSSING", f'"{crossing.name}"')
        self._write_card(handle, "STARTCROSSNOTES", f'"{crossing.notes}"')
        self._write_flow(handle, crossing)
        self._write_tailwater(handle, crossing.tailwater)
        self._write_roadway(handle, crossing)
        self._write_card(handle, "NUMCULVERTS", len(crossing.culverts))
        for culvert in crossing.culverts:
            self._write_culvert(handle, culvert=culvert)
        if crossing.uuid:
            self._write_card(handle, "CROSSGUID", crossing.uuid)
        self._write_card(handle, "ENDCROSSING", f'"{crossing.name}"')

    def _write_flow(self, handle: TextIO, crossing: CulvertCrossing) -> None:
        """Serialize the discharge definition HY-8 expects."""
        flow: FlowDefinition = crossing.flow
        discharge_method: int = 0 if flow.method is FlowMethod.MIN_DESIGN_MAX else 1
        irregular: bool = crossing.roadway.shape == RoadwayShape.IRREGULAR
        point_count: int = len(crossing.roadway.stations)
        # Native min/design/max calculates eleven flows. Larger irregular
        # profiles need an explicit list to avoid OpenRunSave's indexing failure.
        explicit_range = irregular and point_count > 11 and flow.method is FlowMethod.MIN_DESIGN_MAX
        if explicit_range:
            discharge_method = 1
        min_flow, design_flow, max_flow = self._flow_range_values(flow)
        self._write_card(
            handle,
            "DISCHARGERANGE",
            self._flow_value(value=min_flow),
            self._flow_value(value=design_flow),
            self._flow_value(value=max_flow),
        )
        self._write_card(handle, "DISCHARGEMETHOD", discharge_method)
        flow_values: list[float] = flow.sequence()
        has_user_labels: bool = bool(flow.user_value_labels)
        labels: list[str] = list(flow.user_value_labels)
        if irregular and (flow.method is FlowMethod.USER_DEFINED or explicit_range):
            if explicit_range:
                labels = ["Minimum Flow", "Design Flow", "Maximum Flow"]
                has_user_labels = True
            flow_values, labels = self._pad_irregular_flows(flow_values, labels, minimum_count=point_count)
        else:
            flow_values, labels = self._ensure_minimum_user_defined_flows(
                flow, flow_values, labels, has_labels=has_user_labels
            )
        include_labels: bool = has_user_labels
        self._write_card(handle, "DISCHARGEXYUSER", len(flow_values))
        for idx, value in enumerate(flow_values):
            self._write_card(handle, "DISCHARGEXYUSER_Y", self._flow_value(value))
            if include_labels:
                label: str = labels[idx] if idx < len(labels) else ""
                self._write_card(handle, "DISCHARGEXYUSER_NAME", f'"{label}"')

    def _pad_irregular_flows(
        self, flow_values: list[float], labels: list[str], *, minimum_count: int
    ) -> tuple[list[float], list[str]]:
        """Add exactly the missing flows, preserving requests and model state."""
        if len(flow_values) >= minimum_count:
            return flow_values, labels
        entries: list[tuple[float, str]] = [
            (value, labels[index] if labels else "") for index, value in enumerate(flow_values)
        ]
        while len(entries) < minimum_count:
            entries.sort()
            # Split the widest interval rather than accumulating helpers that
            # round to duplicate zero-valued English cards.
            bounds: list[tuple[float, float]] = [(0.0, entries[0][0]), *[(a[0], b[0]) for a, b in pairwise(entries)]]
            lower, upper = max(bounds, key=lambda pair: pair[1] - pair[0])
            candidate: float = lower + (upper - lower) / 2
            if upper == 0:
                candidate = 0.05
            stored: str = f"{self._flow_value(candidate):.6f}"
            if any(f"{self._flow_value(value):.6f}" == stored for value, _ in entries):
                msg = "Cannot pad irregular roadway flows distinctly at HY-8's six-decimal input precision."
                raise ValueError(msg)
            entries.append((candidate, FlowDefinition.DUMMY_FLOW_LABEL if labels else ""))
        entries.sort()
        return [value for value, _ in entries], [label for _, label in entries] if labels else []

    def _ensure_minimum_user_defined_flows(
        self,
        flow: FlowDefinition,
        flow_values: list[float],
        labels: list[str],
        *,
        has_labels: bool,
        minimum_count: int = 2,
    ) -> tuple[list[float], list[str]]:
        """Pad user flows for executable stability, keeping requested flows intact."""
        # The HY-8 GUI requires at least two points for a user-defined flow curve.
        # If only one is provided, we add a second point at 10% of the value.
        if flow.method is not FlowMethod.USER_DEFINED or len(flow_values) >= minimum_count:
            return flow_values, labels
        entries: list[tuple[float, str | None]] = [
            (value, labels[idx] if has_labels and idx < len(labels) else None) for idx, value in enumerate(flow_values)
        ]
        base_value = max(flow_values)
        generated_value = base_value * 0.1 if base_value > 0 else 0.05
        while len(entries) < minimum_count:
            if generated_value not in [value for value, _ in entries]:
                dummy_label = FlowDefinition.DUMMY_FLOW_LABEL if has_labels else None
                entries.append((generated_value, dummy_label))
            # Avoid looping forever if tiny flows underflow to zero.
            generated_value = generated_value * 0.5 if generated_value > 0 else 0.05
        entries.sort(key=lambda entry: entry[0])
        normalized_values: list[float] = [value for value, _ in entries]
        if not has_labels:
            return normalized_values, []
        normalized_labels: list[str] = [label or "" for _, label in entries]
        return normalized_values, normalized_labels

    def _flow_range_values(self, flow: FlowDefinition) -> tuple[float, float, float]:
        """Return the min/design/max tuple HY-8 uses for min-design-max flows."""
        # This ensures the flow definition's attributes are synchronized with the
        # sequence values before being written.
        if flow.method is FlowMethod.MIN_DESIGN_MAX:
            values: list[float] = flow.sequence()
            if len(values) >= 3:
                flow.minimum, flow.design, flow.maximum = values[0], values[1], values[2]
            return flow.minimum, flow.design, flow.maximum
        return flow.minimum, flow.design, flow.maximum

    def _write_tailwater(self, handle: TextIO, tailwater: TailwaterDefinition) -> None:
        """Encode tailwater conditions (currently constant depth only)."""
        if tailwater.tw_type is not TailwaterType.CONSTANT:
            msg = (
                f"Tailwater type '{tailwater.tw_type.name}' is not supported by run-hy8. "
                "Use the HY-8 GUI for advanced tailwater definitions."
            )
            raise ValueError(msg)
        self._write_card(
            handle,
            "TAILWATERTYPE",
            tailwater.tw_type.value,
        )
        self._write_card(
            handle,
            "CHANNELGEOMETRY",
            self._length_value(tailwater.bottom_width),
            tailwater.sideslope,
            tailwater.channel_slope,
            tailwater.manning_n,
            self._length_value(tailwater.invert_elevation),
        )
        stages: list[float] = self._tailwater_stages(tailwater)
        vel: float = 0.0
        shear: float = 0.0
        froude: float = 0.0
        self._write_card(handle, "NUMRATINGCURVE", len(stages))
        first_stage: float = stages[0] if stages else 0.0
        self._write_card(handle, "TWRATINGCURVE", self._length_value(first_stage), vel, shear, froude)
        for stage in stages[1:]:
            self._write_card(handle, "", self._length_value(stage), vel, shear, froude)

    def _tailwater_stages(self, tailwater: TailwaterDefinition) -> list[float]:
        """Generate a list of constant tailwater elevations for the rating curve."""
        # For a constant elevation, the rating curve is just that elevation repeated.
        count: int = max(1, tailwater.rating_curve_entries)
        return [tailwater.constant_elevation] * count

    def _write_roadway(self, handle: TextIO, crossing: CulvertCrossing) -> None:
        """Write roadway surface, station, elevation, and label cards."""
        roadway: RoadwayProfile = crossing.roadway
        self._write_card(handle, "ROADWAYSHAPE", roadway.shape)
        self._write_card(handle, "ROADWIDTH", self._length_value(roadway.width))
        if roadway.discharge_coefficient is not None:
            self._write_card(handle, "WEIRCOEFF", weir_coefficient_to_english(roadway.discharge_coefficient))
        self._write_card(handle, "SURFACE", roadway.surface.value)
        self._write_card(handle, "NUMSTATIONS", len(roadway.stations))
        card: str = "ROADWAYSECDATA"
        for station, elevation in roadway.points():
            station: float
            elevation: float
            self._write_card(handle, card, self._length_value(station), self._length_value(elevation))
            card = "ROADWAYPOINT"

    def _write_culvert(self, handle: TextIO, culvert: CulvertBarrel) -> None:
        """Write geometric and hydraulic properties for a barrel."""
        self._write_card(handle, "STARTCULVERT", f'"{culvert.name}"')
        culvert_shape: int = culvert.shape.value
        culvert_material: int = hy8_v8_material_code(culvert.shape, culvert.material)
        self._write_card(handle, "CULVERTSHAPE", culvert_shape)
        self._write_card(handle, "CULVERTMATERIAL", culvert_material)
        catalogue_size: EllipticalCatalogueSize | None = None
        if culvert.shape is CulvertShape.ELLIPTICAL:
            catalogue_size = self._ellipse_catalogue_size(culvert)
            default_n = catalogue_size.manning_n
            n_top = culvert.manning_n_top if culvert.manning_n_top is not None else default_n
            # ShapeDB supplies one ellipse Manning value and the retained
            # GUI-created ellipse writes BARRELDATA's fourth field as zero.
            n_bottom = culvert.manning_n_bottom if culvert.manning_n_bottom is not None else 0.0
        else:
            n_top, n_bottom = culvert.resolved_manning_values()
        self._write_card(handle, "INLETTYPE", culvert.inlet_type)
        inlet_spec = resolve_v8_inlet_spec(culvert.resolved_inlet_configuration())
        # HY-8 v8 still requires the pre-7.1 compatibility card, but current
        # hydraulics are selected by the contextual INLETEDGETYPE71 index.
        # A neutral legacy value avoids exposing the obsolete code system.
        # Evidence and reproduction notes: docs/hy8_v8_inlet_configurations.md
        self._write_card(handle, "INLETEDGETYPE", 0)
        self._write_card(handle, "INLETEDGETYPE71", inlet_spec.v8_index)
        self._write_card(handle, "IMPINLETEDGETYPE", culvert.improved_inlet_edge_type)
        span_file = self._length_value(culvert.span)
        rise_file = self._length_value(culvert.rise)
        self._write_card(
            handle,
            "BARRELDATA",
            span_file,
            rise_file,
            n_top,
            n_bottom,
        )
        if culvert.shape is CulvertShape.ELLIPTICAL:
            # HY-8 ellipses are material-specific catalogue shapes rather than
            # arbitrary mathematical ellipses. Br/Tr/Cr/B from the matching ShapeDB row
            # are hydraulically significant: zeroing them produces zero barrel
            # discharge. HY-8 rewrites BARRELGEOMETRY's fifth field during
            # OpenRunSave, so the source catalogue area is used as the
            # source-backed input value without treating the rewritten value as
            # a persistent catalogue parameter.
            if catalogue_size is None:  # pragma: no cover - guarded above
                msg = "Missing HY-8 ellipse catalogue selection."
                raise RuntimeError(msg)
            br_file, tr_file, cr_file, b_file = catalogue_size.geometry_prefix_ft
            self._write_card(handle, "LOWERCULVERTMANNING", 0.0)
            self._write_card(handle, "LOWERCULVERTMANNINGB", 0.0)
            self._write_card(handle, "IRREGSIZE", 0, 0, 1)
            self._write_card(handle, "EMBEDDEPTH", 0.0)
            self._write_card(
                handle,
                "BARRELGEOMETRY",
                br_file,
                tr_file,
                cr_file,
                b_file,
                catalogue_size.area_ft2,
            )
            self._write_card(handle, "DEPRESSIONDATA", 0.0, 0.0, 0.0)
            self._write_card(handle, "TAPEREDDATA", 0.0, 0.0, 0.0, 0.0, 0.0)
            self._write_card(handle, "DEPRESSION", 0)
            self._write_card(handle, "MITERED", 0)
        self._write_card(handle, "EMBANKMENTTYPE", 2)
        self._write_card(handle, "NUMBEROFBARRELS", culvert.number_of_barrels)
        self._write_card(
            handle,
            "INVERTDATA",
            self._length_value(culvert.inlet_invert_station),
            self._length_value(culvert.inlet_invert_elevation),
            self._length_value(culvert.outlet_invert_station),
            self._length_value(culvert.outlet_invert_elevation),
        )
        self._write_card(handle, "STARTCULVNOTES", f'"{culvert.notes}"')
        self._write_card(handle, "ENDCULVNOTES")
        self._write_card(handle, "ROADCULVSTATION", self._length_value(culvert.roadway_station))
        spacing: float = culvert.barrel_spacing if culvert.barrel_spacing is not None else max(culvert.span * 1.5, 0.0)
        self._write_card(handle, "BARRELSPACING", self._length_value(spacing))
        self._write_card(handle, "ENDCULVERT", f'"{culvert.name}"')

    def _length_value(self, value: float) -> float:
        """Convert a length from meters (model) to feet (file) if necessary."""
        if self.project.units is UnitSystem.SI:
            return metres_to_feet(value)
        return value

    def _flow_value(self, value: float) -> float:
        """Convert a flow from cms (model) to cfs (file) if necessary."""
        if self.project.units is UnitSystem.SI:
            return cms_to_cfs(value)
        return value

    @staticmethod
    def _write_card(handle: TextIO, name: str, *values: object) -> None:
        """Write a HY-8 card while preserving the GUI-style column alignment.

        All cards indent their first value so that it begins at column 22 (the GUI's
        `ROADWAYSECDATA` reference). Subsequent columns are right-aligned inside a fixed
        width so that digits stack vertically even when a value becomes negative or
        grows to the tens/hundreds/thousands.
        """
        card_column: int = 21
        base_gap: int = 3
        base_length: int = 8
        field_width: int = 11

        def fmt_numeric(value: float) -> str:
            if isinstance(value, int):
                return str(value)
            return f"{float(value):.6f}"

        if name:
            line: str = name if len(name) >= card_column else f"{name:<{card_column}}"
        else:
            line = ""
        builder: list[str] = [line]

        if not values:
            handle.write(f"{''.join(builder)}\n")
            return

        current: int = len(line)
        numeric_index: int = 0
        previous_length: int | None = None

        def append(text: str) -> None:
            nonlocal current
            builder.append(text)
            current += len(text)

        for value in values:
            normalized_value = value.value if isinstance(value, Enum) else value
            if normalized_value is None:
                continue
            if isinstance(normalized_value, (int, float)):
                value_text: str = fmt_numeric(normalized_value)
                if numeric_index == 0:
                    if current < card_column:
                        append(" " * (card_column - current))
                    elif current > card_column:
                        append(" ")
                else:
                    extra: int = max(0, (previous_length or base_length) - base_length)
                    gap: int = max(1, base_gap - extra)
                    append(" " * gap)
                append(value_text)
                previous_length = len(value_text)
                numeric_index += 1
            else:
                text = str(normalized_value)
                target: int = card_column if numeric_index == 0 else card_column + numeric_index * field_width
                if current < target:
                    append(" " * (target - current))
                elif current > target:
                    append(" ")
                append(text)
        handle.write("".join(builder) + "\n")
