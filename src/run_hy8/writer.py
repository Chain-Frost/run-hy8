"""Serialization helpers for .hy8 project files."""

from __future__ import annotations

from pathlib import Path
from typing import TextIO

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
        self.project = project
        self.version = version

    def write(self, output_path: Path, *, overwrite: bool = True) -> Path:
        """Validate and write the project to disk."""
        output_path = output_path.with_suffix(".hy8")
        errors = self.project.validate()
        if errors:
            message = "HY-8 project validation failed:\n" + "\n".join(errors)
            raise ValueError(message)

        if output_path.exists() and not overwrite:
            raise FileExistsError(f"{output_path} already exists. Set overwrite=True to replace it.")

        output_path.parent.mkdir(parents=True, exist_ok=True)
        with output_path.open("w", encoding="utf-8") as handle:
            self._write_project(handle)
        return output_path

    def _write_project(self, handle: TextIO) -> None:
        handle.write(f"HY8PROJECTFILE{self.version}\n")
        handle.write(f"UNITS  {self.project.units.project_flag}\n")
        handle.write(f"EXITLOSSOPTION  {self.project.exit_loss_option}\n")
        handle.write(f"PROJTITLE  {self.project.title}\n")
        handle.write(f"PROJDESIGNER  {self.project.designer}\n")
        handle.write(f"STARTPROJNOTES  {self.project.notes}\nENDPROJNOTES\n")
        handle.write(f"PROJDATE  {self.project.project_timestamp_hours()}\n")
        handle.write(f"NUMCROSSINGS  {len(self.project.crossings)}\n")
        for crossing in self.project.crossings:
            self._write_crossing(handle, crossing)
        handle.write("ENDPROJECTFILE\n")

    def _write_crossing(self, handle: TextIO, crossing: CulvertCrossing) -> None:
        handle.write(f'STARTCROSSING   "{crossing.name}"\n')
        handle.write(f'STARTCROSSNOTES    "{crossing.notes}"\n')
        self._write_flow(handle, crossing)
        self._write_tailwater(handle, crossing.tailwater)
        self._write_roadway(handle, crossing)
        handle.write(f"NUMCULVERTS  {len(crossing.culverts)}\n")
        for culvert in crossing.culverts:
            self._write_culvert(handle, culvert)
        if crossing.uuid:
            handle.write(f"CROSSGUID            {crossing.uuid}\n")
        handle.write("ENDCROSSING\n")

    def _write_flow(self, handle: TextIO, crossing: CulvertCrossing) -> None:
        flow = crossing.flow
        discharge_method = 0 if flow.method is FlowMethod.MIN_DESIGN_MAX else 1
        handle.write(f"DISCHARGERANGE {flow.minimum} {flow.design} {flow.maximum}\n")
        handle.write(f"DISCHARGEMETHOD {discharge_method}\n")
        flow_values = flow.sequence()
        handle.write(f"DISCHARGEXYUSER {len(flow_values)}\n")
        for value in flow_values:
            handle.write(f"DISCHARGEXYUSER_Y {value}\n")

    def _write_tailwater(self, handle: TextIO, tailwater: TailwaterDefinition) -> None:
        if tailwater.type is not TailwaterType.CONSTANT:
            raise ValueError(
                f"Tailwater type '{tailwater.type.name}' is not supported by run-hy8. "
                "Use the HY-8 GUI for advanced tailwater definitions."
            )
        handle.write(f"TAILWATERTYPE {tailwater.type.value}\n")
        handle.write(
            "CHANNELGEOMETRY "
            f"{tailwater.bottom_width} "
            f"{tailwater.sideslope} "
            f"{tailwater.channel_slope} "
            f"{tailwater.manning_n} "
            f"{tailwater.invert_elevation}\n"
        )
        stages = self._tailwater_stages(tailwater)
        vel = shear = froude = 0.0
        handle.write(f"NUMRATINGCURVE {len(stages)}\n")
        first_stage = stages[0] if stages else 0.0
        handle.write(f"TWRATINGCURVE {first_stage} {vel} {shear} {froude}\n")
        for stage in stages:
            handle.write(f"              {stage} {vel} {shear} {froude}\n")

    def _tailwater_stages(self, tailwater: TailwaterDefinition) -> list[float]:
        return [tailwater.constant_elevation] * 6

    def _write_roadway(self, handle: TextIO, crossing: CulvertCrossing) -> None:
        roadway = crossing.roadway
        handle.write(f"ROADWAYSHAPE {roadway.shape}\n")
        handle.write(f"ROADWIDTH {roadway.width}\n")
        handle.write(f"SURFACE {roadway.surface.value}\n")
        handle.write(f"NUMSTATIONS {len(roadway.stations)}\n")
        card = "ROADWAYSECDATA"
        for station, elevation in roadway.points():
            handle.write(f"{card} {station} {elevation}\n")
            card = "ROADWAYPOINT"

    def _write_culvert(self, handle: TextIO, culvert: CulvertBarrel) -> None:
        handle.write(f'STARTCULVERT    "{culvert.name}"\n')
        culvert_shape = culvert.shape.value
        culvert_material = culvert.material.value
        if culvert.shape is CulvertShape.BOX:
            # HY-8 expects boxes to be flagged as concrete, even if the user set a different material.
            culvert_material = CulvertMaterial.CONCRETE.value
        handle.write(f"CULVERTSHAPE    {culvert_shape}\n")
        handle.write(f"CULVERTMATERIAL {culvert_material}\n")
        if culvert.manning_n_top is not None and culvert.manning_n_bottom is not None:
            n_top = culvert.manning_n_top
            n_bottom = culvert.manning_n_bottom
        else:
            n_top, n_bottom = culvert.manning_values()
        handle.write(f"BARRELDATA  {culvert.span} {culvert.rise} {n_top} {n_bottom}\n")
        handle.write("EMBANKMENTTYPE 2\n")
        handle.write(f"NUMBEROFBARRELS {culvert.number_of_barrels}\n")
        handle.write(
            "INVERTDATA "
            f"{culvert.inlet_invert_station} {culvert.inlet_invert_elevation} "
            f"{culvert.outlet_invert_station} {culvert.outlet_invert_elevation}\n"
        )
        handle.write(f"ROADCULVSTATION {culvert.roadway_station}\n")
        spacing = culvert.barrel_spacing if culvert.barrel_spacing is not None else max(culvert.span * 1.5, 0.0)
        handle.write(f"BARRELSPACING {spacing}\n")
        handle.write(f'STARTCULVNOTES "{culvert.notes}"\nENDCULVNOTES\n')
        handle.write("ENDCULVERT\n")
