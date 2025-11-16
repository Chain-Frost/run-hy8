"""Serialization helpers for .hy8 project files."""

from __future__ import annotations

from pathlib import Path
from typing import TextIO

from run_hy8.models import FlowDefinition, RoadwayProfile

from .models import (
    CulvertBarrel,
    CulvertCrossing,
    CulvertMaterial,
    CulvertShape,
    FlowMethod,
    Hy8Project,
    TailwaterDefinition,
    TailwaterType,
)


class Hy8FileWriter:
    """Writes HY-8 project files (.hy8) from the object model."""

    def __init__(self, project: Hy8Project, *, version: float = 80.0) -> None:
        self.project: Hy8Project = project
        self.version: float = version

    def write(self, output_path: Path, *, overwrite: bool = True) -> Path:
        """Validate and write the project to disk."""
        output_path = output_path.with_suffix(".hy8")
        errors: list[str] = self.project.validate()
        if errors:
            message: str = "HY-8 project validation failed:\n" + "\n".join(errors)
            raise ValueError(message)

        if output_path.exists() and not overwrite:
            raise FileExistsError(f"{output_path} already exists. Set overwrite=True to replace it.")

        output_path.parent.mkdir(parents=True, exist_ok=True)
        with output_path.open("w", encoding="utf-8") as handle:
            self._write_project(handle)
        return output_path

    def _write_project(self, handle: TextIO) -> None:
        handle.write(f"HY8PROJECTFILE{self.version}\n")
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
        handle.write("ENDPROJECTFILE\n")

    def _write_crossing(self, handle: TextIO, crossing: CulvertCrossing) -> None:
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
        flow: FlowDefinition = crossing.flow
        discharge_method: int = 0 if flow.method is FlowMethod.MIN_DESIGN_MAX else 1
        self._write_card(handle, "DISCHARGERANGE", flow.minimum, flow.design, flow.maximum)
        self._write_card(handle, "DISCHARGEMETHOD", discharge_method)
        flow_values: list[float] = flow.sequence()
        labels: list[str] = flow.user_value_labels if flow.user_value_labels else []
        include_labels: bool = bool(labels)
        self._write_card(handle, "DISCHARGEXYUSER", len(flow_values))
        for idx, value in enumerate(flow_values):
            self._write_card(handle, "DISCHARGEXYUSER_Y", value)
            if include_labels:
                label: str = labels[idx] if idx < len(labels) else ""
                self._write_card(handle, "DISCHARGEXYUSER_NAME", f'"{label}"')

    def _write_tailwater(self, handle: TextIO, tailwater: TailwaterDefinition) -> None:
        if tailwater.type is not TailwaterType.CONSTANT:
            raise ValueError(
                f"Tailwater type '{tailwater.type.name}' is not supported by run-hy8. "
                "Use the HY-8 GUI for advanced tailwater definitions."
            )
        self._write_card(
            handle,
            "TAILWATERTYPE",
            tailwater.type.value,
        )
        self._write_card(
            handle,
            "CHANNELGEOMETRY",
            tailwater.bottom_width,
            tailwater.sideslope,
            tailwater.channel_slope,
            tailwater.manning_n,
            tailwater.invert_elevation,
        )
        stages: list[float] = self._tailwater_stages(tailwater)
        vel: float = 0.0
        shear: float = 0.0
        froude: float = 0.0
        self._write_card(handle, "NUMRATINGCURVE", len(stages))
        first_stage: float = stages[0] if stages else 0.0
        self._write_card(handle, "TWRATINGCURVE", first_stage, vel, shear, froude)
        for stage in stages:
            handle.write(f"              {stage} {vel} {shear} {froude}\n")

    def _tailwater_stages(self, tailwater: TailwaterDefinition) -> list[float]:
        return [tailwater.constant_elevation] * 6

    def _write_roadway(self, handle: TextIO, crossing: CulvertCrossing) -> None:
        roadway: RoadwayProfile = crossing.roadway
        self._write_card(handle, "ROADWAYSHAPE", roadway.shape)
        self._write_card(handle, "ROADWIDTH", roadway.width)
        self._write_card(handle, "SURFACE", roadway.surface.value)
        self._write_card(handle, "NUMSTATIONS", len(roadway.stations))
        card: str = "ROADWAYSECDATA"
        for station, elevation in roadway.points():
            station: float
            elevation: float
            self._write_card(handle, card, station, elevation)
            card = "ROADWAYPOINT"

    def _write_culvert(self, handle: TextIO, culvert: CulvertBarrel) -> None:
        self._write_card(handle, "STARTCULVERT", f'"{culvert.name}"')
        culvert_shape: int = culvert.shape.value
        culvert_material: int = culvert.material.value
        if culvert.shape is CulvertShape.BOX:
            # HY-8 expects boxes to be flagged as concrete, even if the user set a different material.
            culvert_material = CulvertMaterial.CONCRETE.value
        self._write_card(handle, "CULVERTSHAPE", culvert_shape)
        self._write_card(handle, "CULVERTMATERIAL", culvert_material)
        if culvert.manning_n_top is not None and culvert.manning_n_bottom is not None:
            n_top: float = culvert.manning_n_top
            n_bottom: float = culvert.manning_n_bottom
        else:
            n_top, n_bottom = culvert.manning_values()
        self._write_card(handle, "BARRELDATA", culvert.span, culvert.rise, n_top, n_bottom)
        self._write_card(handle, "EMBANKMENTTYPE", 2)
        self._write_card(handle, "INLETTYPE", culvert.inlet_type)
        self._write_card(handle, "INLETEDGETYPE", culvert.inlet_edge_type)
        self._write_card(handle, "INLETEDGETYPE71", culvert.inlet_edge_type71)
        self._write_card(handle, "IMPINLETEDGETYPE", culvert.improved_inlet_edge_type)
        self._write_card(handle, "NUMBEROFBARRELS", culvert.number_of_barrels)
        self._write_card(
            handle,
            "INVERTDATA",
            culvert.inlet_invert_station,
            culvert.inlet_invert_elevation,
            culvert.outlet_invert_station,
            culvert.outlet_invert_elevation,
        )
        self._write_card(handle, "ROADCULVSTATION", culvert.roadway_station)
        spacing: float = culvert.barrel_spacing if culvert.barrel_spacing is not None else max(culvert.span * 1.5, 0.0)
        self._write_card(handle, "BARRELSPACING", spacing)
        self._write_card(handle, "STARTCULVNOTES", f'"{culvert.notes}"')
        self._write_card(handle, "ENDCULVNOTES")
        self._write_card(handle, "ENDCULVERT", f'"{culvert.name}"')

    @staticmethod
    def _write_card(handle: TextIO, name: str, *values: object) -> None:
        line: str = " ".join(str(value) for value in values if value is not None)
        if line:
            handle.write(f"{name:<20} {line}\n")
        else:
            handle.write(f"{name:<20}\n")
