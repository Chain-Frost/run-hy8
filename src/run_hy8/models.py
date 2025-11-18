"""Domain models that describe HY-8 projects."""

from __future__ import annotations

from collections import OrderedDict
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum, IntEnum
from pathlib import Path
from typing import TYPE_CHECKING, Any, Mapping, Sequence, Type, TypeVar

from loguru import logger

if TYPE_CHECKING:  # pragma: no cover - convenience imports for type checking
    from .executor import Hy8Executable
    from .hydraulics import HydraulicsResult


TEnum = TypeVar("TEnum", bound=Enum)


class ValidationError(ValueError):
    """Exception raised when a model fails validation."""

    def __init__(self, errors: Sequence[str]):
        self.errors: list[str] = list(errors)
        message: str = "; ".join(self.errors) if self.errors else "Unknown validation error."
        super().__init__(message)


class Validatable:
    """Mixin that supplies an assert_valid helper for domain models."""

    def assert_valid(self, prefix: str = "") -> None:
        errors = self.validate(prefix=prefix)  # type: ignore[call-arg]
        if errors:
            logger.debug("Validation failed for %s: %s", self.__class__.__name__, errors)
            raise ValidationError(errors)
        logger.debug("Validation succeeded for %s.", self.__class__.__name__)


def _coerce_enum(enum_cls: Type[TEnum], value: Any, *, default: TEnum) -> TEnum:
    """Return enum member from the provided value, accepting names/values."""

    if value is None:
        return default
    if isinstance(value, enum_cls):
        return value
    if isinstance(value, str):
        try:
            return enum_cls[value]
        except KeyError:
            pass
    return enum_cls(value)


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
    """Tailwater boundary condition categories supported by HY-8."""

    RECTANGULAR = 1
    TRAPEZOIDAL = 2
    TRIANGULAR = 3
    IRREGULAR = 4
    RATING_CURVE = 5
    CONSTANT = 6


class RoadwaySurface(int, Enum):
    """Roadway surface assumptions used when HY-8 estimates friction losses."""

    PAVED = 1
    GRAVEL = 2
    USER_DEFINED = 3


class _DescribedIntEnum(IntEnum):
    """Base class for HY-8 enums that exposes a user-friendly label."""

    def __new__(cls, value: int, label: str) -> "_DescribedIntEnum":
        obj = int.__new__(cls, value)
        obj._value_ = value
        obj._label_ = label
        return obj

    @property
    def label(self) -> str:
        return self._label_


class InletType(_DescribedIntEnum):
    """HY-8 inlet geometry definitions."""

    NOT_SET = 0, "Not set"
    STRAIGHT = 1, "Straight"
    SIDE_TAPERED = 2, "Side tapered"
    SLOPE_TAPERED = 3, "Slope tapered"
    SINGLE_BROKEN_BACK = 4, "Single broken-back"
    DOUBLE_BROKEN_BACK = 5, "Double broken-back"


class InletEdgeType(_DescribedIntEnum):
    """HY-8 inlet edge types for current releases."""

    THIN_EDGE_PROJECTING = 0, "Thin edge projecting"
    GROOVED_END_PROJECTING = 1, "Grooved end projecting"
    GROOVED_END_WITH_HEADWALL = 2, "Grooved end with headwall"
    BEVELED_EDGE = 3, "Beveled edge"
    SQUARE_EDGE_WITH_HEADWALL = 4, "Square edge with headwall"
    MITERED_TO_SLOPE = 5, "Mitered to conform with fill slope"
    HEADWALL = 6, "Headwall / flared end"


class InletEdgeType71(_DescribedIntEnum):
    """Legacy HY-8 7.1 inlet edge numbering."""

    CODE_0 = 0, "Legacy edge code 0"
    CODE_1 = 1, "Legacy edge code 1"
    CODE_2 = 2, "Legacy edge code 2"
    CODE_3 = 3, "Legacy edge code 3"
    CODE_4 = 4, "Legacy edge code 4"


class ImprovedInletEdgeType(_DescribedIntEnum):
    """Enhanced inlet edge treatments used by the optimized HY-8 options."""

    NONE = 0, "None"
    TYPE_1 = 1, "Improved inlet type 1"
    TYPE_2 = 2, "Improved inlet type 2"
    TYPE_3 = 3, "Improved inlet type 3"
    TYPE_4 = 4, "Improved inlet type 4"
    TYPE_5 = 5, "Improved inlet type 5"
    TYPE_6 = 6, "Improved inlet type 6"


class CulvertShape(int, Enum):
    """Culvert barrel shapes supported by HY-8."""

    CIRCLE = 1
    BOX = 2


class CulvertMaterial(int, Enum):
    """Material identifiers used throughout HY-8 projects."""

    CONCRETE = 1
    CORRUGATED_STEEL = 2
    HDPE = 5


TailwaterRatingPoint = tuple[float, float, float]


def _float_list() -> list[float]:
    """Return a new list[float]; helper avoids mutable default arguments."""
    return []


def _string_list() -> list[str]:
    """Return a new list[str] for dataclass default_factory."""
    return []


def _rating_curve_list() -> list[TailwaterRatingPoint]:
    """Return an empty rating-curve list for dataclass defaults."""
    return []


def _culvert_list() -> list["CulvertBarrel"]:
    """Return a fresh list of CulvertBarrel instances for defaults."""
    return []


def _crossing_list() -> list["CulvertCrossing"]:
    """Return a fresh list of CulvertCrossing objects for defaults."""
    return []


@dataclass(slots=True)
class FlowDefinition(Validatable):
    """Flow information for a crossing.

    FlowMethod.MIN_DESIGN_MAX problems must provide exactly three flows via
    `minimum`/`design`/`maximum` or `user_values`.
    FlowMethod.USER_DEFINED problems require at least two `user_values` and
    may include matching `user_value_labels`.
    """

    method: FlowMethod = FlowMethod.USER_DEFINED
    minimum: float = 0.0
    design: float = 0.0
    maximum: float = 0.0
    user_values: list[float] = field(default_factory=_float_list)
    user_value_labels: list[str] = field(default_factory=_string_list)

    def describe(self) -> str:
        try:
            values: list[float] = self.sequence()
        except ValueError:
            values = []
        preview = ", ".join(f"{value:.3f}" for value in values[:3])
        if len(values) > 3:
            preview += ", ..."
        return f"FlowDefinition(method={self.method.name}, count={len(values)}, values=[{preview}])"

    def __str__(self) -> str:
        return self.describe()

    def __repr__(self) -> str:
        return self.describe()

    def sequence(self) -> list[float]:
        """Return the flows HY-8 expects to see in the DISCHARGEXYUSER cards."""
        if self.method is FlowMethod.MIN_DESIGN_MAX:
            return self._min_design_max_values()
        if self.method is FlowMethod.USER_DEFINED:
            return list(self.user_values)
        raise ValueError(f"Flow method '{self.method}' is not supported.")

    def add_user_flow(self, value: float, label: str | None = None) -> "FlowDefinition":
        """Append a user-defined flow (and optional label) while maintaining invariants."""

        self.method = FlowMethod.USER_DEFINED
        self.user_values.append(value)
        if label is not None:
            while len(self.user_value_labels) < len(self.user_values) - 1:
                self.user_value_labels.append("")
            self.user_value_labels.append(label)
        elif self.user_value_labels:
            self.user_value_labels.append("")
        logger.debug("Added user flow %.4f to %s", value, self.describe())
        return self

    def set_min_design_max(self, minimum: float, design: float, maximum: float) -> "FlowDefinition":
        """Configure the Min/Design/Max trio in a fluent-friendly way."""

        self.method = FlowMethod.MIN_DESIGN_MAX
        self.minimum = minimum
        self.design = design
        self.maximum = maximum
        self.user_values.clear()
        self.user_value_labels.clear()
        logger.debug(
            "Configured min/design/max flows (%.4f/%.4f/%.4f) for %s",
            minimum,
            design,
            maximum,
            self.describe(),
        )
        return self

    def to_dict(self) -> dict[str, Any]:
        return {
            "method": self.method.name,
            "minimum": self.minimum,
            "design": self.design,
            "maximum": self.maximum,
            "user_values": list(self.user_values),
            "user_value_labels": list(self.user_value_labels),
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "FlowDefinition":
        method_value = data.get("method", FlowMethod.USER_DEFINED.name)
        method = _coerce_enum(FlowMethod, method_value, default=FlowMethod.USER_DEFINED)
        return cls(
            method=method,
            minimum=float(data.get("minimum", 0.0)),
            design=float(data.get("design", 0.0)),
            maximum=float(data.get("maximum", 0.0)),
            user_values=[float(value) for value in (data.get("user_values") or [])],
            user_value_labels=[str(value) for value in (data.get("user_value_labels") or [])],
        )

    def validate(self, prefix: str = "") -> list[str]:
        errors: list[str] = []
        if self.method is FlowMethod.MIN_DESIGN_MAX:
            if self.user_values and len(self.user_values) != 3:
                errors.append(f"{prefix}Provide exactly three flows for Min/Design/Max problems.")
            values: list[float] = self._min_design_max_values()
            if len(values) != 3:
                return errors
            if not values[0] < values[1] < values[2]:
                errors.append(f"{prefix}Min/Design/Max must be strictly increasing.")
            if values[0] < 0:
                errors.append(f"{prefix}Minimum flow must be >= 0.")
        elif self.method is FlowMethod.USER_DEFINED:
            if len(self.user_values) < 2:
                errors.append(f"{prefix}Provide at least two user-defined flow values.")
            elif any(a >= b for a, b in zip(self.user_values, self.user_values[1:])):
                errors.append(f"{prefix}User-defined flows must be strictly increasing.")
            if self.user_value_labels and len(self.user_value_labels) != len(self.user_values):
                errors.append(f"{prefix}Provide the same number of flow labels as flow values.")
        else:
            errors.append(f"{prefix}Flow method '{self.method}' is not supported.")
        return errors

    def _min_design_max_values(self) -> list[float]:
        if self.user_values:
            return list(self.user_values)
        return [self.minimum, self.design, self.maximum]


@dataclass(slots=True)
class TailwaterDefinition(Validatable):
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

    def describe(self) -> str:
        if self.type is TailwaterType.CONSTANT:
            return (
                f"Tailwater(type=CONSTANT, elevation={self.constant_elevation:.3f}, "
                f"invert={self.invert_elevation:.3f})"
            )
        return f"Tailwater(type={self.type.name}, entries={len(self.rating_curve)})"

    def __str__(self) -> str:
        return self.describe()

    def __repr__(self) -> str:
        return self.describe()

    def set_constant(self, *, elevation: float, invert: float | None = None) -> "TailwaterDefinition":
        """Fluent helper to configure a constant tailwater elevation."""

        self.type = TailwaterType.CONSTANT
        self.constant_elevation = elevation
        if invert is not None:
            self.invert_elevation = invert
        logger.debug(
            "Configured constant tailwater elevation %.4f (invert %.4f)",
            self.constant_elevation,
            self.invert_elevation,
        )
        return self

    def to_dict(self) -> dict[str, Any]:
        return {
            "type": self.type.name,
            "bottom_width": self.bottom_width,
            "sideslope": self.sideslope,
            "channel_slope": self.channel_slope,
            "manning_n": self.manning_n,
            "constant_elevation": self.constant_elevation,
            "invert_elevation": self.invert_elevation,
            "rating_curve_entries": self.rating_curve_entries,
            "rating_curve": [tuple(point) for point in self.rating_curve],
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "TailwaterDefinition":
        rating_curve_data = [
            (float(a), float(b), float(c))
            for a, b, c in (data.get("rating_curve") or [])
        ]
        return cls(
            type=_coerce_enum(TailwaterType, data.get("type"), default=TailwaterType.CONSTANT),
            bottom_width=float(data.get("bottom_width", 0.0)),
            sideslope=float(data.get("sideslope", 1.0)),
            channel_slope=float(data.get("channel_slope", 0.0)),
            manning_n=float(data.get("manning_n", 0.0)),
            constant_elevation=float(data.get("constant_elevation", 0.0)),
            invert_elevation=float(data.get("invert_elevation", 0.0)),
            rating_curve_entries=int(data.get("rating_curve_entries", 6)),
            rating_curve=rating_curve_data,
        )

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
class RoadwayProfile(Validatable):
    """Roadway geometry and metadata."""

    width: float = 0.0
    shape: int = 1
    surface: RoadwaySurface = RoadwaySurface.PAVED
    stations: list[float] = field(default_factory=_float_list)
    elevations: list[float] = field(default_factory=_float_list)

    def describe(self) -> str:
        count: int = min(len(self.stations), len(self.elevations))
        return f"Roadway(width={self.width:.3f}, points={count})"

    def __str__(self) -> str:
        return self.describe()

    def __repr__(self) -> str:
        return self.describe()

    def points(self) -> list[tuple[float, float]]:
        return list(zip(self.stations, self.elevations))

    def add_point(self, station: float, elevation: float) -> "RoadwayProfile":
        """Append a station/elevation pair while keeping arrays aligned."""

        self.stations.append(station)
        self.elevations.append(elevation)
        logger.debug("Added roadway point (station %.3f, elevation %.3f)", station, elevation)
        return self

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

    def to_dict(self) -> dict[str, Any]:
        return {
            "width": self.width,
            "shape": self.shape,
            "surface": self.surface.name,
            "stations": list(self.stations),
            "elevations": list(self.elevations),
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "RoadwayProfile":
        return cls(
            width=float(data.get("width", 0.0)),
            shape=int(data.get("shape", 1)),
            surface=_coerce_enum(RoadwaySurface, data.get("surface"), default=RoadwaySurface.PAVED),
            stations=[float(value) for value in (data.get("stations") or [])],
            elevations=[float(value) for value in (data.get("elevations") or [])],
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
        shape = self.shape.name
        return (
            f"CulvertBarrel(name={self.name or '<unnamed>'}, shape={shape}, "
            f"span={self.span:.3f}, rise={self.rise:.3f}, count={self.number_of_barrels})"
        )

    def __str__(self) -> str:
        return self.describe()

    def __repr__(self) -> str:
        return self.describe()

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
            shape=_coerce_enum(CulvertShape, data.get("shape"), default=CulvertShape.CIRCLE),
            material=_coerce_enum(CulvertMaterial, data.get("material"), default=CulvertMaterial.CONCRETE),
            number_of_barrels=int(data.get("number_of_barrels", 1)),
            inlet_invert_station=float(data.get("inlet_invert_station", 0.0)),
            inlet_invert_elevation=float(data.get("inlet_invert_elevation", 0.0)),
            outlet_invert_station=float(data.get("outlet_invert_station", 0.0)),
            outlet_invert_elevation=float(data.get("outlet_invert_elevation", 0.0)),
            roadway_station=float(data.get("roadway_station", 0.0)),
            inlet_type=_coerce_enum(InletType, data.get("inlet_type"), default=InletType.STRAIGHT),
            inlet_edge_type=_coerce_enum(
                InletEdgeType, data.get("inlet_edge_type"), default=InletEdgeType.THIN_EDGE_PROJECTING
            ),
            inlet_edge_type71=_coerce_enum(InletEdgeType71, data.get("inlet_edge_type71"), default=InletEdgeType71.CODE_0),
            improved_inlet_edge_type=_coerce_enum(
                ImprovedInletEdgeType, data.get("improved_inlet_edge_type"), default=ImprovedInletEdgeType.NONE
            ),
            barrel_spacing=float(data["barrel_spacing"]) if data.get("barrel_spacing") is not None else None,
            notes=str(data.get("notes", "")),
            manning_n_top=float(data["manning_n_top"]) if data.get("manning_n_top") is not None else None,
            manning_n_bottom=float(data["manning_n_bottom"]) if data.get("manning_n_bottom") is not None else None,
        )


@dataclass(slots=True)
class CulvertCrossing(Validatable):
    """A culvert crossing which may contain multiple barrels."""

    name: str
    notes: str = ""
    flow: FlowDefinition = field(default_factory=FlowDefinition)
    tailwater: TailwaterDefinition = field(default_factory=TailwaterDefinition)
    roadway: RoadwayProfile = field(default_factory=RoadwayProfile)
    culverts: list[CulvertBarrel] = field(default_factory=_culvert_list)
    uuid: str | None = None

    def describe(self) -> str:
        barrel_count: int = len(self.culverts)
        crest = None
        if self.roadway.elevations:
            crest = self.roadway.crest_elevation()
        crest_str = f", crest={crest:.3f}" if crest is not None else ""
        return (
            f"CulvertCrossing(name={self.name}, barrels={barrel_count}, flow_method={self.flow.method.name}"
            f"{crest_str})"
        )

    def __str__(self) -> str:
        return self.describe()

    def __repr__(self) -> str:
        return self.describe()

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

    def add_barrel(self, barrel: CulvertBarrel | None = None, **kwargs: Any) -> CulvertBarrel:
        """Append a barrel definition, optionally constructing one from kwargs."""

        if barrel is not None and kwargs:
            raise ValueError("Provide either a barrel instance or keyword arguments, not both.")
        if barrel is None:
            options = dict(kwargs)
            options.setdefault("name", f"Barrel {len(self.culverts) + 1}")
            barrel = CulvertBarrel(**options)
        self.culverts.append(barrel)
        logger.debug("Added barrel %s to crossing %s", barrel.describe(), self.name)
        return barrel

    def hw_from_q(
        self,
        q: float,
        *,
        hy8: "Hy8Executable | Path | None" = None,
        project: "Hy8Project | None" = None,
        units: UnitSystem | None = None,
        exit_loss_option: int | None = None,
        workspace: Path | None = None,
        keep_files: bool = False,
    ) -> "HydraulicsResult":
        """Run HY-8 for a specific discharge and return the resulting headwater."""
        from .hydraulics import crossing_hw_from_q

        logger.info("Crossing %s running hw_from_q for flow %.4f", self.name, q)
        result = crossing_hw_from_q(
            crossing=self,
            q=q,
            hy8=hy8,
            project=project,
            units=units,
            exit_loss_option=exit_loss_option,
            workspace=workspace,
            keep_files=keep_files,
        )
        logger.debug(
            "Crossing %s hw_from_q computed headwater %.4f for flow %.4f",
            self.name,
            result.computed_headwater,
            result.computed_flow,
        )
        return result

    def q_from_hw(
        self,
        hw: float,
        *,
        q_hint: float | None = None,
        hy8: "Hy8Executable | Path | None" = None,
        project: "Hy8Project | None" = None,
        units: UnitSystem | None = None,
        exit_loss_option: int | None = None,
        workspace: Path | None = None,
        keep_files: bool = False,
    ) -> "HydraulicsResult":
        """Iteratively run HY-8 to find the discharge that produces the requested headwater."""
        from .hydraulics import crossing_q_from_hw

        logger.info("Crossing %s running q_from_hw for HW %.4f", self.name, hw)
        result = crossing_q_from_hw(
            crossing=self,
            hw=hw,
            q_hint=q_hint,
            hy8=hy8,
            project=project,
            units=units,
            exit_loss_option=exit_loss_option,
            workspace=workspace,
            keep_files=keep_files,
        )
        logger.debug(
            "Crossing %s q_from_hw computed flow %.4f for headwater %.4f",
            self.name,
            result.computed_flow,
            result.requested_headwater or hw,
        )
        return result

    def q_for_hwd(
        self,
        hw_d_ratio: float,
        *,
        q_hint: float | None = None,
        hy8: "Hy8Executable | Path | None" = None,
        project: "Hy8Project | None" = None,
        units: UnitSystem | None = None,
        exit_loss_option: int | None = None,
        workspace: Path | None = None,
        keep_files: bool = False,
    ) -> "HydraulicsResult":
        """Run HY-8 to find the discharge that satisfies a headwater-to-diameter ratio (optionally seeding with q_hint)."""
        from .hydraulics import crossing_q_for_hwd

        logger.info("Crossing %s running q_for_hwd for ratio %.4f", self.name, hw_d_ratio)
        result = crossing_q_for_hwd(
            crossing=self,
            hw_d_ratio=hw_d_ratio,
            q_hint=q_hint,
            hy8=hy8,
            project=project,
            units=units,
            exit_loss_option=exit_loss_option,
            workspace=workspace,
            keep_files=keep_files,
        )
        logger.debug(
            "Crossing %s q_for_hwd computed flow %.4f for HW/D %.4f",
            self.name,
            result.computed_flow,
            hw_d_ratio,
        )
        return result

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "notes": self.notes,
            "flow": self.flow.to_dict(),
            "tailwater": self.tailwater.to_dict(),
            "roadway": self.roadway.to_dict(),
            "culverts": [culvert.to_dict() for culvert in self.culverts],
            "uuid": self.uuid,
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "CulvertCrossing":
        flow_data = FlowDefinition.from_dict(data.get("flow", {}))
        tailwater_data = TailwaterDefinition.from_dict(data.get("tailwater", {}))
        roadway_data = RoadwayProfile.from_dict(data.get("roadway", {}))
        culvert_data = [CulvertBarrel.from_dict(raw) for raw in (data.get("culverts") or [])]
        return cls(
            name=data.get("name", "Crossing"),
            notes=str(data.get("notes", "")),
            flow=flow_data,
            tailwater=tailwater_data,
            roadway=roadway_data,
            culverts=culvert_data,
            uuid=data.get("uuid"),
        )


@dataclass(slots=True)
class Hy8Project(Validatable):
    """A full HY-8 project containing one or more crossings."""

    title: str = ""
    designer: str = ""
    notes: str = ""
    units: UnitSystem = UnitSystem.SI
    exit_loss_option: int = 0
    crossings: list[CulvertCrossing] = field(default_factory=_crossing_list)

    def describe(self) -> str:
        return f"Hy8Project(title={self.title or '<untitled>'}, crossings={len(self.crossings)})"

    def __str__(self) -> str:
        return self.describe()

    def __repr__(self) -> str:
        return self.describe()

    def validate(self, prefix: str = "") -> list[str]:
        errors: list[str] = []
        if not self.crossings:
            errors.append(f"{prefix}At least one crossing is required.")
        for index, crossing in enumerate(self.crossings, start=1):
            crossing_prefix: str = f"{prefix}Crossing #{index} ({crossing.name}): "
            errors.extend(crossing.validate(crossing_prefix))
        return errors

    @staticmethod
    def project_timestamp_hours() -> float:
        """HY-8 expects the project date as hours since epoch."""
        return datetime.now().timestamp() / 3600.0

    def add_crossing(self, crossing: CulvertCrossing | None = None) -> CulvertCrossing:
        if crossing is None:
            crossing = CulvertCrossing(name=f"Crossing {len(self.crossings) + 1}")
        self.crossings.append(crossing)
        logger.debug("Added crossing %s to project %s", crossing.name, self.title or "<untitled>")
        return crossing

    def flow_values(self) -> Sequence[list[float]]:
        return [crossing.flow.sequence() for crossing in self.crossings]

    def hw_from_q(
        self,
        q: float,
        *,
        hy8: "Hy8Executable | Path | None" = None,
        workspace: Path | None = None,
        keep_files: bool = False,
    ) -> "OrderedDict[str, HydraulicsResult]":
        """Return per-crossing headwater elevations by running HY-8 for the specified discharge."""
        from .hydraulics import project_hw_from_q

        logger.info("Project %s running hw_from_q for flow %.4f", self.title or "<untitled>", q)
        results = project_hw_from_q(
            project=self,
            q=q,
            hy8=hy8,
            workspace=workspace,
            keep_files=keep_files,
        )
        logger.debug("Project hw_from_q complete for flow %.4f across %s crossings", q, len(results))
        return results

    def q_from_hw(
        self,
        hw: float,
        *,
        q_hint: float | None = None,
        hy8: "Hy8Executable | Path | None" = None,
        workspace: Path | None = None,
        keep_files: bool = False,
    ) -> "OrderedDict[str, HydraulicsResult]":
        """Return per-crossing discharges for a requested headwater."""
        from .hydraulics import project_q_from_hw

        logger.info("Project %s running q_from_hw for HW %.4f", self.title or "<untitled>", hw)
        results = project_q_from_hw(
            project=self,
            hw=hw,
            q_hint=q_hint,
            hy8=hy8,
            workspace=workspace,
            keep_files=keep_files,
        )
        logger.debug("Project q_from_hw complete for HW %.4f across %s crossings", hw, len(results))
        return results

    def q_for_hwd(
        self,
        hw_d_ratio: float,
        *,
        q_hint: float | None = None,
        hy8: "Hy8Executable | Path | None" = None,
        workspace: Path | None = None,
        keep_files: bool = False,
    ) -> "OrderedDict[str, HydraulicsResult]":
        """Return per-crossing discharges for a headwater-to-diameter ratio (optionally seeded by q_hint)."""
        from .hydraulics import project_q_for_hwd

        logger.info(
            "Project %s running q_for_hwd for ratio %.4f", self.title or "<untitled>", hw_d_ratio
        )
        results = project_q_for_hwd(
            project=self,
            hw_d_ratio=hw_d_ratio,
            q_hint=q_hint,
            hy8=hy8,
            workspace=workspace,
            keep_files=keep_files,
        )
        logger.debug("Project q_for_hwd complete for ratio %.4f across %s crossings", hw_d_ratio, len(results))
        return results

    def to_dict(self) -> dict[str, Any]:
        return {
            "title": self.title,
            "designer": self.designer,
            "notes": self.notes,
            "units": self.units.name,
            "exit_loss_option": self.exit_loss_option,
            "crossings": [crossing.to_dict() for crossing in self.crossings],
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "Hy8Project":
        return cls(
            title=data.get("title", ""),
            designer=data.get("designer", ""),
            notes=data.get("notes", ""),
            units=_coerce_enum(UnitSystem, data.get("units"), default=UnitSystem.SI),
            exit_loss_option=int(data.get("exit_loss_option", 0)),
            crossings=[CulvertCrossing.from_dict(raw) for raw in (data.get("crossings") or [])],
        )
