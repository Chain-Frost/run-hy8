"""Tests for the version-pinned HY-8 concrete ellipse catalogue."""

from __future__ import annotations

import pytest

from run_hy8 import (
    CONCRETE_ELLIPSE_CATALOGUE,
    CulvertBarrel,
    CulvertMaterial,
    CulvertShape,
    EllipticalConcreteInlet,
    find_concrete_ellipse_catalogue_size,
)


def test_concrete_ellipse_catalogue_matches_shapedb_snapshot() -> None:
    assert len(CONCRETE_ELLIPSE_CATALOGUE) == 23
    entry = CONCRETE_ELLIPSE_CATALOGUE[8]

    assert entry.row_index_zero_based == 8
    assert entry.span_in == pytest.approx(60.0)
    assert entry.rise_in == pytest.approx(38.0)
    assert entry.area_ft2 == pytest.approx(12.850000381469727)
    assert entry.manning_n == pytest.approx(0.012000000104308128)
    assert entry.br_in == pytest.approx(51.599998474121094)
    assert entry.tr_in == pytest.approx(51.599998474121094)
    assert entry.cr_in == pytest.approx(16.43000030517578)
    assert entry.b_in == pytest.approx(19.0)
    assert entry.span_m == pytest.approx(1.524)
    assert entry.rise_m == pytest.approx(0.9652)


def test_catalogue_match_allows_project_file_round_trip_precision() -> None:
    entry = find_concrete_ellipse_catalogue_size(
        span_m=5.0 * 0.3048,
        rise_m=3.166667 * 0.3048,
    )

    assert entry.row_index_zero_based == 8


def test_catalogue_rejects_non_catalogued_size_without_substitution() -> None:
    with pytest.raises(ValueError, match="no nearest-size substitution"):
        find_concrete_ellipse_catalogue_size(1.5, 0.95)


def test_catalogue_rejects_reversed_horizontal_size() -> None:
    with pytest.raises(ValueError, match="Unsupported HY-8 concrete elliptical size"):
        find_concrete_ellipse_catalogue_size(0.9652, 1.524)


def test_barrel_validation_rejects_non_catalogued_ellipse() -> None:
    barrel = CulvertBarrel(
        shape=CulvertShape.ELLIPTICAL,
        material=CulvertMaterial.CONCRETE,
        span=1.5,
        rise=0.95,
        inlet_configuration=EllipticalConcreteInlet.SQUARE_EDGE_WITH_HEADWALL,
    )

    errors = barrel.validate()

    assert any("requires a catalogued ellipse size" in error for error in errors)


def test_barrel_validation_accepts_catalogued_ellipse() -> None:
    barrel = CulvertBarrel(
        shape=CulvertShape.ELLIPTICAL,
        material=CulvertMaterial.CONCRETE,
        span=1.524,
        rise=0.9652,
        inlet_configuration=EllipticalConcreteInlet.SQUARE_EDGE_WITH_HEADWALL,
    )

    assert barrel.validate() == []
