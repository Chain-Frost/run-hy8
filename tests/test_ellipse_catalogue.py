"""Tests for the version-pinned HY-8 concrete ellipse catalogue."""

from __future__ import annotations

from pathlib import Path

import pytest

from run_hy8 import (
    CONCRETE_ELLIPSE_CATALOGUE,
    CulvertMaterial,
    CulvertShape,
    EllipticalConcreteInlet,
    Hy8FileWriter,
    Hy8Project,
    UnitSystem,
    find_concrete_ellipse_catalogue_size,
)

from .sample_data import build_sample_project


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


def _project_with_concrete_ellipse(
    span: float,
    rise: float,
    *,
    units: UnitSystem = UnitSystem.SI,
) -> Hy8Project:
    project = build_sample_project()
    project.units = units
    barrel = project.crossings[0].culverts[0]
    barrel.shape = CulvertShape.ELLIPTICAL
    barrel.material = CulvertMaterial.CONCRETE
    barrel.span = span
    barrel.rise = rise
    barrel.inlet_configuration = EllipticalConcreteInlet.SQUARE_EDGE_WITH_HEADWALL
    barrel.manning_n_top = None
    barrel.manning_n_bottom = None
    return project


def test_writer_rejects_non_catalogued_ellipse(tmp_path: Path) -> None:
    project = _project_with_concrete_ellipse(1.5, 0.95)

    with pytest.raises(ValueError, match="no nearest-size substitution"):
        Hy8FileWriter(project).write(tmp_path / "unsupported.hy8")


def test_writer_accepts_catalogued_si_ellipse(tmp_path: Path) -> None:
    project = _project_with_concrete_ellipse(1.524, 0.9652)

    path = Hy8FileWriter(project).write(tmp_path / "supported-si.hy8")

    assert path.exists()


def test_writer_accepts_catalogued_english_ellipse(tmp_path: Path) -> None:
    project = _project_with_concrete_ellipse(
        5.0,
        3.166667,
        units=UnitSystem.ENGLISH,
    )

    text = Hy8FileWriter(project).write(tmp_path / "supported-en.hy8").read_text(encoding="utf-8")

    assert "CULVERTSHAPE         3" in text
    assert "CULVERTMATERIAL      2" in text
    geometry_line = next(line for line in text.splitlines() if line.startswith("BARRELGEOMETRY"))
    geometry = [float(value) for value in geometry_line.split()[1:]]
    assert geometry == pytest.approx(
        [4.3, 4.3, 16.43 / 12.0, 19.0 / 12.0, 12.850000381469727],
        abs=1e-6,
    )
