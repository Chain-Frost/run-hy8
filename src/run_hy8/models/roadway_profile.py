"""Roadway geometry metadata."""

from __future__ import annotations

import math
from _collections_abc import Mapping
from dataclasses import dataclass, field
from itertools import pairwise
from typing import Any

from loguru import logger

from ..type_helpers import RoadwayShape, RoadwaySurface, coerce_enum
from .base import Validatable, float_list, normalize_sequence


@dataclass(slots=True)
class RoadwayProfile(Validatable):
    """Roadway geometry and metadata."""

    width: float = 0.0
    shape: RoadwayShape = RoadwayShape.CONSTANT
    surface: RoadwaySurface = RoadwaySurface.PAVED
    stations: list[float] = field(default_factory=float_list)
    elevations: list[float] = field(default_factory=float_list)
    discharge_coefficient: float | None = None

    def __post_init__(self) -> None:
        """Accept existing numeric flags while exposing a typed shape."""
        self.shape = RoadwayShape(self.shape)

    def describe(self) -> str:
        """Return a short, human-readable description of the roadway profile."""
        count: int = min(len(self.stations), len(self.elevations))
        return f"Roadway(width={self.width:.3f}, points={count})"

    def __str__(self) -> str:
        return self.describe()

    def __repr__(self) -> str:
        return self.describe()

    def points(self) -> list[tuple[float, float]]:
        """Return a list of (station, elevation) tuples."""
        return list(zip(self.stations, self.elevations, strict=False))

    def add_point(self, station: float, elevation: float) -> RoadwayProfile:
        """Append a station/elevation pair while keeping arrays aligned."""
        self.stations.append(station)
        self.elevations.append(elevation)
        logger.debug(
            "Added roadway point (station {station:.3f}, elevation {elevation:.3f})",
            station=station,
            elevation=elevation,
        )
        return self

    def validate(self, prefix: str = "") -> list[str]:
        """Return a list of validation errors, or an empty list if the model is valid."""
        errors: list[str] = []
        if not math.isfinite(self.width) or self.width <= 0:
            errors.append(f"{prefix}Roadway width must be finite and > 0.")
        if len(self.stations) != len(self.elevations):
            errors.append(f"{prefix}Stations and elevations counts must match.")
        if self.shape == RoadwayShape.CONSTANT:
            if len(self.stations) != 2:
                errors.append(f"{prefix}Constant roadway requires exactly two endpoints.")
            if len(set(self.elevations)) != 1:
                errors.append(f"{prefix}Constant roadway endpoints must have equal elevations.")
        elif self.shape == RoadwayShape.IRREGULAR:
            if not 3 <= len(self.stations) <= 5000:
                errors.append(f"{prefix}Irregular roadway requires 3-5000 points (HY-8 7.70+).")
        else:
            errors.append(f"{prefix}Unsupported roadway shape {self.shape}.")
        if not all(math.isfinite(value) for value in (*self.stations, *self.elevations)):
            errors.append(f"{prefix}Roadway coordinates must be finite.")
        if any(right <= left for left, right in pairwise(self.stations)):
            errors.append(f"{prefix}Roadway stations must be strictly increasing with positive extent.")
        coefficient: float | None = self.discharge_coefficient
        if self.surface == RoadwaySurface.USER_DEFINED and coefficient is None:
            errors.append(f"{prefix}User-defined roadway requires discharge_coefficient in SI units.")
        if coefficient is not None:
            # Manual section 3.3.1: 2.5-3.095 in English units, including SI display projects.
            lower: float = 2.5 * math.sqrt(0.3048)
            upper: float = 3.095 * math.sqrt(0.3048)
            # Automatic modes retain inactive saved WEIRCOEFF=0 for faithful read/write.
            if not math.isfinite(coefficient) or (
                self.surface == RoadwaySurface.USER_DEFINED and not lower <= coefficient <= upper
            ):
                errors.append(f"{prefix}Roadway discharge_coefficient must be finite and in [{lower}, {upper}] SI.")
        return errors

    def crest_elevation(self) -> float:
        """Return the lowest elevation in the roadway profile."""
        if not self.elevations:
            msg = "Roadway elevations are required before computing crest elevation."
            raise ValueError(msg)
        return min(self.elevations)

    def to_dict(self) -> dict[str, Any]:
        """Return a dictionary representation of the roadway profile."""
        return {
            "width": self.width,
            "shape": int(self.shape),
            "surface": self.surface.name,
            "stations": list(self.stations),
            "elevations": list(self.elevations),
            "discharge_coefficient": self.discharge_coefficient,
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> RoadwayProfile:
        """Create a RoadwayProfile from a dictionary."""
        return cls(
            width=float(data.get("width", 0.0)),
            shape=coerce_enum(RoadwayShape, data.get("shape"), default=RoadwayShape.CONSTANT),
            surface=coerce_enum(RoadwaySurface, data.get("surface"), default=RoadwaySurface.PAVED),
            stations=[float(value) for value in normalize_sequence(data.get("stations"))],
            elevations=[float(value) for value in normalize_sequence(data.get("elevations"))],
            discharge_coefficient=(
                float(data["discharge_coefficient"]) if data.get("discharge_coefficient") is not None else None
            ),
        )
