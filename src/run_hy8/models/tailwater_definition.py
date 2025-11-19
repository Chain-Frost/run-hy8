"""Tailwater boundary condition models."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any
from _collections_abc import Mapping, Sequence as ABCSequence

from loguru import logger

from .base import Validatable, normalize_sequence, rating_curve_list
from ..type_helpers import TailwaterType, coerce_enum, TailwaterRatingPoint


@dataclass(slots=True)
class TailwaterDefinition(Validatable):
    """Hydraulic tailwater definitions understood by run-hy8."""

    tw_type: TailwaterType = TailwaterType.CONSTANT
    bottom_width: float = 0.0
    sideslope: float = 1.0
    channel_slope: float = 0.0
    manning_n: float = 0.0
    constant_elevation: float = 0.0
    invert_elevation: float = 0.0
    rating_curve_entries: int = 6
    rating_curve: list[TailwaterRatingPoint] = field(default_factory=rating_curve_list)

    def describe(self) -> str:
        if self.tw_type is TailwaterType.CONSTANT:
            return (
                f"Tailwater(type=CONSTANT, elevation={self.constant_elevation:.3f}, "
                f"invert={self.invert_elevation:.3f})"
            )
        return f"Tailwater(type={self.tw_type.name}, entries={len(self.rating_curve)})"

    def __str__(self) -> str:
        return self.describe()

    def __repr__(self) -> str:
        return self.describe()

    def set_constant(self, *, elevation: float, invert: float | None = None) -> "TailwaterDefinition":
        """Fluent helper to configure a constant tailwater elevation."""

        self.tw_type = TailwaterType.CONSTANT
        self.constant_elevation = elevation
        if invert is not None:
            self.invert_elevation = invert
        logger.debug(
            "Configured constant tailwater elevation {elevation:.4f} (invert {invert:.4f})",
            elevation=self.constant_elevation,
            invert=self.invert_elevation,
        )
        return self

    def to_dict(self) -> dict[str, Any]:
        return {
            "type": self.tw_type.name,
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
        rating_curve_data: list[tuple[float, float, float]] = []
        for entry in normalize_sequence(data.get("rating_curve")):
            if not (isinstance(entry, ABCSequence) and not isinstance(entry, (str, bytes))):
                continue
            entry_tuple = tuple(entry)
            if len(entry_tuple) < 3:
                continue
            a, b, c = entry_tuple[:3]
            rating_curve_data.append((float(a), float(b), float(c)))
        return cls(
            tw_type=coerce_enum(TailwaterType, data.get("type"), default=TailwaterType.CONSTANT),
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
        if self.tw_type is not TailwaterType.CONSTANT:
            errors.append(
                f"{prefix}Tailwater type '{self.tw_type.name}' is not supported by run-hy8. "
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
