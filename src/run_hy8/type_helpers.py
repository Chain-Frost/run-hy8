"""Enums and enum helpers shared between HY-8 domain models."""

from __future__ import annotations

from enum import Enum, IntEnum
from typing import Any, TypeVar

TEnum = TypeVar("TEnum", bound=Enum)


def coerce_enum(enum_cls: type[TEnum], value: Any, *, default: TEnum) -> TEnum:
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

    _label_: str

    def __new__(cls, value: int, label: str) -> "_DescribedIntEnum":
        obj: _DescribedIntEnum = int.__new__(cls, value)
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