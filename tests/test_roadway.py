"""Roadway contracts, policy propagation, and executable input parity."""

from __future__ import annotations

import json
import math
import os
import shutil
import subprocess
import warnings
from pathlib import Path

import pytest

from run_hy8 import (
    FlowDefinition,
    FlowMethod,
    Hy8Executable,
    Hy8FileWriter,
    Hy8Project,
    Hy8Results,
    RoadwayOvertoppingError,
    RoadwayOvertoppingPolicy,
    RoadwayOvertoppingWarning,
    RoadwayProfile,
    RoadwayShape,
    RoadwaySurface,
    UnitSystem,
    check_roadway_overtopping,
    cli,
    hydraulics,
    load_project_from_hy8,
    parse_rsql,
    parse_rst,
    project_from_mapping,
)
from run_hy8.units import weir_coefficient_to_english, weir_coefficient_to_si
from scripts.validate_roadway import build_case, execute_case

from .sample_data import CONFIG_JSON


@pytest.mark.parametrize("units", [UnitSystem.SI, UnitSystem.ENGLISH])
@pytest.mark.parametrize("surface", list(RoadwaySurface))
def test_coefficient_file_and_dictionary_roundtrip(tmp_path: Path, units: UnitSystem, surface: RoadwaySurface) -> None:
    project = build_case("constant-free", surface, units=units)
    project = Hy8Project.from_dict(json.loads(json.dumps(project.to_dict())))
    path = Hy8FileWriter(project).write(tmp_path / "coefficient.hy8")
    card = next(line for line in path.read_text().splitlines() if line.startswith("WEIRCOEFF"))
    assert float(card.split()[1]) == pytest.approx(2.898094224008874, abs=5e-7)
    road = load_project_from_hy8(path).crossings[0].roadway
    assert road.surface == surface
    assert road.discharge_coefficient == pytest.approx(1.6, abs=3e-7)
    assert RoadwayProfile.from_dict(road.to_dict()).to_dict() == road.to_dict()


def test_coefficient_dimensional_conversion() -> None:
    assert weir_coefficient_to_si(2.898094224008874) == pytest.approx(1.6)
    assert weir_coefficient_to_english(1.6) == pytest.approx(2.898094224008874)


@pytest.mark.parametrize("coefficient", [None, math.nan, math.inf, -math.inf, 0, -1, 1, 2])
def test_invalid_active_coefficient(coefficient: float | None) -> None:
    road = build_case("constant-free").crossings[0].roadway
    road.discharge_coefficient = coefficient
    assert any("discharge_coefficient" in error for error in road.validate())


@pytest.mark.parametrize("coefficient", [2.5, 3.095])
def test_coefficient_range_endpoints(coefficient: float) -> None:
    road = build_case("constant-free").crossings[0].roadway
    road.discharge_coefficient = weir_coefficient_to_si(coefficient)
    assert road.validate() == []


def test_config_preserves_coefficient_and_named_shape() -> None:
    raw = build_case("submerged").to_dict()
    config = json.loads(CONFIG_JSON)
    config["crossings"][0]["roadway"] = raw["crossings"][0]["roadway"]
    project = project_from_mapping(json.loads(json.dumps(config)))
    assert project.crossings[0].roadway.discharge_coefficient == 1.6
    assert project.crossings[0].roadway.shape is RoadwayShape.CONSTANT
    assert project.validate() == []


@pytest.mark.parametrize("count", [2, 5001])
def test_invalid_irregular_count(count: int) -> None:
    road = RoadwayProfile(
        width=10, shape=RoadwayShape.IRREGULAR, stations=list(map(float, range(count))), elevations=[12] * count
    )
    assert any("3-5000" in error for error in road.validate())


@pytest.mark.parametrize("count", [3, 15, 16, 5000])
def test_supported_irregular_count(count: int) -> None:
    road = RoadwayProfile(
        width=10, shape=RoadwayShape.IRREGULAR, stations=list(map(float, range(count))), elevations=[12] * count
    )
    assert road.validate() == []


@pytest.mark.parametrize(
    ("stations", "elevations"),
    [
        ([0, 0], [12, 12]),
        ([2, 1], [12, 12]),
        ([0, math.inf], [12, 12]),
        ([0, 20], [12, math.nan]),
        ([0, 10, 20], [12, 12, 12]),
        ([0, 20], [12, 13]),
    ],
)
def test_invalid_constant_profile(stations: list[float], elevations: list[float]) -> None:
    assert RoadwayProfile(width=10, stations=stations, elevations=elevations).validate()


def test_linear_slope_has_explicit_middle_point() -> None:
    road = RoadwayProfile(width=10, shape=RoadwayShape.IRREGULAR, stations=[0, 10, 20], elevations=[12, 12.5, 13])
    assert road.validate() == []


def test_submerged_serialization(tmp_path: Path) -> None:
    path = Hy8FileWriter(build_case("submerged")).write(tmp_path / "submerged.hy8")
    assert load_project_from_hy8(path).crossings[0].tailwater.constant_elevation == pytest.approx(12.9, abs=4e-7)


@pytest.mark.parametrize("flow", [math.nan, math.inf, -math.inf, -1])
def test_invalid_flow_cannot_enter_padding_loop(tmp_path: Path, flow: float) -> None:
    project = build_case("irregular-free")
    project.crossings[0].flow.user_values = [flow]
    with pytest.raises(ValueError, match="finite and non-negative"):
        Hy8FileWriter(project).write(tmp_path / "invalid.hy8")


def test_unknown_saved_surface_is_not_replaced(tmp_path: Path) -> None:
    path = Hy8FileWriter(build_case("constant-free")).write(tmp_path / "unknown.hy8")
    path.write_text(path.read_text().replace("SURFACE              3", "SURFACE              99"), encoding="utf-8")
    with pytest.raises(ValueError, match="Unsupported HY-8 roadway surface"):
        load_project_from_hy8(path)


@pytest.mark.parametrize("discharge", [0, 0.0049, 0.005, -0.0049])
def test_no_overtopping_noise(discharge: float) -> None:
    results = Hy8Results({"flow": [10], "headwater": [99], "roadway": [discharge], "iterations": ["Overtopping"]})
    with warnings.catch_warnings(record=True) as caught:
        for policy in RoadwayOvertoppingPolicy:
            check_roadway_overtopping(results, "Example", policy)
    assert not caught


def test_actual_discharge_policies_retain_results() -> None:
    results = Hy8Results({"flow": [10], "headwater": [0], "roadway": [0.01]})
    with pytest.raises(RoadwayOvertoppingError, match=r"Example.*0\.01 m3/s") as caught:
        check_roadway_overtopping(results, "Example")
    assert caught.value.results is results
    with pytest.warns(RoadwayOvertoppingWarning, match="0.01 m3/s"):
        check_roadway_overtopping(results, "Example", RoadwayOvertoppingPolicy.WARN)
    with warnings.catch_warnings(record=True) as warning_list:
        check_roadway_overtopping(results, "Example", RoadwayOvertoppingPolicy.ALLOW)
    assert not warning_list


@pytest.mark.parametrize("policy", list(RoadwayOvertoppingPolicy))
def test_missing_roadway_result_is_not_zero(policy: RoadwayOvertoppingPolicy) -> None:
    with pytest.raises(ValueError, match="missing or non-finite"):
        check_roadway_overtopping(Hy8Results({"flow": [10]}), "Example", policy)


@pytest.mark.parametrize("policy", list(RoadwayOvertoppingPolicy))
def test_cli_overtopping_policy(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, policy: RoadwayOvertoppingPolicy
) -> None:
    def fake_executable(exe_path: Path) -> FakeExecutable:
        executable = FakeExecutable()
        executable.exe_path = exe_path
        return executable

    monkeypatch.setattr(cli, "Hy8Executable", fake_executable)
    config_path = tmp_path / "config.json"
    config = json.loads(CONFIG_JSON)
    config["project"]["units"] = "SI"
    config_path.write_text(json.dumps(config), encoding="utf-8")
    args = [
        "build",
        "--config",
        str(config_path),
        "--output",
        str(tmp_path / "case.hy8"),
        "--run-exe",
        "fake.exe",
        "--roadway-overtopping",
        policy.value,
    ]
    if policy is RoadwayOvertoppingPolicy.ERROR:
        with pytest.raises(SystemExit, match="roadway discharge"):
            cli.main(args)
    elif policy is RoadwayOvertoppingPolicy.WARN:
        with pytest.warns(RoadwayOvertoppingWarning):
            assert cli.main(args) == 0
    else:
        with warnings.catch_warnings(record=True) as caught:
            assert cli.main(args) == 0
        assert not caught


class FakeExecutable(Hy8Executable):
    def __init__(self) -> None:
        self.exe_path = Path("fake.exe")

    def open_run_save(self, hy8_file: Path, *, check: bool = True) -> subprocess.CompletedProcess[str]:
        del check
        crossing = load_project_from_hy8(hy8_file).crossings[0]
        flows = crossing.flow.sequence()
        text = f"Dialog: Summary of Flows at Crossing - {crossing.name}\n"
        text += "Total Discharge (cms), " + ", ".join(str(q) for q in flows) + "\n"
        text += "Headwater Elevation (m), " + ", ".join(str(10 + q) for q in flows) + "\n"
        text += "Roadway Discharge (cms), " + ", ".join("1" if q > 0.5 else "0" for q in flows) + "\n"
        hy8_file.with_suffix(".rst").write_text(text, encoding="utf-8")
        return subprocess.CompletedProcess([], 0, stdout="", stderr="")


@pytest.mark.parametrize("units", [UnitSystem.SI, UnitSystem.ENGLISH])
def test_inverse_interpolation_uses_si_headwater(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, units: UnitSystem
) -> None:
    def seeds(_search: hydraulics._FlowSearch) -> list[float]:
        return [1, 3]

    def no_subdivisions(_search: hydraulics._FlowSearch, **_bounds: object) -> list[float]:
        return []

    # Force the interpolation fallback with neither seed inside tolerance.
    monkeypatch.setattr(hydraulics._FlowSearch, "initial_candidates", seeds)
    monkeypatch.setattr(hydraulics._FlowSearch, "subdivision_candidates", no_subdivisions)
    project = build_case("constant-free", units=units)
    headwater_si = 10.06 if units is UnitSystem.ENGLISH else 12.13
    requested = headwater_si / 0.3048 if units is UnitSystem.ENGLISH else headwater_si
    result = project.crossings[0].q_from_hw(
        requested,
        project=project,
        hy8=FakeExecutable(),
        workspace=tmp_path,
        roadway_overtopping=RoadwayOvertoppingPolicy.ALLOW,
    )
    assert result.computed_flow == pytest.approx(headwater_si - 10, abs=1e-7)
    assert result.computed_headwater == pytest.approx(headwater_si, abs=1e-7)
    assert result.requested_headwater == requested
    assert len(list(tmp_path.glob("*.hy8"))) == 2


@pytest.mark.parametrize("method", ["q_from_hw", "q_for_hwd"])
@pytest.mark.parametrize("project_level", [False, True])
@pytest.mark.parametrize("policy", list(RoadwayOvertoppingPolicy))
def test_inverse_policy_checks_intermediate_batch(
    tmp_path: Path,
    method: str,
    *,
    project_level: bool,
    policy: RoadwayOvertoppingPolicy,
) -> None:
    project = build_case("constant-free")
    target = project if project_level else project.crossings[0]
    run = getattr(target, method)
    value = 10.05 if method == "q_from_hw" else 0.05 / 1.2
    kwargs = {"hy8": FakeExecutable(), "workspace": tmp_path, "roadway_overtopping": policy}
    if policy is RoadwayOvertoppingPolicy.ERROR:
        with pytest.raises(RoadwayOvertoppingError):
            run(value, **kwargs)
        return
    with warnings.catch_warnings(record=True) as caught:
        returned = run(value, **kwargs)
    result = next(iter(returned.values())) if project_level else returned
    # The selected solution is dry, but its seed batch contains overtopping.
    assert result.row.roadway_discharge == 0
    assert bool(caught) is (policy is RoadwayOvertoppingPolicy.WARN)


def test_rsql_keeps_precision_and_does_not_reuse_unrelated_profile(tmp_path: Path) -> None:
    path = tmp_path / "precise.rsql"
    path.write_text(
        "Crossing: Test\nFlowProfileName: Minimum\nFlowProfileFlow: 353.146667\nHeadwaterToDepth: 2.1419823\nOvertops: true\nEndFlowProfile: 0\n",
        encoding="utf-8",
    )
    profiles = parse_rsql(path)["Test"]
    assert profiles[0].flow == pytest.approx(10)
    assert profiles[0].raw_fields["HeadwaterToDepth"] == "2.1419823"
    results = Hy8Results({"flow": [10, 20], "roadway": [0, 1]}, profiles)
    assert results.rows[0].headwater_to_depth_ratio == 2.1419823
    assert math.isnan(results.rows[0].headwater_depth)
    assert not results.rows[1].profile_fields


@pytest.mark.requires_hy8
@pytest.mark.parametrize("surface", list(RoadwaySurface))
@pytest.mark.parametrize("case", ["constant-free", "irregular-free", "submerged"])
def test_executable_saved_input_and_reader_roundtrip(tmp_path: Path, surface: RoadwaySurface, case: str) -> None:
    evidence = execute_case(build_case(case, surface), tmp_path, Hy8Executable())
    assert evidence["saved_inputs_verified"] is True
    assert evidence["report_roundtrip_equal"] is True


@pytest.mark.requires_hy8
def test_executable_single_irregular_flow_is_padded_safely(tmp_path: Path) -> None:
    crossing = build_case("irregular-free").crossings[0]
    result = crossing.hw_from_q(20, workspace=tmp_path, roadway_overtopping=RoadwayOvertoppingPolicy.ALLOW)
    assert result.row is not None
    assert result.row.roadway_discharge > 0
    assert result.computed_flow == 20
    saved = load_project_from_hy8(next(tmp_path.glob("*.hy8")))
    assert len(saved.crossings[0].flow.sequence()) == 3


@pytest.mark.requires_hy8
def test_english_helper_matches_flow_in_si_results(tmp_path: Path) -> None:
    project = build_case("constant-free", units=UnitSystem.ENGLISH)
    result = project.crossings[0].hw_from_q(
        20, project=project, workspace=tmp_path, roadway_overtopping=RoadwayOvertoppingPolicy.ALLOW
    )
    assert result.computed_flow == pytest.approx(20 * 0.028316846592, abs=0.0003)


@pytest.mark.requires_hy8
def test_gui_fixture_roundtrip_when_supplied(tmp_path: Path) -> None:
    fixture = os.environ.get("HY8_ROADWAY_GUI_FIXTURE")
    if not fixture:
        pytest.skip("GUI-created fixture pending; set HY8_ROADWAY_GUI_FIXTURE to its local path.")
    original = tmp_path / "original.hy8"
    shutil.copyfile(fixture, original)
    executable = Hy8Executable()
    project = load_project_from_hy8(original)
    assert any(
        c.roadway.shape == RoadwayShape.IRREGULAR and c.tailwater.constant_elevation >= c.roadway.crest_elevation()
        for c in project.crossings
    )
    regenerated = Hy8FileWriter(project).write(tmp_path / "regenerated.hy8")
    executable.open_run_save(original)
    executable.open_run_save(regenerated)
    assert parse_rst(original.with_suffix(".rst")) == parse_rst(regenerated.with_suffix(".rst"))
    saved_original, saved_regenerated = load_project_from_hy8(original), load_project_from_hy8(regenerated)
    for a, b in zip(saved_original.crossings, saved_regenerated.crossings, strict=True):
        assert a.roadway.to_dict() == b.roadway.to_dict()
        assert a.tailwater.constant_elevation == b.tailwater.constant_elevation


def test_floodway_gui_input_roundtrip(tmp_path: Path) -> None:
    fixture = Path(__file__).with_name("floodway.hy8")
    project = load_project_from_hy8(fixture)
    crossing = project.crossings[0]
    assert crossing.roadway.shape == RoadwayShape.IRREGULAR
    assert len(crossing.roadway.stations) == 6
    assert crossing.roadway.crest_elevation() == pytest.approx(19)
    regenerated = Hy8FileWriter(project).write(tmp_path / "floodway.hy8")
    saved = load_project_from_hy8(regenerated)
    assert saved.crossings[0].roadway.to_dict() == crossing.roadway.to_dict()
    assert saved.crossings[0].tailwater.constant_elevation == crossing.tailwater.constant_elevation


@pytest.mark.requires_hy8
@pytest.mark.parametrize("submerged", [False, True])
def test_floodway_derived_executable_roundtrip(tmp_path: Path, *, submerged: bool) -> None:
    project = load_project_from_hy8(Path(__file__).with_name("floodway.hy8"))
    crossing = project.crossings[0]
    # OpenRunSave crashes when the six roadway points exceed the flow count.
    # Retain all GUI-authored geometry; add three smaller analysis discharges.
    crossing.flow.user_values = [1, 2, 4, 8, 30, 100]
    crossing.flow.user_value_labels = [f"Q{flow}" for flow in crossing.flow.user_values]
    if submerged:
        crossing.tailwater.constant_elevation = 19.2
    original = Hy8FileWriter(project).write(tmp_path / "derived.hy8")
    executable = Hy8Executable()
    executable.open_run_save(original)
    report = parse_rst(original.with_suffix(".rst"))
    assert max(report[crossing.name]["roadway"]) > 0
    if not submerged:
        design_index = report[crossing.name]["flow"].index(100)
        # Independently displayed in the user's GUI screenshot.
        assert report[crossing.name]["headwater"][design_index] == 20.71
        assert report[crossing.name]["roadway"][design_index] == 48.05
    saved = load_project_from_hy8(original)
    regenerated = Hy8FileWriter(saved).write(tmp_path / "regenerated.hy8")
    executable.open_run_save(regenerated)
    assert report == parse_rst(regenerated.with_suffix(".rst"))
    assert load_project_from_hy8(regenerated).crossings[0].roadway.to_dict() == saved.crossings[0].roadway.to_dict()


@pytest.mark.requires_hy8
@pytest.mark.parametrize("point_count", [6, 11, 12])
@pytest.mark.parametrize("submerged", [False, True])
def test_min_design_max_irregular_executable(tmp_path: Path, point_count: int, *, submerged: bool) -> None:
    project = load_project_from_hy8(Path(__file__).with_name("floodway.hy8"))
    crossing = project.crossings[0]
    if point_count != 6:
        crossing.roadway.stations = [20 * index / (point_count - 1) for index in range(point_count)]
        crossing.roadway.elevations = [19 + abs(station - 10) * 0.1 for station in crossing.roadway.stations]
    crossing.flow = FlowDefinition(method=FlowMethod.MIN_DESIGN_MAX, minimum=8, design=30, maximum=100)
    original_flow = crossing.flow.to_dict()
    if submerged:
        crossing.tailwater.constant_elevation = 19.2
    original = Hy8FileWriter(project).write(tmp_path / "min-design-max.hy8")
    assert crossing.flow.to_dict() == original_flow
    executable = Hy8Executable()
    executable.open_run_save(original)
    report = parse_rst(original.with_suffix(".rst"))
    flows = report[crossing.name]["flow"]
    # Native mode expands to eleven flows; larger profiles use minimal padding.
    assert len(flows) == max(11, point_count) + 1
    assert all(flow in flows for flow in [8, 30, 100])
    assert max(report[crossing.name]["roadway"]) > 0
    saved = load_project_from_hy8(original)
    expected_method = FlowMethod.USER_DEFINED if point_count > 11 else FlowMethod.MIN_DESIGN_MAX
    assert saved.crossings[0].flow.method == expected_method
    if point_count > 11:
        assert saved.crossings[0].flow.user_value_labels.count(FlowDefinition.DUMMY_FLOW_LABEL) == point_count - 3
    regenerated = Hy8FileWriter(saved).write(tmp_path / "regenerated.hy8")
    executable.open_run_save(regenerated)
    assert report == parse_rst(regenerated.with_suffix(".rst"))


@pytest.mark.parametrize("point_count", [3, 6, 12, 100])
def test_irregular_padding_is_minimal_and_preserves_requests(tmp_path: Path, point_count: int) -> None:
    project = load_project_from_hy8(Path(__file__).with_name("floodway.hy8"))
    crossing = project.crossings[0]
    crossing.roadway.stations = list(range(point_count))
    crossing.roadway.elevations = [19.0] * point_count
    crossing.flow = FlowDefinition(user_values=[8, 30, 100], user_value_labels=["low", "design", "high"])
    before = crossing.flow.to_dict()
    output = Hy8FileWriter(project).write(tmp_path / "padded.hy8")
    saved = load_project_from_hy8(output).crossings[0]
    assert len(saved.flow.user_values) == point_count
    assert crossing.flow.to_dict() == before
    for flow, label in zip([8, 30, 100], ["low", "design", "high"], strict=True):
        index = min(range(point_count), key=lambda index: abs(saved.flow.user_values[index] - flow))
        assert saved.flow.user_values[index] == pytest.approx(flow, abs=2e-8)
        assert saved.flow.user_value_labels[index] == label
    assert saved.flow.user_value_labels.count(FlowDefinition.DUMMY_FLOW_LABEL) == point_count - 3


def test_irregular_padding_leaves_sufficient_flows_unchanged(tmp_path: Path) -> None:
    project = build_case("irregular-free")
    project.crossings[0].flow = FlowDefinition(user_values=[1, 2, 3, 4, 5, 6])
    saved = load_project_from_hy8(Hy8FileWriter(project).write(tmp_path / "enough.hy8"))
    assert len(saved.crossings[0].flow.user_values) == 6


@pytest.mark.parametrize("method", [FlowMethod.USER_DEFINED, FlowMethod.MIN_DESIGN_MAX])
def test_constant_flow_serialization_is_unchanged(tmp_path: Path, method: FlowMethod) -> None:
    project = build_case("constant-free")
    project.crossings[0].flow = FlowDefinition(
        method=method, minimum=8, design=30, maximum=100, user_values=[8, 30, 100]
    )
    saved = load_project_from_hy8(Hy8FileWriter(project).write(tmp_path / "constant.hy8"))
    assert saved.crossings[0].flow.method == method
    assert len(saved.crossings[0].flow.sequence()) == 3


def test_irregular_padding_rejects_precision_collapse(tmp_path: Path) -> None:
    project = build_case("irregular-free")
    project.crossings[0].flow = FlowDefinition(user_values=[1e-15])
    with pytest.raises(ValueError, match="six-decimal"):
        Hy8FileWriter(project).write(tmp_path / "too-small.hy8")


@pytest.mark.requires_hy8
@pytest.mark.parametrize("submerged", [False, True])
def test_original_six_point_geometry_runs_with_automatic_padding(tmp_path: Path, *, submerged: bool) -> None:
    project = load_project_from_hy8(Path(__file__).with_name("floodway.hy8"))
    crossing = project.crossings[0]
    original_flow = crossing.flow.to_dict()
    if submerged:
        crossing.tailwater.constant_elevation = 19.2
    file = Hy8FileWriter(project).write(tmp_path / "automatic.hy8")
    Hy8Executable().open_run_save(file)
    saved = load_project_from_hy8(file).crossings[0]
    assert len(saved.flow.user_values) == 6
    assert saved.roadway.to_dict() == crossing.roadway.to_dict()
    assert crossing.flow.to_dict() == original_flow
    report = parse_rst(file.with_suffix(".rst"))[crossing.name]
    index = report["flow"].index(100)
    assert report["headwater"][index] == (21.13 if submerged else 20.71)
    assert report["roadway"][index] == (73.05 if submerged else 48.05)
