"""Tests for the version-pinned HY-8 concrete ellipse catalogue."""

from __future__ import annotations

import csv
from pathlib import Path

import pytest

from run_hy8 import (
    CONCRETE_ELLIPSE_CATALOGUE,
    STEEL_OR_ALUMINUM_ELLIPSE_CATALOGUE,
    CulvertMaterial,
    CulvertShape,
    EllipticalConcreteInlet,
    EllipticalSteelOrAluminumInlet,
    Hy8FileWriter,
    Hy8Project,
    UnitSystem,
    find_concrete_ellipse_catalogue_size,
    find_ellipse_catalogue_size,
    find_steel_or_aluminum_ellipse_catalogue_size,
    load_project_from_hy8,
)
from run_hy8.ellipse_catalogue import EllipticalCatalogueSize

from .sample_data import build_sample_project


@pytest.mark.parametrize("units", [UnitSystem.SI, UnitSystem.ENGLISH])
@pytest.mark.parametrize(
    ("material", "entry"),
    [
        (material, entry)
        for material, catalogue in (
            (CulvertMaterial.CONCRETE, CONCRETE_ELLIPSE_CATALOGUE),
            (CulvertMaterial.STEEL_OR_ALUMINUM, STEEL_OR_ALUMINUM_ELLIPSE_CATALOGUE),
        )
        for entry in catalogue
    ],
    ids=lambda value: value.name if isinstance(value, CulvertMaterial) else str(value.row_index_zero_based),
)
def test_entire_catalogue_writer_readback(
    tmp_path: Path,
    units: UnitSystem,
    material: CulvertMaterial,
    entry: EllipticalCatalogueSize,
) -> None:
    source_path = Path(__file__).resolve().parents[1] / "reference_docs/catalogue/catalogue_sizes.csv"
    label = "Concrete" if material is CulvertMaterial.CONCRETE else "Steel or Aluminum"
    with source_path.open(newline="", encoding="utf-8") as handle:
        source_rows = [row for row in csv.DictReader(handle) if row["table_path"].startswith(f"/Elliptical/{label}/")]
    source = source_rows[entry.row_index_zero_based]
    assert [
        entry.span_in,
        entry.rise_in,
        entry.area_ft2,
        entry.manning_n,
        entry.br_in,
        entry.tr_in,
        entry.cr_in,
        entry.b_in,
    ] == [float(source[key]) for key in ("Span", "Rise", "Area", "Mannings n", "Br", "Tr", "Cr", "B")]
    span = entry.span_m if units is UnitSystem.SI else entry.span_in / 12
    rise = entry.rise_m if units is UnitSystem.SI else entry.rise_in / 12
    factory = (
        _project_with_concrete_ellipse
        if material is CulvertMaterial.CONCRETE
        else _project_with_steel_or_aluminum_ellipse
    )
    project = factory(span, rise, units=units)
    path = Hy8FileWriter(project).write(tmp_path / "catalogue.hy8")
    cards = {line.split()[0]: line.split()[1:] for line in path.read_text().splitlines() if line.split()}
    assert [float(value) for value in cards["BARRELGEOMETRY"]] == pytest.approx(
        [*entry.geometry_prefix_ft, entry.area_ft2],
        abs=1e-6,
    )
    assert [float(value) for value in cards["BARRELDATA"]][2:] == pytest.approx(
        [entry.manning_n, 0.0],
        abs=1e-6,
    )
    restored = load_project_from_hy8(path)
    barrel = restored.crossings[0].culverts[0]
    # Reader normalizes all project-file lengths to SI, regardless of display flag.
    assert restored.units is UnitSystem.SI
    assert barrel.material is material
    assert barrel.shape is CulvertShape.ELLIPTICAL
    assert barrel.span == pytest.approx(entry.span_m, abs=2e-6)
    assert barrel.rise == pytest.approx(entry.rise_m, abs=2e-6)
    assert barrel.resolved_manning_values() == pytest.approx((entry.manning_n, 0.0), abs=1e-6)


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


def test_steel_or_aluminum_ellipse_catalogue_matches_gui_reference() -> None:
    assert len(STEEL_OR_ALUMINUM_ELLIPSE_CATALOGUE) == 40
    entry = STEEL_OR_ALUMINUM_ELLIPSE_CATALOGUE[1]

    assert entry.row_index_zero_based == 1
    assert entry.span_in == pytest.approx(241.0)
    assert entry.rise_in == pytest.approx(156.0)
    assert entry.area_ft2 == pytest.approx(201.85000610351562)
    assert entry.manning_n == pytest.approx(0.03400000184774399)
    assert entry.geometry_prefix_ft == pytest.approx((157.0 / 12.0, 157.0 / 12.0, 54.0 / 12.0, 78.0 / 12.0))


def test_steel_or_aluminum_catalogue_uses_per_size_manning() -> None:
    assert STEEL_OR_ALUMINUM_ELLIPSE_CATALOGUE[1].manning_n == pytest.approx(0.034)
    assert STEEL_OR_ALUMINUM_ELLIPSE_CATALOGUE[4].manning_n == pytest.approx(0.033)


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
    with pytest.raises(ValueError, match="Unsupported HY-8 Concrete elliptical size"):
        find_concrete_ellipse_catalogue_size(0.9652, 1.524)


def test_generic_catalogue_lookup_is_material_specific() -> None:
    concrete = find_ellipse_catalogue_size(
        1.524,
        0.9652,
        material=CulvertMaterial.CONCRETE,
    )
    steel = find_steel_or_aluminum_ellipse_catalogue_size(
        241.0 * 0.0254,
        156.0 * 0.0254,
    )

    assert concrete.span_in == pytest.approx(60.0)
    assert steel.span_in == pytest.approx(241.0)


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
    barrel.outlet_invert_station = barrel.inlet_invert_station + 20.0
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


def _project_with_steel_or_aluminum_ellipse(
    span: float,
    rise: float,
    *,
    units: UnitSystem = UnitSystem.SI,
) -> Hy8Project:
    project = build_sample_project()
    project.units = units
    barrel = project.crossings[0].culverts[0]
    barrel.shape = CulvertShape.ELLIPTICAL
    barrel.material = CulvertMaterial.STEEL_OR_ALUMINUM
    barrel.span = span
    barrel.rise = rise
    barrel.inlet_configuration = EllipticalSteelOrAluminumInlet.HEADWALL
    barrel.outlet_invert_station = barrel.inlet_invert_station + 20.0
    barrel.manning_n_top = None
    barrel.manning_n_bottom = None
    return project


def test_writer_accepts_catalogued_steel_or_aluminum_ellipse(tmp_path: Path) -> None:
    project = _project_with_steel_or_aluminum_ellipse(
        241.0 * 0.0254,
        156.0 * 0.0254,
    )

    text = Hy8FileWriter(project).write(tmp_path / "steel-ellipse.hy8").read_text(encoding="utf-8")

    assert "CULVERTSHAPE         3" in text
    assert "CULVERTMATERIAL      1" in text
    geometry_line = next(line for line in text.splitlines() if line.startswith("BARRELGEOMETRY"))
    geometry = [float(value) for value in geometry_line.split()[1:]]
    assert geometry == pytest.approx(
        [
            157.0 / 12.0,
            157.0 / 12.0,
            54.0 / 12.0,
            78.0 / 12.0,
            201.85000610351562,
        ],
        abs=1e-6,
    )


def test_failed_ellipse_write_preserves_existing_file(tmp_path: Path) -> None:
    destination = tmp_path / "existing.hy8"
    destination.write_text("existing valid project\n", encoding="utf-8")
    project = _project_with_concrete_ellipse(0.9652, 1.524)

    with pytest.raises(ValueError, match="Unsupported HY-8 Concrete elliptical size"):
        Hy8FileWriter(project).write(destination)

    assert destination.read_text(encoding="utf-8") == "existing valid project\n"


def test_writer_uses_size_specific_steel_or_aluminum_manning(tmp_path: Path) -> None:
    project = _project_with_steel_or_aluminum_ellipse(
        252.0 * 0.0254,
        182.0 * 0.0254,
    )

    text = Hy8FileWriter(project).write(tmp_path / "steel-ellipse-033.hy8").read_text(encoding="utf-8")
    barrel_data = next(line for line in text.splitlines() if line.startswith("BARRELDATA"))
    values = [float(value) for value in barrel_data.split()[1:]]

    assert values[2:] == pytest.approx([0.033, 0.0], abs=1e-6)


def test_writer_accepts_catalogued_steel_or_aluminum_english_units(tmp_path: Path) -> None:
    project = _project_with_steel_or_aluminum_ellipse(
        241.0 / 12.0,
        156.0 / 12.0,
        units=UnitSystem.ENGLISH,
    )

    path = Hy8FileWriter(project).write(tmp_path / "steel-ellipse-en.hy8")

    assert path.exists()
    assert "CULVERTMATERIAL      1" in path.read_text(encoding="utf-8")


def test_writer_defaults_ellipse_barrel_data_fourth_field_to_zero(tmp_path: Path) -> None:
    project = _project_with_concrete_ellipse(60.0 * 0.0254, 38.0 * 0.0254)

    text = Hy8FileWriter(project).write(tmp_path / "concrete-ellipse-n.hy8").read_text(encoding="utf-8")
    barrel_data = next(line for line in text.splitlines() if line.startswith("BARRELDATA"))
    values = [float(value) for value in barrel_data.split()[1:]]

    assert values[2:] == pytest.approx([0.012, 0.0], abs=1e-6)


def test_writer_preserves_explicit_ellipse_bottom_manning_override(tmp_path: Path) -> None:
    project = _project_with_steel_or_aluminum_ellipse(
        241.0 * 0.0254,
        156.0 * 0.0254,
    )
    project.crossings[0].culverts[0].manning_n_bottom = 0.041

    text = Hy8FileWriter(project).write(tmp_path / "steel-ellipse-n-override.hy8").read_text(encoding="utf-8")
    barrel_data = next(line for line in text.splitlines() if line.startswith("BARRELDATA"))
    values = [float(value) for value in barrel_data.split()[1:]]

    assert values[2:] == pytest.approx([0.034, 0.041], abs=1e-6)
