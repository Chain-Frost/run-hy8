"""HY-8 version 8 inlet-configuration identifiers and file-code mappings.

Research basis
--------------
The mappings in this module are a checked-in snapshot of HY-8 8.0.1.2, not a
translation of another application's culvert types. On 2026-08-13 the inlet
names and their order were inspected in the installed ``ShapeDB.dat`` HDF5
database beneath paths such as::

    Concrete Box/Concrete/Entrance Types/Straight/Inlet Names
    Circular/Concrete/Entrance Types/Straight/Inlet Names

That order is the contextual index stored in the unfortunately named
``INLETEDGETYPE71`` project card. Executed probes with HY-8 8.0.1.2 established
that removing this card causes HY-8 to reinterpret inlet selections from the
older ``INLETEDGETYPE`` card. Conversely, retaining the contextual card while
writing zero to ``INLETEDGETYPE`` produced the same ``.rst`` results as the
HY-8-saved reference project. HY-8 still needs the older card to be present in
the file grammar, so the writer emits a neutral value without exposing its
obsolete code system in the public model.

The installed HY-8 User Manual corroborates the available configurations in
section 4.4 (Inlet Configurations) and the concrete-box equation/configuration
families in section 11.3 (Polynomial Coefficients - Box). See
``docs/hy8_v8_inlet_configurations.md`` for the complete observations,
experiment boundaries, and extension procedure.

Do not replace these semantic enums with a single integer enum: the same list
index has different hydraulic meaning for different shape/material contexts.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import TypeAlias, cast

from .type_helpers import CulvertMaterial, CulvertShape, InletType


class CircularConcreteInlet(StrEnum):
    """Straight inlet configurations for circular concrete pipe."""

    SQUARE_EDGE_WITH_HEADWALL = "square-edge-with-headwall"
    GROOVED_END_PROJECTING = "grooved-end-projecting"
    GROOVED_END_IN_HEADWALL = "grooved-end-in-headwall"
    BEVELED_EDGE_1_TO_1 = "beveled-edge-1-to-1"
    BEVELED_EDGE_1_5_TO_1 = "beveled-edge-1-5-to-1"
    MITERED_TO_CONFORM_TO_SLOPE = "mitered-to-conform-to-slope"


class CircularCorrugatedSteelInlet(StrEnum):
    """Straight inlet configurations for circular corrugated-steel pipe."""

    THIN_EDGE_PROJECTING = "thin-edge-projecting"
    MITERED_TO_CONFORM_TO_SLOPE = "mitered-to-conform-to-slope"
    SQUARE_EDGE_WITH_HEADWALL = "square-edge-with-headwall"
    BEVELED_EDGE_1_TO_1 = "beveled-edge-1-to-1"
    BEVELED_EDGE_1_5_TO_1 = "beveled-edge-1-5-to-1"


class CircularHdpeInlet(StrEnum):
    """Straight inlet configurations for circular smooth-HDPE pipe."""

    SQUARE_EDGE_WITH_HEADWALL = "square-edge-with-headwall"
    BEVELED_EDGE_1_TO_1 = "beveled-edge-1-to-1"
    BEVELED_EDGE_1_5_TO_1 = "beveled-edge-1-5-to-1"
    THIN_EDGE_PROJECTING = "thin-edge-projecting"
    MITERED_TO_CONFORM_TO_SLOPE = "mitered-to-conform-to-slope"


class ConcreteBoxInlet(StrEnum):
    """Straight inlet configurations for conventional concrete boxes."""

    SQUARE_EDGE_90_DEG_HEADWALL = "square-edge-90-deg-headwall"
    BEVEL_1_5_TO_1_90_DEG_HEADWALL = "bevel-1-5-to-1-90-deg-headwall"
    BEVEL_1_TO_1_HEADWALL = "bevel-1-to-1-headwall"
    SQUARE_EDGE_30_TO_75_DEG_WINGWALL = "square-edge-30-to-75-deg-wingwall"
    SQUARE_EDGE_90_OR_15_DEG_WINGWALL = "square-edge-90-or-15-deg-wingwall"
    SQUARE_EDGE_0_DEG_WINGWALL = "square-edge-0-deg-wingwall"
    BEVEL_1_5_TO_1_18_TO_34_DEG_WINGWALL = "bevel-1-5-to-1-18-to-34-deg-wingwall"
    BEVEL_1_TO_1_45_DEG_WINGWALL = "bevel-1-to-1-45-deg-wingwall"


SupportedInletConfiguration: TypeAlias = (
    CircularConcreteInlet | CircularCorrugatedSteelInlet | CircularHdpeInlet | ConcreteBoxInlet
)


@dataclass(frozen=True, slots=True)
class Hy8V8InletSpec:
    """A semantic configuration's context and v8 ``INLETEDGETYPE71`` index."""

    shape: CulvertShape
    material: CulvertMaterial
    inlet_type: InletType
    v8_index: int
    label: str


def _spec(
    shape: CulvertShape,
    material: CulvertMaterial,
    index: int,
    label: str,
) -> Hy8V8InletSpec:
    return Hy8V8InletSpec(
        shape=shape,
        material=material,
        inlet_type=InletType.STRAIGHT,
        v8_index=index,
        label=label,
    )


InletConfigurationKey: TypeAlias = tuple[type[StrEnum], str]


def _inlet_key(configuration: SupportedInletConfiguration) -> InletConfigurationKey:
    """Qualify a StrEnum value because equal strings from different enums compare equal."""

    return type(configuration), configuration.value


# Snapshot from HY-8 8.0.1.2 ShapeDB.dat. The public enum values are stable
# semantic identifiers; only this registry knows the contextual file indices.
HY8_V8_INLET_SPECS: dict[InletConfigurationKey, Hy8V8InletSpec] = {
    _inlet_key(CircularConcreteInlet.SQUARE_EDGE_WITH_HEADWALL): _spec(
        CulvertShape.CIRCLE, CulvertMaterial.CONCRETE, 0, "Square Edge with Headwall"
    ),
    _inlet_key(CircularConcreteInlet.GROOVED_END_PROJECTING): _spec(
        CulvertShape.CIRCLE, CulvertMaterial.CONCRETE, 1, "Grooved End Projecting"
    ),
    _inlet_key(CircularConcreteInlet.GROOVED_END_IN_HEADWALL): _spec(
        CulvertShape.CIRCLE, CulvertMaterial.CONCRETE, 2, "Grooved End in Headwall"
    ),
    _inlet_key(CircularConcreteInlet.BEVELED_EDGE_1_TO_1): _spec(
        CulvertShape.CIRCLE, CulvertMaterial.CONCRETE, 3, "Beveled Edge (1:1)"
    ),
    _inlet_key(CircularConcreteInlet.BEVELED_EDGE_1_5_TO_1): _spec(
        CulvertShape.CIRCLE, CulvertMaterial.CONCRETE, 4, "Beveled Edge (1.5:1)"
    ),
    _inlet_key(CircularConcreteInlet.MITERED_TO_CONFORM_TO_SLOPE): _spec(
        CulvertShape.CIRCLE, CulvertMaterial.CONCRETE, 5, "Mitered to Conform to Slope"
    ),
    _inlet_key(CircularCorrugatedSteelInlet.THIN_EDGE_PROJECTING): _spec(
        CulvertShape.CIRCLE, CulvertMaterial.CORRUGATED_STEEL, 0, "Thin Edge Projecting"
    ),
    _inlet_key(CircularCorrugatedSteelInlet.MITERED_TO_CONFORM_TO_SLOPE): _spec(
        CulvertShape.CIRCLE, CulvertMaterial.CORRUGATED_STEEL, 1, "Mitered to Conform to Slope"
    ),
    _inlet_key(CircularCorrugatedSteelInlet.SQUARE_EDGE_WITH_HEADWALL): _spec(
        CulvertShape.CIRCLE, CulvertMaterial.CORRUGATED_STEEL, 2, "Square Edge with Headwall"
    ),
    _inlet_key(CircularCorrugatedSteelInlet.BEVELED_EDGE_1_TO_1): _spec(
        CulvertShape.CIRCLE, CulvertMaterial.CORRUGATED_STEEL, 3, "Beveled Edge (1:1)"
    ),
    _inlet_key(CircularCorrugatedSteelInlet.BEVELED_EDGE_1_5_TO_1): _spec(
        CulvertShape.CIRCLE, CulvertMaterial.CORRUGATED_STEEL, 4, "Beveled Edge (1.5:1)"
    ),
    _inlet_key(CircularHdpeInlet.SQUARE_EDGE_WITH_HEADWALL): _spec(
        CulvertShape.CIRCLE, CulvertMaterial.HDPE, 0, "Square Edge with Headwall"
    ),
    _inlet_key(CircularHdpeInlet.BEVELED_EDGE_1_TO_1): _spec(
        CulvertShape.CIRCLE, CulvertMaterial.HDPE, 1, "Beveled Edge (1:1)"
    ),
    _inlet_key(CircularHdpeInlet.BEVELED_EDGE_1_5_TO_1): _spec(
        CulvertShape.CIRCLE, CulvertMaterial.HDPE, 2, "Beveled Edge (1.5:1)"
    ),
    _inlet_key(CircularHdpeInlet.THIN_EDGE_PROJECTING): _spec(
        CulvertShape.CIRCLE, CulvertMaterial.HDPE, 3, "Thin Edge Projecting"
    ),
    _inlet_key(CircularHdpeInlet.MITERED_TO_CONFORM_TO_SLOPE): _spec(
        CulvertShape.CIRCLE, CulvertMaterial.HDPE, 4, "Mitered to Conform to Slope"
    ),
    _inlet_key(ConcreteBoxInlet.SQUARE_EDGE_90_DEG_HEADWALL): _spec(
        CulvertShape.BOX, CulvertMaterial.CONCRETE, 0, "Square Edge (90 deg) Headwall"
    ),
    _inlet_key(ConcreteBoxInlet.BEVEL_1_5_TO_1_90_DEG_HEADWALL): _spec(
        CulvertShape.BOX, CulvertMaterial.CONCRETE, 1, "1.5:1 Bevel (90 deg) Headwall"
    ),
    _inlet_key(ConcreteBoxInlet.BEVEL_1_TO_1_HEADWALL): _spec(
        CulvertShape.BOX, CulvertMaterial.CONCRETE, 2, "1:1 Bevel Headwall"
    ),
    _inlet_key(ConcreteBoxInlet.SQUARE_EDGE_30_TO_75_DEG_WINGWALL): _spec(
        CulvertShape.BOX, CulvertMaterial.CONCRETE, 3, "Square Edge (30-75 deg flare) Wingwall"
    ),
    _inlet_key(ConcreteBoxInlet.SQUARE_EDGE_90_OR_15_DEG_WINGWALL): _spec(
        CulvertShape.BOX, CulvertMaterial.CONCRETE, 4, "Square Edge (90 & 15 deg flare) Wingwall"
    ),
    _inlet_key(ConcreteBoxInlet.SQUARE_EDGE_0_DEG_WINGWALL): _spec(
        CulvertShape.BOX, CulvertMaterial.CONCRETE, 5, "Square Edge (0 deg flare) Wingwall"
    ),
    _inlet_key(ConcreteBoxInlet.BEVEL_1_5_TO_1_18_TO_34_DEG_WINGWALL): _spec(
        CulvertShape.BOX, CulvertMaterial.CONCRETE, 6, "1.5:1 Bevel (18-34 deg flare) Wingwall"
    ),
    _inlet_key(ConcreteBoxInlet.BEVEL_1_TO_1_45_DEG_WINGWALL): _spec(
        CulvertShape.BOX, CulvertMaterial.CONCRETE, 7, "1:1 Bevel (45 deg flare) Wingwall"
    ),
}

_ALL_INLET_CONFIGURATIONS: tuple[SupportedInletConfiguration, ...] = (
    *tuple(CircularConcreteInlet),
    *tuple(CircularCorrugatedSteelInlet),
    *tuple(CircularHdpeInlet),
    *tuple(ConcreteBoxInlet),
)

HY8_V8_INLET_BY_CONTEXT: dict[tuple[CulvertShape, CulvertMaterial, InletType, int], SupportedInletConfiguration] = {
    (spec.shape, spec.material, spec.inlet_type, spec.v8_index): configuration
    for configuration in _ALL_INLET_CONFIGURATIONS
    for spec in (HY8_V8_INLET_SPECS[_inlet_key(configuration)],)
}


def default_inlet_configuration(shape: CulvertShape, material: CulvertMaterial) -> SupportedInletConfiguration:
    """Return HY-8 v8's first straight-inlet option for a supported context."""

    return resolve_v8_inlet_configuration(
        shape=shape,
        material=material,
        inlet_type=InletType.STRAIGHT,
        v8_index=0,
    )


def resolve_v8_inlet_spec(
    configuration: SupportedInletConfiguration,
) -> Hy8V8InletSpec:
    """Return the version 8 file specification for a semantic configuration."""

    try:
        return HY8_V8_INLET_SPECS[_inlet_key(configuration)]
    except KeyError as exc:  # pragma: no cover - type checkers prevent normal callers
        raise ValueError(f"Unsupported HY-8 v8 inlet configuration: {configuration!r}") from exc


def resolve_v8_inlet_configuration(
    *,
    shape: CulvertShape,
    material: CulvertMaterial,
    inlet_type: InletType,
    v8_index: int,
) -> SupportedInletConfiguration:
    """Resolve a contextual HY-8 v8 inlet-list index into its semantic identifier."""

    key: tuple[CulvertShape, CulvertMaterial, InletType, int] = (shape, material, inlet_type, v8_index)
    try:
        return HY8_V8_INLET_BY_CONTEXT[key]
    except KeyError as exc:
        raise ValueError(
            "Unsupported HY-8 v8 inlet configuration: "
            f"shape={shape.name}, material={material.name}, "
            f"inlet_type={inlet_type.name}, index={v8_index}."
        ) from exc


def parse_inlet_configuration(
    value: object,
    *,
    shape: CulvertShape,
    material: CulvertMaterial,
) -> SupportedInletConfiguration:
    """Parse a public configuration slug in the supplied shape/material context."""

    candidates: list[CircularConcreteInlet | CircularCorrugatedSteelInlet | CircularHdpeInlet | ConcreteBoxInlet] = [
        configuration
        for configuration in _ALL_INLET_CONFIGURATIONS
        for spec in (HY8_V8_INLET_SPECS[_inlet_key(configuration)],)
        if spec.shape is shape and spec.material is material
    ]
    if isinstance(value, StrEnum):
        typed_value: CircularConcreteInlet | CircularCorrugatedSteelInlet | CircularHdpeInlet | ConcreteBoxInlet = cast(SupportedInletConfiguration, value)
        for candidate in candidates:
            if _inlet_key(configuration=typed_value) == _inlet_key(configuration=candidate):
                return candidate
    normalized: str = str(value).strip().lower().replace("_", "-").replace(" ", "-")
    for configuration in candidates:
        if configuration.value == normalized or configuration.name.lower().replace("_", "-") == normalized:
            return configuration
    available:str = ", ".join(configuration.value for configuration in candidates)
    raise ValueError(
        f"Unsupported inlet configuration '{value}' for {shape.name}/{material.name}. "
        f"Available configurations: {available or '<none>'}."
    )


__all__: list[str] = [
    "CircularConcreteInlet",
    "CircularCorrugatedSteelInlet",
    "CircularHdpeInlet",
    "ConcreteBoxInlet",
    "HY8_V8_INLET_SPECS",
    "Hy8V8InletSpec",
    "SupportedInletConfiguration",
    "default_inlet_configuration",
    "parse_inlet_configuration",
    "resolve_v8_inlet_configuration",
    "resolve_v8_inlet_spec",
]
