"""Domain models that describe HY-8 projects."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Sequence


class UnitSystem(Enum):
    """Supported unit systems."""

    ENGLISH = ("EN", 0)
    SI = ("SI", 1)

    def __init__(self, cli_flag: str, project_flag: int) -> None:
        self.cli_flag: str = cli_flag
        self.project_flag: int = project_flag


class FlowMethod(str, Enum):
    """How HY-8 should interpret the flow definition."""

    MIN_DESIGN_MAX = "min-design-max"
    MIN_MAX_INCREMENT = "min-max-increment"
    USER_DEFINED = "user-defined"


class TailwaterType(int, Enum):
    RECTANGULAR = 1
    TRAPEZOIDAL = 2
    TRIANGULAR = 3
    IRREGULAR = 4
    RATING_CURVE = 5
    CONSTANT = 6


class RoadwaySurface(int, Enum):
    PAVED = 1
    GRAVEL = 2
    USER_DEFINED = 3


class CulvertShape(int, Enum):
    CIRCLE = 1
    BOX = 2


class CulvertMaterial(int, Enum):
    CONCRETE = 1
    CORRUGATED_STEEL = 2
    HDPE = 5


TailwaterRatingPoint = tuple[float, float, float]


def _float_list() -> list[float]:
    return []


def _string_list() -> list[str]:
    return []


def _rating_curve_list() -> list[TailwaterRatingPoint]:
    return []


def _culvert_list() -> list["CulvertBarrel"]:
    return []


def _crossing_list() -> list["CulvertCrossing"]:
    return []


@dataclass(slots=True)
class FlowDefinition:
    """Flow information for a crossing."""

    method: FlowMethod = FlowMethod.MIN_DESIGN_MAX
    minimum: float = 0.0
    design: float = 0.0
    maximum: float = 0.0
    increment: float = 0.0
    user_values: list[float] = field(default_factory=_float_list)
    user_value_labels: list[str] = field(default_factory=_string_list)

    def sequence(self) -> list[float]:
        """Return the flows HY-8 expects to see in the DISCHARGEXYUSER cards."""
        if self.method is FlowMethod.USER_DEFINED:
            return list(self.user_values)
        if self.method is FlowMethod.MIN_MAX_INCREMENT:
            values: list[float] = []
            if self.increment <= 0:
                return values
            current: float = self.minimum
            # Add a small epsilon to include the end point when the increment is fractional.
            epsilon: float = self.increment / 1000.0
            while current <= self.maximum + epsilon:
                values.append(round(current, 6))
                current += self.increment
            return values
        return [self.minimum, self.design, self.maximum]

    def validate(self, prefix: str = "") -> list[str]:
        errors: list[str] = []
        if self.method is FlowMethod.MIN_DESIGN_MAX:
            if not self.minimum < self.design < self.maximum:
                errors.append(f"{prefix}Min/Design/Max must be strictly increasing.")
            if self.minimum < 0:
                errors.append(f"{prefix}Minimum flow must be >= 0.")
        elif self.method is FlowMethod.MIN_MAX_INCREMENT:
            if not self.minimum < self.maximum:
                errors.append(f"{prefix}Minimum flow must be less than maximum flow.")
            if self.increment <= 0:
                errors.append(f"{prefix}Flow increment must be greater than zero.")
        elif self.method is FlowMethod.USER_DEFINED:
            if len(self.user_values) < 2:
                errors.append(f"{prefix}Provide at least two user-defined flow values.")
            elif any(a >= b for a, b in zip(self.user_values, self.user_values[1:])):
                errors.append(f"{prefix}User-defined flows must be strictly increasing.")
            if self.user_value_labels and len(self.user_value_labels) != len(self.user_values):
                errors.append(f"{prefix}Provide the same number of flow labels as flow values.")
        else:
            errors.append(f"{prefix}Unknown flow method '{self.method}'.")
        return errors


@dataclass(slots=True)
class TailwaterDefinition:
    """Tailwater configuration."""

    type: TailwaterType = TailwaterType.CONSTANT
    bottom_width: float = 0.0
    sideslope: float = 1.0
    channel_slope: float = 0.0
    manning_n: float = 0.0
    constant_elevation: float = 0.0
    invert_elevation: float = 0.0
    rating_curve_entries: int = 6
    rating_curve: list[TailwaterRatingPoint] = field(default_factory=_rating_curve_list)

    def validate(self, prefix: str = "") -> list[str]:
        errors: list[str] = []
        if self.type is not TailwaterType.CONSTANT:
            errors.append(
                f"{prefix}Tailwater type '{self.type.name}' is not supported by run-hy8. "
                "Configure a constant tailwater elevation or use the HY-8 GUI."
            )
            return errors

        if self.constant_elevation < self.invert_elevation:
            errors.append(
                f"{prefix}Constant tailwater elevation must be greater than or equal to the invert elevation."
            )
        return errors

    def rating_curve_rows(self) -> list[TailwaterRatingPoint]:
        return list(self.rating_curve)


@dataclass(slots=True)
class RoadwayProfile:
    """Roadway geometry and metadata."""

    width: float = 0.0
    shape: int = 1
    surface: RoadwaySurface = RoadwaySurface.PAVED
    stations: list[float] = field(default_factory=_float_list)
    elevations: list[float] = field(default_factory=_float_list)

    def points(self) -> list[tuple[float, float]]:
        return list(zip(self.stations, self.elevations))

    def validate(self, prefix: str = "") -> list[str]:
        errors: list[str] = []
        if self.width <= 0:
            errors.append(f"{prefix}Roadway width must be > 0.")
        if len(self.stations) < 2 or len(self.elevations) < 2:
            errors.append(f"{prefix}Provide at least two roadway stations/elevations.")
        if len(self.stations) != len(self.elevations):
            errors.append(f"{prefix}Stations and elevations counts must match.")
        return errors

    def crest_elevation(self) -> float:
        if not self.elevations:
            raise ValueError("Roadway elevations are required before computing crest elevation.")
        return min(self.elevations)


@dataclass(slots=True)
class CulvertBarrel:
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
    inlet_type: int = 1
    inlet_edge_type: int = 0
    inlet_edge_type71: int = 0
    improved_inlet_edge_type: int = 0
    barrel_spacing: float | None = None
    notes: str = ""
    manning_n_top: float | None = None
    manning_n_bottom: float | None = None

    def validate(self, prefix: str = "") -> list[str]:
        errors: list[str] = []
        if self.span <= 0:
            errors.append(f"{prefix}Span must be greater than zero.")
        if self.shape is CulvertShape.BOX and self.rise <= 0:
            errors.append(f"{prefix}Box culverts must include a rise.")
        if self.number_of_barrels <= 0:
            errors.append(f"{prefix}Number of barrels must be >= 1.")
        return errors

    def manning_values(self) -> tuple[float, float]:
        if self.material is CulvertMaterial.CORRUGATED_STEEL:
            return 0.024, 0.024
        return 0.012, 0.012


@dataclass(slots=True)
class CulvertCrossing:
    """A culvert crossing which may contain multiple barrels."""

    name: str
    notes: str = ""
    flow: FlowDefinition = field(default_factory=FlowDefinition)
    tailwater: TailwaterDefinition = field(default_factory=TailwaterDefinition)
    roadway: RoadwayProfile = field(default_factory=RoadwayProfile)
    culverts: list[CulvertBarrel] = field(default_factory=_culvert_list)
    uuid: str | None = None

    def validate(self, prefix: str = "") -> list[str]:
        errors: list[str] = []
        flow_prefix: str = f"{prefix}Flow: "
        errors.extend(self.flow.validate(flow_prefix))
        tw_prefix: str = f"{prefix}Tailwater: "
        errors.extend(self.tailwater.validate(tw_prefix))
        roadway_prefix: str = f"{prefix}Roadway: "
        errors.extend(self.roadway.validate(roadway_prefix))
        if not self.culverts:
            errors.append(f"{prefix}At least one culvert barrel is required.")
        for index, culvert in enumerate(self.culverts, start=1):
            culvert_prefix: str = f"{prefix}Culvert #{index} ({culvert.name}): "
            errors.extend(culvert.validate(culvert_prefix))
        if self.roadway.elevations:
            road_crest: float = self.roadway.crest_elevation()
            if self.tailwater.constant_elevation >= road_crest:
                errors.append(
                    f"{prefix}Constant tailwater elevation ({self.tailwater.constant_elevation}) "
                    f"reaches or exceeds the roadway crest ({road_crest}). "
                    "Lower the tailwater or use the HY-8 GUI for overtopping conditions."
                )
        return errors


@dataclass(slots=True)
class Hy8Project:
    """A full HY-8 project containing one or more crossings."""

    title: str = ""
    designer: str = ""
    notes: str = ""
    units: UnitSystem = UnitSystem.SI
    exit_loss_option: int = 0
    crossings: list[CulvertCrossing] = field(default_factory=_crossing_list)

    def validate(self) -> list[str]:
        errors: list[str] = []
        if not self.crossings:
            errors.append("At least one crossing is required.")
        for index, crossing in enumerate(self.crossings, start=1):
            prefix: str = f"Crossing #{index} ({crossing.name}): "
            errors.extend(crossing.validate(prefix))
        return errors

    @staticmethod
    def project_timestamp_hours() -> float:
        """HY-8 expects the project date as hours since epoch."""
        return datetime.now().timestamp() / 3600.0

    def add_crossing(self, crossing: CulvertCrossing | None = None) -> CulvertCrossing:
        if crossing is None:
            crossing = CulvertCrossing(name=f"Crossing {len(self.crossings) + 1}")
        self.crossings.append(crossing)
        return crossing

    def flow_values(self) -> Sequence[list[float]]:
        return [crossing.flow.sequence() for crossing in self.crossings]
