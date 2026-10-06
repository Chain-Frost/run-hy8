"""HY-8 v8 elliptical culvert modelling and executable regression tests."""

from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any

import pytest

from run_hy8 import (
    CulvertBarrel,
    CulvertMaterial,
    CulvertShape,
    EllipticalConcreteInlet,
    Hy8Executable,
    Hy8FileWriter,
    Hy8Project,
    load_project_from_hy8,
    load_project_from_json,
    parse_rsql,
    parse_rst,
)
from run_hy8.inlet_configurations import (
    default_inlet_configuration,
    resolve_v8_inlet_configuration,
    resolve_v8_inlet_spec,
)

from .sample_data import CONFIG_JSON, build_sample_project


def _ellipse_project(*, span: float, rise: float) -> Hy8Project:
    project = build_sample_project()
    barrel = project.crossings[0].culverts[0]
    barrel.shape = CulvertShape.ELLIPTICAL
    barrel.material = CulvertMaterial.CONCRETE
    barrel.span = span
    barrel.rise = rise
    barrel.inlet_configuration = EllipticalConcreteInlet.SQUARE_EDGE_WITH_HEADWALL
    barrel.manning_n_top = None
    barrel.manning_n_bottom = None
    return project


def test_elliptical_shape_code_is_verified_hy8_v8_code() -> None:
    assert CulvertShape.ELLIPTICAL.value == 3


@pytest.mark.parametrize(
    ("configuration", "expected_index", "expected_label"),
    [
        (
            EllipticalConcreteInlet.SQUARE_EDGE_WITH_HEADWALL,
            0,
            "Square Edge with Headwall",
        ),
        (
            EllipticalConcreteInlet.GROOVED_EDGE_WITH_HEADWALL,
            1,
            "Grooved Edge with Headwall",
        ),
        (
            EllipticalConcreteInlet.GROOVED_EDGE_PROJECTING,
            2,
            "Grooved Edge Projecting",
        ),
    ],
)
def test_elliptical_concrete_v8_inlet_indices(
    configuration: EllipticalConcreteInlet,
    expected_index: int,
    expected_label: str,
) -> None:
    spec = resolve_v8_inlet_spec(configuration)

    assert spec.shape is CulvertShape.ELLIPTICAL
    assert spec.material is CulvertMaterial.CONCRETE
    assert spec.v8_index == expected_index
    assert spec.label == expected_label
    assert (
        resolve_v8_inlet_configuration(
            shape=CulvertShape.ELLIPTICAL,
            material=CulvertMaterial.CONCRETE,
            inlet_type=spec.inlet_type,
            v8_index=expected_index,
        )
        is configuration
    )


def test_elliptical_concrete_defaults_are_context_specific() -> None:
    barrel = CulvertBarrel(
        shape=CulvertShape.ELLIPTICAL,
        material=CulvertMaterial.CONCRETE,
        inlet_configuration=EllipticalConcreteInlet.SQUARE_EDGE_WITH_HEADWALL,
    )

    assert barrel.manning_values() == (0.012, 0.012)
    assert (
        default_inlet_configuration(
            shape=CulvertShape.ELLIPTICAL,
            material=CulvertMaterial.CONCRETE,
        )
        is EllipticalConcreteInlet.SQUARE_EDGE_WITH_HEADWALL
    )

    with pytest.raises(ValueError, match="Unsupported HY-8 v8 inlet configuration"):
        default_inlet_configuration(
            shape=CulvertShape.ELLIPTICAL,
            material=CulvertMaterial.CORRUGATED_STEEL,
        )


@pytest.mark.parametrize(
    ("span", "rise"),
    [
        (1.524, 0.9652),
        (0.9652, 1.524),
    ],
)
def test_ellipse_writer_reader_preserves_orientation(
    tmp_path: Path,
    span: float,
    rise: float,
) -> None:
    project = _ellipse_project(span=span, rise=rise)

    output = Hy8FileWriter(project).write(tmp_path / "ellipse.hy8")
    text = output.read_text(encoding="utf-8")
    assert "CULVERTSHAPE         3" in text
    assert "INLETEDGETYPE71      0" in text

    restored = load_project_from_hy8(output)
    barrel = restored.crossings[0].culverts[0]

    assert barrel.shape is CulvertShape.ELLIPTICAL
    assert barrel.material is CulvertMaterial.CONCRETE
    assert barrel.inlet_configuration is EllipticalConcreteInlet.SQUARE_EDGE_WITH_HEADWALL
    assert barrel.span == pytest.approx(span, abs=2e-6)
    assert barrel.rise == pytest.approx(rise, abs=2e-6)


@pytest.mark.parametrize(
    ("span", "rise"),
    [
        (1.524, 0.9652),
        (0.9652, 1.524),
    ],
)
def test_ellipse_json_config_preserves_orientation(
    tmp_path: Path,
    span: float,
    rise: float,
) -> None:
    config: dict[str, Any] = json.loads(CONFIG_JSON)
    culvert: dict[str, Any] = config["crossings"][0]["culverts"][0]
    culvert["shape"] = "elliptical"
    culvert["material"] = "concrete"
    culvert["span"] = span
    culvert["rise"] = rise
    culvert["inlet_configuration"] = "square-edge-with-headwall"

    path = tmp_path / "ellipse.json"
    path.write_text(json.dumps(config), encoding="utf-8")
    project = load_project_from_json(path)
    barrel = project.crossings[0].culverts[0]

    assert barrel.shape is CulvertShape.ELLIPTICAL
    assert barrel.inlet_configuration is EllipticalConcreteInlet.SQUARE_EDGE_WITH_HEADWALL
    assert barrel.span == pytest.approx(span)
    assert barrel.rise == pytest.approx(rise)

    serialized = json.loads(json.dumps(barrel.to_dict()))
    restored = CulvertBarrel.from_dict(serialized)
    assert restored.shape is CulvertShape.ELLIPTICAL
    assert restored.span == pytest.approx(span)
    assert restored.rise == pytest.approx(rise)


def test_ellipse_unsupported_material_fails_closed(tmp_path: Path) -> None:
    config: dict[str, Any] = json.loads(CONFIG_JSON)
    culvert: dict[str, Any] = config["crossings"][0]["culverts"][0]
    culvert["shape"] = "elliptical"
    culvert["material"] = "corrugated steel"
    culvert["span"] = 1.524
    culvert["rise"] = 0.9652
    culvert.pop("inlet_configuration")

    path = tmp_path / "unsupported.json"
    path.write_text(json.dumps(config), encoding="utf-8")

    with pytest.raises(ValueError, match=r"ELLIPTICAL.*CORRUGATED_STEEL"):
        load_project_from_json(path)


@pytest.mark.requires_hy8
@pytest.mark.parametrize(
    ("span", "rise"),
    [
        (1.524, 0.9652),
        (0.9652, 1.524),
    ],
)
def test_ellipse_hy8_v8_executable_round_trip(
    tmp_path: Path,
    span: float,
    rise: float,
) -> None:
    project = _ellipse_project(span=span, rise=rise)
    path = Hy8FileWriter(project).write(tmp_path / "ellipse_exec.hy8")

    Hy8Executable().open_run_save(path)

    restored = load_project_from_hy8(path)
    barrel = restored.crossings[0].culverts[0]
    assert barrel.shape is CulvertShape.ELLIPTICAL
    assert barrel.span == pytest.approx(span, abs=2e-6)
    assert barrel.rise == pytest.approx(rise, abs=2e-6)

    rst = parse_rst(path.with_suffix(".rst"))
    series = rst["Sample Crossing"]
    headwaters = series["headwater"]
    assert headwaters
    assert all(math.isfinite(value) for value in headwaters)

    culverts = series["culverts"]
    assert len(culverts) == 1
    culvert = culverts[0]
    for key in (
        "discharge",
        "inlet_control_depth",
        "outlet_control_depth",
        "full_length",
        "free_length",
        "outlet_velocity",
    ):
        values = culvert[key]
        assert values
        assert all(math.isfinite(value) for value in values)
    assert culvert["flow_type"]

    profiles = parse_rsql(path.with_suffix(".rsql"))["Sample Crossing"]
    assert profiles
    assert all(math.isfinite(profile.flow) for profile in profiles)
    assert all(math.isfinite(profile.headwater_to_depth_ratio) for profile in profiles)
    assert all(profile.flow_type for profile in profiles)
