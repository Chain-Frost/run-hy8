"""Observed hydraulic defaults from the HY-8 8.0.1.2 shape database.

``HY8_V8_OBSERVED_MANNING_N`` records every shape/material default found in
the installed ``ShapeDB.dat`` on 2026-08-13, including combinations that
``run-hy8`` does not yet model. Keeping the complete observation here makes
future shape/material work discoverable without pretending those combinations
are already supported by the public barrel model.

Where ShapeDB provides only ``Mannings``, HY-8 uses the same value for both
parts of the ``BARRELDATA`` pair. Where it also provides ``Mannings Bottom``,
the two observed values are retained separately.
"""

from __future__ import annotations

from .type_helpers import CulvertMaterial, CulvertShape

type Hy8ShapeMaterialName = tuple[str, str]
type ManningPair = tuple[float, float]


HY8_V8_OBSERVED_MANNING_N: dict[Hy8ShapeMaterialName, ManningPair] = {
    ("Arch, Open Bottom", "Corrugated Aluminum"): (0.035, 0.035),
    ("Arch, Open Bottom", "Corrugated Steel"): (0.035, 0.035),
    ("Circular", "Concrete"): (0.012, 0.012),
    ("Circular", "Corrugated Aluminum"): (0.031, 0.031),
    ("Circular", "Corrugated PE"): (0.024, 0.024),
    ("Circular", "Corrugated Steel"): (0.024, 0.024),
    ("Circular", "PVC"): (0.011, 0.011),
    ("Circular", "Smooth HDPE"): (0.012, 0.012),
    ("Concrete Box", "Concrete"): (0.012, 0.012),
    ("Concrete Open-Bottom Arch", "Concrete"): (0.012, 0.035),
    ("Elliptical", "Concrete"): (0.012, 0.012),
    ("Elliptical", "Steel or Aluminum"): (0.034, 0.034),
    ("High-Profile Arch", "Corrugated Aluminum"): (0.035, 0.035),
    ("High-Profile Arch", "Corrugated Steel"): (0.035, 0.035),
    ("Low-Profile Arch", "Corrugated Aluminum"): (0.035, 0.035),
    ("Low-Profile Arch", "Corrugated Steel"): (0.035, 0.035),
    ("Metal Box", "Corrugated Aluminum"): (0.035, 0.035),
    ("Metal Box", "Corrugated Steel"): (0.035, 0.035),
    ("Pipe Arch", "Aluminum Structural Plate"): (0.035, 0.035),
    ("Pipe Arch", "Concrete"): (0.012, 0.012),
    ("Pipe Arch", "Steel Structural Plate"): (0.035, 0.035),
    ("Pipe Arch", "Steel or Aluminum"): (0.025, 0.025),
    ("South Dakota Concrete Box Culvert", "Concrete"): (0.012, 0.012),
    ("User Defined", "Concrete"): (0.012, 0.012),
    ("User Defined", "Corrugated Metal Riveted or Welded"): (0.035, 0.035),
}

# Only these contexts are currently constructible as supported run-hy8
# barrels. Adding a new enum does not activate one of the observations above;
# its full shape, material, inlet and serialization support must be implemented
# before it is added to this bridge.
_SUPPORTED_CONTEXT_NAMES: dict[
    tuple[CulvertShape, CulvertMaterial], Hy8ShapeMaterialName
] = {
    (CulvertShape.CIRCLE, CulvertMaterial.CONCRETE): ("Circular", "Concrete"),
    (CulvertShape.CIRCLE, CulvertMaterial.CORRUGATED_STEEL): (
        "Circular",
        "Corrugated Steel",
    ),
    (CulvertShape.CIRCLE, CulvertMaterial.HDPE): ("Circular", "Smooth HDPE"),
    (CulvertShape.BOX, CulvertMaterial.CONCRETE): ("Concrete Box", "Concrete"),
}


def default_manning_values(
    shape: CulvertShape,
    material: CulvertMaterial,
) -> ManningPair:
    """Return the observed HY-8 v8 default for a supported context.

    Raises:
        ValueError: If ``run-hy8`` does not yet support the complete
            shape/material context. There is intentionally no catch-all.
    """

    context: tuple[CulvertShape, CulvertMaterial] = (shape, material)
    try:
        observed_name = _SUPPORTED_CONTEXT_NAMES[context]
    except KeyError as exc:
        raise ValueError(
            "No HY-8 v8 default Manning's n is registered for "
            f"{shape.name}/{material.name}. Specify both manning_n_top and "
            "manning_n_bottom explicitly or implement the complete researched "
            "shape/material context."
        ) from exc
    return HY8_V8_OBSERVED_MANNING_N[observed_name]


__all__: list[str] = [
    "HY8_V8_OBSERVED_MANNING_N",
    "ManningPair",
    "default_manning_values",
]
