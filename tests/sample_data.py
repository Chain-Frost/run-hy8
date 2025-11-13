"""Shared sample data structures used across tests."""

from __future__ import annotations

import json

from run_hy8 import (
    CulvertBarrel,
    CulvertCrossing,
    CulvertMaterial,
    CulvertShape,
    FlowDefinition,
    FlowMethod,
    Hy8Project,
    RoadwaySurface,
)

CONFIG_MAPPING: dict[str, object] = {
    "project": {
        "title": "Sample Project",
        "designer": "Hydraulics Team",
        "units": "EN",
    },
    "crossings": [
        {
            "name": "Sample Crossing",
            "flow": {"minimum": 5.0, "design": 10.0, "maximum": 15.0},
            "tailwater": {"constant_elevation": 100.5, "invert_elevation": 99.0},
            "roadway": {
                "width": 36.0,
                "surface": "paved",
                "stations": [-15.0, 0.0, 15.0],
                "elevations": [102.0, 101.5, 102.0],
            },
            "culverts": [
                {
                    "name": "Barrel 1",
                    "shape": "circle",
                    "material": "concrete",
                    "span": 4.0,
                    "rise": 4.0,
                    "inlet_invert_elevation": 98.5,
                    "outlet_invert_elevation": 98.0,
                }
            ],
        }
    ],
}

CONFIG_JSON: str = json.dumps(CONFIG_MAPPING, indent=2)


def build_sample_project() -> Hy8Project:
    """Construct a Hy8Project that mirrors the fixture configuration."""

    project = Hy8Project(title="Sample Project", designer="Hydraulics Team")
    crossing = CulvertCrossing(name="Sample Crossing")
    crossing.flow = FlowDefinition(minimum=5.0, design=10.0, maximum=15.0)
    crossing.tailwater.constant_elevation = 100.5
    crossing.tailwater.invert_elevation = 99.0
    crossing.roadway.width = 36.0
    crossing.roadway.shape = 2
    crossing.roadway.surface = RoadwaySurface.PAVED
    crossing.roadway.stations = [-15.0, 0.0, 15.0]
    crossing.roadway.elevations = [102.0, 101.5, 102.0]
    crossing.culverts.append(
        CulvertBarrel(
            name="Barrel 1",
            span=4.0,
            rise=4.0,
            material=CulvertMaterial.CONCRETE,
            shape=CulvertShape.CIRCLE,
            inlet_invert_elevation=98.5,
            outlet_invert_elevation=98.0,
        )
    )
    project.crossings.append(crossing)
    return project


def build_two_crossing_project() -> Hy8Project:
    project = Hy8Project(title="Two Crossings", designer="Hydraulics Team")

    first = build_sample_project().crossings[0]
    project.crossings.append(first)

    second = CulvertCrossing(name="Second Crossing")
    second.flow.method = FlowMethod.MIN_MAX_INCREMENT
    second.flow.minimum = 0.0
    second.flow.maximum = 30.0
    second.flow.increment = 10.0
    second.tailwater.constant_elevation = 150.0
    second.tailwater.invert_elevation = 148.5
    second.roadway.width = 40.0
    second.roadway.shape = 1
    second.roadway.surface = RoadwaySurface.GRAVEL
    second.roadway.stations = [-10.0, 0.0, 10.0]
    second.roadway.elevations = [151.0, 150.5, 151.0]
    second.culverts.append(
        CulvertBarrel(
            name="Box Culvert",
            span=6.0,
            rise=5.0,
            shape=CulvertShape.BOX,
            material=CulvertMaterial.CONCRETE,
            inlet_invert_elevation=149.0,
            outlet_invert_elevation=148.8,
        )
    )
    second.culverts.append(
        CulvertBarrel(
            name="Steel Barrel",
            span=3.0,
            rise=3.0,
            shape=CulvertShape.CIRCLE,
            material=CulvertMaterial.CORRUGATED_STEEL,
            inlet_invert_elevation=149.2,
            outlet_invert_elevation=149.0,
            number_of_barrels=2,
        )
    )
    project.crossings.append(second)
    return project


def build_user_defined_project() -> Hy8Project:
    project = Hy8Project(title="User Defined Flow", designer="Hydraulics Team")
    crossing = CulvertCrossing(name="User Crossing")
    crossing.flow.method = FlowMethod.USER_DEFINED
    crossing.flow.user_values = [2.5, 5.0, 7.5, 10.0]
    crossing.tailwater.constant_elevation = 200.0
    crossing.tailwater.invert_elevation = 199.0
    crossing.roadway.width = 30.0
    crossing.roadway.shape = 1
    crossing.roadway.surface = RoadwaySurface.USER_DEFINED
    crossing.roadway.stations = [-12.0, 0.0, 12.0]
    crossing.roadway.elevations = [201.0, 200.5, 201.0]
    crossing.culverts.append(
        CulvertBarrel(
            name="Triple Barrel",
            span=2.5,
            rise=2.5,
            number_of_barrels=3,
            inlet_invert_elevation=198.5,
            outlet_invert_elevation=198.0,
        )
    )
    crossing.culverts.append(
        CulvertBarrel(
            name="Small Box",
            span=4.0,
            rise=3.0,
            shape=CulvertShape.BOX,
            material=CulvertMaterial.CONCRETE,
            inlet_invert_elevation=198.8,
            outlet_invert_elevation=198.2,
        )
    )
    project.crossings.append(crossing)
    return project
