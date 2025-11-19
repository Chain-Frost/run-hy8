"""Roadway geometry metadata."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any
from _collections_abc import Mapping

from loguru import logger

from .base import Validatable, float_list, normalize_sequence
from ..type_helpers import RoadwaySurface, coerce_enum


@dataclass(slots=True)
class RoadwayProfile(Validatable):
    """Roadway geometry and metadata."""

    width: float = 0.0
    shape: int = 1
    surface: RoadwaySurface = RoadwaySurface.PAVED
    stations: list[float] = field(default_factory=float_list)
    elevations: list[float] = field(default_factory=float_list)

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
        logger.debug(
            "Added roadway point (station {station:.3f}, elevation {elevation:.3f})",
            station=station,
            elevation=elevation,
        )
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
            surface=coerce_enum(RoadwaySurface, data.get("surface"), default=RoadwaySurface.PAVED),
            stations=[float(value) for value in normalize_sequence(data.get("stations"))],
            elevations=[float(value) for value in normalize_sequence(data.get("elevations"))],
        )
