"""HY-8 v8 inlet-configuration modelling and serialization tests."""

from __future__ import annotations

from pathlib import Path

import pytest

from run_hy8 import (
    CircularConcreteInlet,
    CircularCorrugatedSteelInlet,
    CircularHdpeInlet,
    ConcreteBoxInlet,
    CulvertBarrel,
    CulvertMaterial,
    CulvertShape,
    Hy8Executable,
    Hy8FileWriter,
    InletEdgeType,
    LegacyInletConfigurationWarning,
    culvert_dataframe,
)
from run_hy8.hydraulic_defaults import HY8_V8_OBSERVED_MANNING_N
from run_hy8.inlet_configurations import (
    HY8_V8_INLET_SPECS,
    resolve_v8_inlet_configuration,
    resolve_v8_inlet_spec,
)
from run_hy8.reader import load_project_from_hy8
from run_hy8.results import parse_rsql, parse_rst

from .sample_data import build_sample_project

EXAMPLE_FILE = Path(__file__).resolve().parent / "example_crossings.hy8"


def test_default_barrel_is_thin_edge_corrugated_steel_pipe() -> None:
    barrel = CulvertBarrel()

    assert barrel.shape is CulvertShape.CIRCLE
    assert barrel.material is CulvertMaterial.CORRUGATED_STEEL
    assert barrel.inlet_configuration is CircularCorrugatedSteelInlet.THIN_EDGE_PROJECTING
    assert barrel.manning_values() == (0.024, 0.024)


@pytest.mark.parametrize(
    ("shape", "material", "expected"),
    [
        (CulvertShape.CIRCLE, CulvertMaterial.CONCRETE, 0.012),
        (CulvertShape.CIRCLE, CulvertMaterial.CORRUGATED_STEEL, 0.024),
        (CulvertShape.CIRCLE, CulvertMaterial.HDPE, 0.012),
        (CulvertShape.BOX, CulvertMaterial.CONCRETE, 0.012),
    ],
)
def test_hy8_v8_default_manning_values(
    shape: CulvertShape,
    material: CulvertMaterial,
    expected: float,
) -> None:
    barrel = CulvertBarrel(shape=shape, material=material)

    assert barrel.manning_values() == (expected, expected)


def test_default_manning_registry_covers_every_supported_context() -> None:
    supported_contexts = {(spec.shape, spec.material) for spec in HY8_V8_INLET_SPECS.values()}

    barrels = [CulvertBarrel(shape=shape, material=material) for shape, material in supported_contexts]
    assert all(barrel.manning_values() for barrel in barrels)


def test_all_observed_hy8_v8_manning_defaults_are_recorded() -> None:
    assert len(HY8_V8_OBSERVED_MANNING_N) == 25
    assert HY8_V8_OBSERVED_MANNING_N[("Circular", "Corrugated Aluminum")] == (0.031, 0.031)
    assert HY8_V8_OBSERVED_MANNING_N[("Circular", "Corrugated PE")] == (0.024, 0.024)
    assert HY8_V8_OBSERVED_MANNING_N[("Circular", "PVC")] == (0.011, 0.011)
    assert HY8_V8_OBSERVED_MANNING_N[("Concrete Open-Bottom Arch", "Concrete")] == (0.012, 0.035)


def test_unregistered_manning_context_does_not_fall_back() -> None:
    barrel = CulvertBarrel(shape=CulvertShape.BOX, material=CulvertMaterial.HDPE)

    with pytest.raises(ValueError, match="No HY-8 v8 default Manning's n"):
        barrel.manning_values()


def test_manual_manning_values_override_defaults_independently() -> None:
    barrel = CulvertBarrel(manning_n_top=0.020)
    assert barrel.resolved_manning_values() == (0.020, 0.024)

    barrel.manning_n_bottom = 0.030
    assert barrel.resolved_manning_values() == (0.020, 0.030)


def test_complete_manual_manning_values_do_not_require_registered_context() -> None:
    barrel = CulvertBarrel(
        shape=CulvertShape.BOX,
        material=CulvertMaterial.HDPE,
        manning_n_top=0.015,
        manning_n_bottom=0.017,
    )

    assert barrel.resolved_manning_values() == (0.015, 0.017)


@pytest.mark.parametrize(
    ("configuration", "expected_index"),
    [
        (ConcreteBoxInlet.SQUARE_EDGE_30_TO_75_DEG_WINGWALL, 3),
        (ConcreteBoxInlet.SQUARE_EDGE_90_OR_15_DEG_WINGWALL, 4),
        (ConcreteBoxInlet.SQUARE_EDGE_0_DEG_WINGWALL, 5),
        (ConcreteBoxInlet.BEVEL_1_TO_1_45_DEG_WINGWALL, 7),
    ],
)
def test_concrete_box_v8_indices(configuration: ConcreteBoxInlet, expected_index: int) -> None:
    spec = resolve_v8_inlet_spec(configuration)

    assert spec.v8_index == expected_index
    assert (
        resolve_v8_inlet_configuration(
            shape=spec.shape,
            material=spec.material,
            inlet_type=spec.inlet_type,
            v8_index=expected_index,
        )
        is configuration
    )


def test_duplicate_slugs_remain_context_specific() -> None:
    concrete = resolve_v8_inlet_spec(CircularConcreteInlet.SQUARE_EDGE_WITH_HEADWALL)
    steel = resolve_v8_inlet_spec(CircularCorrugatedSteelInlet.SQUARE_EDGE_WITH_HEADWALL)
    hdpe = resolve_v8_inlet_spec(CircularHdpeInlet.SQUARE_EDGE_WITH_HEADWALL)

    assert concrete.v8_index == 0
    assert steel.v8_index == 2
    assert hdpe.v8_index == 0
    assert len(HY8_V8_INLET_SPECS) == 24


def test_invalid_shape_material_configuration_is_rejected() -> None:
    barrel = CulvertBarrel(
        shape=CulvertShape.BOX,
        material=CulvertMaterial.CONCRETE,
        inlet_configuration=CircularConcreteInlet.SQUARE_EDGE_WITH_HEADWALL,
    )

    assert any("not valid" in error for error in barrel.validate())


def test_writer_uses_v8_contextual_index_and_neutral_legacy_card(tmp_path: Path) -> None:
    project = build_sample_project()
    barrel = project.crossings[0].culverts[0]
    barrel.shape = CulvertShape.BOX
    barrel.inlet_configuration = ConcreteBoxInlet.SQUARE_EDGE_30_TO_75_DEG_WINGWALL

    output = Hy8FileWriter(project).write(tmp_path / "box.hy8")
    lines = output.read_text(encoding="utf-8").splitlines()

    assert any(line.startswith("INLETEDGETYPE ") and line.split()[-1] == "0" for line in lines)
    assert any(line.startswith("INLETEDGETYPE71 ") and line.split()[-1] == "3" for line in lines)


def test_reader_uses_contextual_v8_index() -> None:
    project = load_project_from_hy8(EXAMPLE_FILE)
    box = project.crossings[3].culverts[0]

    assert box.inlet_configuration is ConcreteBoxInlet.SQUARE_EDGE_30_TO_75_DEG_WINGWALL


def test_culvert_dataframe_exposes_semantic_configuration_only() -> None:
    dataframe = culvert_dataframe(load_project_from_hy8(EXAMPLE_FILE))

    assert "inlet_configuration" in dataframe.columns
    assert "inlet_edge_type" not in dataframe.columns
    assert "inlet_edge_type71" not in dataframe.columns
    assert "_legacy_warning_emitted" not in dataframe.columns


def test_legacy_constructor_input_warns() -> None:
    with pytest.warns(LegacyInletConfigurationWarning):
        barrel = CulvertBarrel(inlet_edge_type=InletEdgeType.THIN_EDGE_PROJECTING)

    assert barrel.resolved_inlet_configuration() is CircularCorrugatedSteelInlet.THIN_EDGE_PROJECTING


def test_reader_rejects_pre_v8_header(tmp_path: Path) -> None:
    path = tmp_path / "old.hy8"
    path.write_text("HY8PROJECTFILE71\nENDPROJECTFILE", encoding="utf-8")

    with pytest.raises(ValueError, match="supports version 8 only"):
        load_project_from_hy8(path)


def test_writer_rejects_non_v8_header_request() -> None:
    with pytest.raises(ValueError, match="supports version 8 only"):
        Hy8FileWriter(build_sample_project(), version=71)


@pytest.mark.requires_hy8
@pytest.mark.parametrize(
    ("v8_index", "configuration"),
    [
        (3, ConcreteBoxInlet.SQUARE_EDGE_30_TO_75_DEG_WINGWALL),
        (4, ConcreteBoxInlet.SQUARE_EDGE_90_OR_15_DEG_WINGWALL),
        (5, ConcreteBoxInlet.SQUARE_EDGE_0_DEG_WINGWALL),
    ],
)
def test_box_wingwall_v8_results_survive_round_trip(
    tmp_path: Path,
    v8_index: int,
    configuration: ConcreteBoxInlet,
) -> None:
    source_text = EXAMPLE_FILE.read_text(encoding="utf-8")
    original_pair = "INLETEDGETYPE        4\nINLETEDGETYPE71      3"
    replacement_pair = f"INLETEDGETYPE        4\nINLETEDGETYPE71      {v8_index}"
    assert original_pair in source_text

    original = tmp_path / f"box_{v8_index}_original.hy8"
    original.write_text(source_text.replace(original_pair, replacement_pair, 1), encoding="utf-8")
    project = load_project_from_hy8(original)
    assert project.crossings[3].culverts[0].inlet_configuration is configuration

    regenerated = Hy8FileWriter(project).write(tmp_path / f"box_{v8_index}_regenerated.hy8")
    executable = Hy8Executable()
    executable.open_run_save(original)
    executable.open_run_save(regenerated)

    assert parse_rst(original.with_suffix(".rst")) == parse_rst(regenerated.with_suffix(".rst"))
    assert parse_rsql(original.with_suffix(".rsql")) == parse_rsql(regenerated.with_suffix(".rsql"))
