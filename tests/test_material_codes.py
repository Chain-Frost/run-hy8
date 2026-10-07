"""Tests for shape-contextual HY-8 v8 material codes."""

from __future__ import annotations

import pytest

from run_hy8.material_codes import hy8_v8_material_code, material_from_hy8_v8_code
from run_hy8.type_helpers import CulvertMaterial, CulvertShape


@pytest.mark.parametrize(
    ("shape", "material", "expected_code"),
    [
        (CulvertShape.CIRCLE, CulvertMaterial.CONCRETE, 1),
        (CulvertShape.CIRCLE, CulvertMaterial.CORRUGATED_STEEL, 2),
        (CulvertShape.CIRCLE, CulvertMaterial.HDPE, 5),
        (CulvertShape.BOX, CulvertMaterial.CONCRETE, 1),
        (CulvertShape.ELLIPTICAL, CulvertMaterial.CONCRETE, 2),
    ],
)
def test_material_code_is_shape_contextual(
    shape: CulvertShape,
    material: CulvertMaterial,
    expected_code: int,
) -> None:
    assert hy8_v8_material_code(shape, material) == expected_code
    assert material_from_hy8_v8_code(shape, expected_code) is material


def test_ellipse_material_code_one_is_not_concrete() -> None:
    with pytest.raises(ValueError, match=r"material code 1.*ELLIPTICAL"):
        material_from_hy8_v8_code(CulvertShape.ELLIPTICAL, 1)


def test_unsupported_shape_material_context_fails_closed() -> None:
    with pytest.raises(ValueError, match="ELLIPTICAL/CORRUGATED_STEEL"):
        hy8_v8_material_code(
            CulvertShape.ELLIPTICAL,
            CulvertMaterial.CORRUGATED_STEEL,
        )
