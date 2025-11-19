"""Single culvert barrel definition for HY-8."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any
from _collections_abc import Mapping

from loguru import logger

from .base import Validatable
from ..type_helpers import (
    CulvertMaterial,
    CulvertShape,
    InletEdgeType,
    InletEdgeType71,
    InletType,
    ImprovedInletEdgeType,
    coerce_enum,
)


@dataclass(slots=True)
class CulvertBarrel(Validatable):
    """Single culvert barrel definition."""

    name: str = ""
    span: float = 0.0
    rise: float = 0.0
    shape: CulvertShape = CulvertShape.CIRCLE
    material: CulvertMaterial = CulvertMaterial.CONCRETE
    number_of_barrels: int = 1
    inlet_invert_station: float = 0.0
    inlet_invert_elevation: float = 0.0
    outlet_invert_station: float = 0.0
    outlet_invert_elevation: float = 0.0
    roadway_station: float = 0.0
    inlet_type: InletType = InletType.STRAIGHT
    inlet_edge_type: InletEdgeType = InletEdgeType.THIN_EDGE_PROJECTING
    inlet_edge_type71: InletEdgeType71 = InletEdgeType71.CODE_0
    improved_inlet_edge_type: ImprovedInletEdgeType = ImprovedInletEdgeType.NONE
    barrel_spacing: float | None = None
    notes: str = ""
    manning_n_top: float | None = None
    manning_n_bottom: float | None = None

    def describe(self) -> str:
        shape: str = self.shape.name
        return (
            f"CulvertBarrel(name={self.name or '<unnamed>'}, shape={shape}, "
            f"span={self.span:.2f}, rise={self.rise:.2f})"
        )

    def __str__(self) -> str:
        return self.describe()

    def __repr__(self) -> str:
        return self.describe()

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "span": self.span,
            "rise": self.rise,
            "shape": self.shape.name,
            "material": self.material.name,
            "number_of_barrels": self.number_of_barrels,
            "inlet_invert_station": self.inlet_invert_station,
            "inlet_invert_elevation": self.inlet_invert_elevation,
            "outlet_invert_station": self.outlet_invert_station,
            "outlet_invert_elevation": self.outlet_invert_elevation,
            "roadway_station": self.roadway_station,
            "inlet_type": self.inlet_type.name,
            "inlet_edge_type": self.inlet_edge_type.name,
            "inlet_edge_type71": self.inlet_edge_type71.name,
            "improved_inlet_edge_type": self.improved_inlet_edge_type.name,
            "barrel_spacing": self.barrel_spacing,
            "notes": self.notes,
            "manning_n_top": self.manning_n_top,
            "manning_n_bottom": self.manning_n_bottom,
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "CulvertBarrel":
        return cls(
            name=data.get("name", ""),
            span=float(data.get("span", 0.0)),
            rise=float(data.get("rise", 0.0)),
            shape=coerce_enum(CulvertShape, data.get("shape"), default=CulvertShape.CIRCLE),
            material=coerce_enum(CulvertMaterial, data.get("material"), default=CulvertMaterial.CONCRETE),
            number_of_barrels=int(data.get("number_of_barrels", 1)),
            inlet_invert_station=float(data.get("inlet_invert_station", 0.0)),
            inlet_invert_elevation=float(data.get("inlet_invert_elevation", 0.0)),
            outlet_invert_station=float(data.get("outlet_invert_station", 0.0)),
            outlet_invert_elevation=float(data.get("outlet_invert_elevation", 0.0)),
            roadway_station=float(data.get("roadway_station", 0.0)),
            inlet_type=coerce_enum(InletType, data.get("inlet_type"), default=InletType.STRAIGHT),
            inlet_edge_type=coerce_enum(
                InletEdgeType, data.get("inlet_edge_type"), default=InletEdgeType.THIN_EDGE_PROJECTING
            ),
            inlet_edge_type71=coerce_enum(
                InletEdgeType71, data.get("inlet_edge_type71"), default=InletEdgeType71.CODE_0
            ),
            improved_inlet_edge_type=coerce_enum(
                ImprovedInletEdgeType, data.get("improved_inlet_edge_type"), default=ImprovedInletEdgeType.NONE
            ),
            barrel_spacing=float(data["barrel_spacing"]) if data.get("barrel_spacing") is not None else None,
            notes=str(data.get("notes", "")),
            manning_n_top=float(data["manning_n_top"]) if data.get("manning_n_top") is not None else None,
            manning_n_bottom=float(data["manning_n_bottom"]) if data.get("manning_n_bottom") is not None else None,
        )

    def validate(self, prefix: str = "") -> list[str]:
        errors: list[str] = []
        if self.span <= 0:
            errors.append(f"{prefix}Culvert span must be greater than zero.")
        if self.rise <= 0:
            errors.append(f"{prefix}Culvert rise must be greater than zero.")
        if self.shape is CulvertShape.BOX and self.rise <= 0:
            errors.append(f"{prefix}Box culverts must include a rise.")
        if self.number_of_barrels <= 0:
            errors.append(f"{prefix}Number of barrels must be >= 1.")
        return errors

    def manning_values(self) -> tuple[float, float]:
        if self.material is CulvertMaterial.CORRUGATED_STEEL:
            return 0.024, 0.024
        return 0.012, 0.012
