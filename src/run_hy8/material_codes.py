"""Shape-contextual HY-8 v8 material-code mappings.

HY-8 project-file material integers are not global material identifiers. They
are one-based indices into each shape's Material Names list in ShapeDB.dat.
In particular, elliptical code 1 is "Steel or Aluminum" while elliptical code 2
is "Concrete". Treating CulvertMaterial.value as the file code therefore gives
the wrong material for ellipses.

The mappings below cover only shape/material contexts currently supported by
run-hy8. Unsupported contexts fail closed.
"""

from __future__ import annotations

from .type_helpers import CulvertMaterial, CulvertShape

HY8_V8_MATERIAL_CODE_BY_CONTEXT: dict[tuple[CulvertShape, CulvertMaterial], int] = {
    (CulvertShape.CIRCLE, CulvertMaterial.CONCRETE): 1,
    (CulvertShape.CIRCLE, CulvertMaterial.CORRUGATED_STEEL): 2,
    (CulvertShape.CIRCLE, CulvertMaterial.HDPE): 5,
    (CulvertShape.BOX, CulvertMaterial.CONCRETE): 1,
    (CulvertShape.ELLIPTICAL, CulvertMaterial.CONCRETE): 2,
}

HY8_V8_MATERIAL_BY_SHAPE_CODE: dict[tuple[CulvertShape, int], CulvertMaterial] = {
    (shape, code): material for (shape, material), code in HY8_V8_MATERIAL_CODE_BY_CONTEXT.items()
}


def hy8_v8_material_code(shape: CulvertShape, material: CulvertMaterial) -> int:
    """Return the contextual HY-8 v8 project-file material index."""
    try:
        return HY8_V8_MATERIAL_CODE_BY_CONTEXT[(shape, material)]
    except KeyError as exc:
        msg = (
            "Unsupported HY-8 v8 shape/material context: "
            f"{shape.name}/{material.name}. Material codes are shape-contextual."
        )
        raise ValueError(msg) from exc


def material_from_hy8_v8_code(shape: CulvertShape, code: int) -> CulvertMaterial:
    """Resolve a contextual HY-8 v8 material index into a supported material."""
    try:
        return HY8_V8_MATERIAL_BY_SHAPE_CODE[(shape, code)]
    except KeyError as exc:
        msg = f"Unsupported HY-8 v8 material code {code} for culvert shape {shape.name}."
        raise ValueError(msg) from exc


__all__: list[str] = [
    "HY8_V8_MATERIAL_BY_SHAPE_CODE",
    "HY8_V8_MATERIAL_CODE_BY_CONTEXT",
    "hy8_v8_material_code",
    "material_from_hy8_v8_code",
]
