"""Single culvert barrel definition for HY-8."""

from __future__ import annotations

import warnings
from _collections_abc import Mapping
from dataclasses import dataclass, field
from typing import Any

from ..hydraulic_defaults import default_manning_values
from ..inlet_configurations import (
    CircularCorrugatedSteelInlet,
    Hy8V8InletSpec,
    SupportedInletConfiguration,
    default_inlet_configuration,
    parse_inlet_configuration,
    resolve_v8_inlet_configuration,
    resolve_v8_inlet_spec,
)
from ..type_helpers import (
    CulvertMaterial,
    CulvertShape,
    ImprovedInletEdgeType,
    InletEdgeType,
    InletEdgeType71,
    InletType,
    coerce_enum,
)
from .base import Validatable


class LegacyInletConfigurationWarning(UserWarning):
    """Use of the deprecated context-free inlet edge API."""


@dataclass(slots=True)
class CulvertBarrel(Validatable):
    """Single culvert barrel definition."""

    name: str = ""
    span: float = 0.0
    rise: float = 0.0
    shape: CulvertShape = CulvertShape.CIRCLE
    material: CulvertMaterial = CulvertMaterial.CORRUGATED_STEEL
    number_of_barrels: int = 1
    inlet_invert_station: float = 0.0
    inlet_invert_elevation: float = 0.0
    outlet_invert_station: float = 0.0
    outlet_invert_elevation: float = 0.0
    roadway_station: float = 0.0
    inlet_type: InletType = InletType.STRAIGHT
    inlet_configuration: SupportedInletConfiguration = CircularCorrugatedSteelInlet.THIN_EDGE_PROJECTING
    inlet_edge_type: InletEdgeType | None = field(default=None, repr=False)
    inlet_edge_type71: InletEdgeType71 | None = field(default=None, repr=False)
    improved_inlet_edge_type: ImprovedInletEdgeType = ImprovedInletEdgeType.NONE
    barrel_spacing: float | None = None
    notes: str = ""
    manning_n_top: float | None = None
    manning_n_bottom: float | None = None
    _legacy_warning_emitted: bool = field(default=False, init=False, repr=False, compare=False)

    def __post_init__(self) -> None:
        if self.inlet_edge_type is not None or self.inlet_edge_type71 is not None:
            self._warn_legacy_inlet_configuration()
            self.inlet_configuration = self._configuration_from_legacy_fields()

    def _warn_legacy_inlet_configuration(self) -> None:
        if self._legacy_warning_emitted:
            return
        warnings.warn(
            message="InletEdgeType and InletEdgeType71 are deprecated context-free inputs. "
            "Use a shape/material-specific HY-8 v8 inlet configuration enum.",
            category=LegacyInletConfigurationWarning,
            stacklevel=3,
        )
        self._legacy_warning_emitted = True

    def _configuration_from_legacy_fields(self) -> SupportedInletConfiguration:
        """Interpret a legacy numeric value as the current contextual v8 list index."""

        raw: InletEdgeType71 | InletEdgeType | None = self.inlet_edge_type71 if self.inlet_edge_type71 is not None else self.inlet_edge_type
        if raw is None:  # pragma: no cover - guarded by caller
            return self.inlet_configuration
        return resolve_v8_inlet_configuration(
            shape=self.shape,
            material=self.material,
            inlet_type=self.inlet_type,
            v8_index=int(raw),
        )

    def resolved_inlet_configuration(self) -> SupportedInletConfiguration:
        """Return the semantic v8 configuration, translating deprecated fields if needed."""

        if self.inlet_edge_type is not None or self.inlet_edge_type71 is not None:
            self._warn_legacy_inlet_configuration()
            return self._configuration_from_legacy_fields()
        return self.inlet_configuration

    def describe(self) -> str:
        """Return a short, human-readable description of the culvert barrel."""
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
        """Return a dictionary representation of the culvert barrel."""
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
            "inlet_configuration": self.resolved_inlet_configuration().value,
            "improved_inlet_edge_type": self.improved_inlet_edge_type.name,
            "barrel_spacing": self.barrel_spacing,
            "notes": self.notes,
            "manning_n_top": self.manning_n_top,
            "manning_n_bottom": self.manning_n_bottom,
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> CulvertBarrel:
        """Create a CulvertBarrel from a dictionary."""
        legacy_keys: set[str] = {"inlet_edge_type", "inlet_edge_type71"} & data.keys()
        if legacy_keys and "inlet_configuration" in data:
            warnings.warn(
                message="inlet_edge_type and inlet_edge_type71 are deprecated. Use inlet_configuration.",
                category=LegacyInletConfigurationWarning,
                stacklevel=2,
            )
            raise ValueError("Do not combine inlet_configuration with deprecated inlet edge fields.")
        return cls(
            name=data.get("name", ""),
            span=float(data.get("span", 0.0)),
            rise=float(data.get("rise", 0.0)),
            shape=coerce_enum(CulvertShape, data.get("shape"), default=CulvertShape.CIRCLE),
            material=coerce_enum(CulvertMaterial, data.get("material"), default=CulvertMaterial.CORRUGATED_STEEL),
            number_of_barrels=int(data.get("number_of_barrels", 1)),
            inlet_invert_station=float(data.get("inlet_invert_station", 0.0)),
            inlet_invert_elevation=float(data.get("inlet_invert_elevation", 0.0)),
            outlet_invert_station=float(data.get("outlet_invert_station", 0.0)),
            outlet_invert_elevation=float(data.get("outlet_invert_elevation", 0.0)),
            roadway_station=float(data.get("roadway_station", 0.0)),
            inlet_type=coerce_enum(InletType, data.get("inlet_type"), default=InletType.STRAIGHT),
            inlet_configuration=cls._configuration_from_mapping(data),
            inlet_edge_type=(
                coerce_enum(InletEdgeType, data.get("inlet_edge_type"), default=InletEdgeType.THIN_EDGE_PROJECTING)
                if "inlet_edge_type" in data
                else None
            ),
            inlet_edge_type71=(
                coerce_enum(InletEdgeType71, data.get("inlet_edge_type71"), default=InletEdgeType71.CODE_0)
                if "inlet_edge_type71" in data
                else None
            ),
            improved_inlet_edge_type=coerce_enum(
                ImprovedInletEdgeType, data.get("improved_inlet_edge_type"), default=ImprovedInletEdgeType.NONE
            ),
            barrel_spacing=float(data["barrel_spacing"]) if data.get("barrel_spacing") is not None else None,
            notes=str(data.get("notes", "")),
            manning_n_top=float(data["manning_n_top"]) if data.get("manning_n_top") is not None else None,
            manning_n_bottom=float(data["manning_n_bottom"]) if data.get("manning_n_bottom") is not None else None,
        )

    @staticmethod
    def _configuration_from_mapping(data: Mapping[str, Any]) -> SupportedInletConfiguration:
        shape: CulvertShape = coerce_enum(CulvertShape, data.get("shape"), default=CulvertShape.CIRCLE)
        material: CulvertMaterial = coerce_enum(CulvertMaterial, data.get("material"), default=CulvertMaterial.CORRUGATED_STEEL)
        raw = data.get("inlet_configuration")
        if raw is None:
            return default_inlet_configuration(shape=shape, material=material)
        return parse_inlet_configuration(raw, shape=shape, material=material)

    def validate(self, prefix: str = "") -> list[str]:
        """Return a list of validation errors, or an empty list if the model is valid."""
        errors: list[str] = []
        if self.span <= 0:
            errors.append(f"{prefix}Culvert span must be greater than zero.")
        if self.rise <= 0:
            errors.append(f"{prefix}Culvert rise must be greater than zero.")
        if self.shape is CulvertShape.BOX and self.rise <= 0:
            errors.append(f"{prefix}Box culverts must include a rise.")
        if self.number_of_barrels <= 0:
            errors.append(f"{prefix}Number of barrels must be >= 1.")
        try:
            configuration = self.resolved_inlet_configuration()
            spec: Hy8V8InletSpec = resolve_v8_inlet_spec(configuration)
            if (spec.shape, spec.material, spec.inlet_type) != (self.shape, self.material, self.inlet_type):
                errors.append(
                    f"{prefix}Inlet configuration '{configuration.value}' is not valid for "
                    f"{self.shape.name}/{self.material.name}/{self.inlet_type.name}."
                )
        except ValueError as exc:
            errors.append(f"{prefix}{exc}")
        return errors

    def manning_values(self) -> tuple[float, float]:
        """Return HY-8 v8's default top and bottom Manning's n values.

        The defaults are a checked-in snapshot of the ``Mannings`` datasets in
        HY-8 8.0.1.2 ``ShapeDB.dat``. HY-8 provides one default for each
        currently supported shape/material context, while ``BARRELDATA`` needs
        both top and bottom values, so that value is returned for both sides.

        Raises:
            ValueError: If the shape/material context has no researched HY-8
                v8 default. This intentional failure prevents future enum
                additions from silently receiving an unrelated roughness.
        """

        return default_manning_values(shape=self.shape, material=self.material)

    def resolved_manning_values(self) -> tuple[float, float]:
        """Return explicit Manning values with per-side HY-8 defaults.

        Supplying both values bypasses the default registry entirely. Supplying
        only one preserves that override and uses the researched HY-8 default
        for the other side.
        """

        if self.manning_n_top is not None and self.manning_n_bottom is not None:
            return self.manning_n_top, self.manning_n_bottom
        default_top, default_bottom = self.manning_values()
        top: float = self.manning_n_top if self.manning_n_top is not None else default_top
        bottom: float = self.manning_n_bottom if self.manning_n_bottom is not None else default_bottom
        return top, bottom
