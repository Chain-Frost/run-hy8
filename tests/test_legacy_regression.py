"""Regression tests that compare run_hy8 output with the legacy Hy8Runner."""

from __future__ import annotations

from pathlib import Path
from typing import Callable

import pytest

from .hy8runner.hy8_runner import Hy8Runner

from run_hy8 import (
    CulvertBarrel,
    CulvertMaterial,
    CulvertShape,
    FlowMethod,
    Hy8Project,
    RoadwaySurface,
    UnitSystem,
)
from run_hy8.writer import Hy8FileWriter

from .sample_data import (
    build_sample_project,
    build_two_crossing_project,
    build_user_defined_project,
)

PROJECT_BUILDERS: list[tuple[str, Callable[[], Hy8Project]]] = [
    ("sample", build_sample_project),
    ("two_crossings", build_two_crossing_project),
    ("user_defined", build_user_defined_project),
]


@pytest.mark.parametrize(("name", "builder"), PROJECT_BUILDERS, ids=[name for name, _ in PROJECT_BUILDERS])
def test_generated_file_matches_legacy(tmp_path: Path, name: str, builder: Callable[[], Hy8Project]) -> None:
    project: Hy8Project = builder()
    new_file: Path = Hy8FileWriter(project=project).write(output_path=tmp_path / f"{name}_new.hy8")
    legacy_file: Path = _write_with_legacy(project=project, working_dir=tmp_path / f"{name}_legacy")

    assert _normalize(contents=new_file.read_text(encoding="utf-8")) == _normalize(
        contents=legacy_file.read_text(encoding="utf-8")
    )


def _write_with_legacy(project: Hy8Project, working_dir: Path) -> Path:
    working_dir.mkdir(parents=True, exist_ok=True)
    exe_path: Path = working_dir / "HY864.exe"
    exe_path.write_bytes(b"")

    hy8_path: Path = working_dir / "legacy.hy8"
    runner = Hy8Runner(str(exe_path.parent), str(hy8_path))
    runner.project_title = project.title
    runner.designer_name = project.designer
    runner.project_notes = project.notes
    runner.set_hy8_exe_path(str(exe_path.parent))
    runner.set_hy8_file(str(hy8_path))
    type(runner).si_units = project.units is UnitSystem.SI
    type(runner).exit_loss_option = project.exit_loss_option

    while len(runner.crossings) < len(project.crossings):
        runner.add_crossing()
    while len(runner.crossings) > len(project.crossings):
        runner.delete_crossing(len(runner.crossings) - 1)

    for index, crossing in enumerate(project.crossings):
        runner.set_culvert_crossing_name(crossing.name, index=index)
        if crossing.flow.method is FlowMethod.MIN_DESIGN_MAX:
            runner.set_discharge_min_design_max_flow(
                flow_min=crossing.flow.minimum,
                flow_design=crossing.flow.design,
                flow_max=crossing.flow.maximum,
                index=index,
            )
        elif crossing.flow.method is FlowMethod.MIN_MAX_INCREMENT:
            runner.set_discharge_min_max_inc_flow(
                flow_min=crossing.flow.minimum,
                flow_max=crossing.flow.maximum,
                flow_increment=crossing.flow.increment,
                index=index,
            )
        else:
            runner.set_discharge_user_list_flow(crossing.flow.sequence(), index=index)

        runner.set_tw_constant(
            tw_invert_elevation=crossing.tailwater.invert_elevation,
            tw_constant_elevation=crossing.tailwater.constant_elevation,
            index=index,
        )

        runner.set_roadway_width(roadway_width=crossing.roadway.width, index=index)
        runner.set_roadway_surface(roadway_surface=_surface_name(surface=crossing.roadway.surface), index=index)
        runner.set_roadway_stations_and_elevations(
            stations=crossing.roadway.stations,
            elevations=crossing.roadway.elevations,
            index=index,
        )
        runner.crossings[index].roadway_shape = crossing.roadway.shape

        _synchronize_culverts(runner=runner, culverts=crossing.culverts, crossing_index=index)

    success, messages = runner.create_hy8_file()
    assert success, messages
    return hy8_path


def _synchronize_culverts(runner: Hy8Runner, culverts: list[CulvertBarrel], crossing_index: int) -> None:
    crossing = runner.crossings[crossing_index]
    while len(crossing.culverts) < len(culverts):
        runner.add_culvert_barrel(index_crossing=crossing_index)
    while len(crossing.culverts) > len(culverts):
        runner.delete_culvert_barrel(index_crossing=crossing_index, index_culvert=len(crossing.culverts) - 1)

    for culvert_index, culvert in enumerate(culverts):
        runner.set_culvert_barrel_name(
            name=culvert.name or f"Culvert {culvert_index + 1}",
            index_crossing=crossing_index,
            index_culvert=culvert_index,
        )
        runner.set_culvert_barrel_shape(
            shape=_shape_name(shape=culvert.shape),
            index_crossing=crossing_index,
            index_culvert=culvert_index,
        )
        rise: float = culvert.rise if culvert.rise > 0 else culvert.span
        runner.set_culvert_barrel_span_and_rise(
            span=culvert.span,
            rise=rise,
            index_crossing=crossing_index,
            index_culvert=culvert_index,
        )
        runner.set_culvert_barrel_material(
            material=_material_name(material=culvert.material),
            index_crossing=crossing_index,
            index_culvert=culvert_index,
        )
        runner.set_culvert_barrel_site_data(
            inlet_invert_station=culvert.inlet_invert_station,
            inlet_invert_elevation=culvert.inlet_invert_elevation,
            outlet_invert_station=culvert.outlet_invert_station,
            outlet_invert_elevation=culvert.outlet_invert_elevation,
            index_crossing=crossing_index,
            index_culvert=culvert_index,
        )
        runner.set_culvert_barrel_number_of_barrels(
            number_of_barrels=culvert.number_of_barrels,
            index_crossing=crossing_index,
            index_culvert=culvert_index,
        )
        runner.crossings[crossing_index].culverts[culvert_index].notes = culvert.notes


def _surface_name(surface: RoadwaySurface) -> str:
    mapping: dict[RoadwaySurface, str] = {
        RoadwaySurface.PAVED: "paved",
        RoadwaySurface.GRAVEL: "gravel",
        RoadwaySurface.USER_DEFINED: "user-defined",
    }
    return mapping[surface]


def _shape_name(shape: CulvertShape) -> str:
    mapping: dict[CulvertShape, str] = {
        CulvertShape.CIRCLE: "circle",
        CulvertShape.BOX: "box",
    }
    return mapping[shape]


def _material_name(material: CulvertMaterial) -> str:
    mapping: dict[CulvertMaterial, str] = {
        CulvertMaterial.CONCRETE: "concrete",
        CulvertMaterial.CORRUGATED_STEEL: "corrugated steel",
    }
    return mapping[material]


def _normalize(contents: str) -> list[str]:
    lines: list[str] = []
    for line in contents.splitlines():
        if line.startswith("PROJDATE"):
            continue
        lines.append(" ".join(line.split()))
    return lines
