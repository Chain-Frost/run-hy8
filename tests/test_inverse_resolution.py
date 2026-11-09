"""Inverse acceptance must distinguish a tolerance match from resolved flow."""

from __future__ import annotations

import hashlib
from pathlib import Path

import pytest

from run_hy8 import CulvertBarrel, CulvertCrossing, hydraulics, load_project_from_hy8
from run_hy8.hydraulics import FlowSearchError, _FlowSearch
from run_hy8.results import Hy8ResultRow, Hy8Results


def search_with_samples(target: float, pairs: list[tuple[float, float]]) -> _FlowSearch:
    search = _FlowSearch(target_headwater=target, simple_flow=1.0)
    for flow, headwater in pairs:
        search.record(flow, Hy8ResultRow(flow=flow, headwater_elevation=headwater))
    return search


def test_first_seed_is_not_a_resolved_inverse() -> None:
    search = search_with_samples(43.5636, [(0.05, 43.56)])
    assert search.exact_match() is None
    search.record(0.10, Hy8ResultRow(flow=0.10, headwater_elevation=43.56))
    with pytest.raises(FlowSearchError, match="report resolution") as caught:
        search.exact_match()
    assert caught.value.best_sample is not None
    assert caught.value.target_headwater == 43.5636


@pytest.mark.parametrize("headwaters", [[43.56, 43.56, 43.56], [43.55, 43.56, 43.56, 43.58]])
def test_flat_or_rounded_target_series_fails_closed(headwaters: list[float]) -> None:
    search = search_with_samples(43.5636, list(enumerate(headwaters, start=1)))
    with pytest.raises(FlowSearchError, match="report resolution"):
        search.exact_match()


def test_tolerance_match_requires_both_sides_outside_tolerance() -> None:
    search = search_with_samples(10.0, [(1.0, 10.0), (2.0, 10.5)])
    assert search.exact_match() is None
    search.record(0.5, Hy8ResultRow(flow=0.5, headwater_elevation=9.5))
    match = search.exact_match()
    assert match is not None
    assert match.flow == 1.0


def test_resolvable_case_selects_closest_sample_instead_of_first() -> None:
    search = search_with_samples(10.0, [(0.5, 9.5), (0.99, 9.991), (1.0, 10.0), (2.0, 10.5)])
    match = search.exact_match()
    assert match is not None
    assert match.flow == 1.0


def test_next_guess_expands_upper_endpoint_beyond_tolerance_band() -> None:
    search = search_with_samples(10.005, [(0.05, 9.97), (1.0, 9.99), (2.0, 10.01)])
    assert search.bracket() is None
    # Q=2 is above the target but still inside the 0.01 m acceptance band.
    # Bisecting to 1.5 would not establish the required upper endpoint.
    assert search.next_guess() == pytest.approx(4.0)
    search.record(4.0, Hy8ResultRow(flow=4.0, headwater_elevation=10.05))
    match = search.exact_match()
    assert match is not None
    assert match.flow == pytest.approx(2.0)


def test_next_guess_expands_lower_endpoint_beyond_tolerance_band() -> None:
    search = search_with_samples(10.005, [(1.0, 10.0), (2.0, 10.04)])
    assert search.bracket() is None
    # Q=1 is below the target but still inside the acceptance band.
    assert search.next_guess() == pytest.approx(0.5)
    search.record(0.5, Hy8ResultRow(flow=0.5, headwater_elevation=9.97))
    match = search.exact_match()
    assert match is not None
    assert match.flow == pytest.approx(1.0)


def test_public_search_expands_before_bisecting_near_target_signs(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    evaluated: list[float] = []

    def fake_run(**kwargs: object) -> Hy8Results:
        project = kwargs["project"]
        assert isinstance(project, hydraulics.Hy8Project)
        flows = project.crossings[0].flow.sequence()
        evaluated.extend(flows)
        heads = [round(9.97 + 0.02 * flow, 2) for flow in flows]
        return Hy8Results({"flow": flows, "headwater": heads})

    monkeypatch.setattr(hydraulics, "_write_and_run", fake_run)
    executable = tmp_path / "unused.exe"
    executable.touch()
    crossing = CulvertCrossing(name="Synthetic", culverts=[CulvertBarrel()])
    result = crossing.q_from_hw(10.005, q_hint=1.0, hy8=executable, workspace=tmp_path)
    assert result.computed_flow == pytest.approx(2.0)
    assert 4.0 in evaluated
    assert len(evaluated) == len(set(evaluated))
    assert len(evaluated) <= hydraulics.FLOW_SEARCH_MAX_RUNS


def test_non_monotonic_series_is_not_interpolated() -> None:
    search = search_with_samples(10.0, [(0.5, 9.5), (1.0, 10.0), (2.0, 9.9), (3.0, 11.0)])
    with pytest.raises(FlowSearchError, match="non-monotonic"):
        search.exact_match()


@pytest.mark.parametrize("curve", ["flat", "jump", "unbracketed", "smooth"])
def test_public_search_is_bounded_and_preserves_resolvable_case(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, curve: str
) -> None:
    evaluated: list[float] = []

    def fake_run(**kwargs: object) -> Hy8Results:
        project = kwargs["project"]
        assert isinstance(project, hydraulics.Hy8Project)
        flows = project.crossings[0].flow.sequence()
        evaluated.extend(flows)
        if curve == "flat":
            heads = [10.0] * len(flows)
        elif curve == "jump":
            heads = [9.0 if q < 1.0 else 11.0 for q in flows]
        elif curve == "unbracketed":
            heads = [11.0 + q for q in flows]
        else:
            heads = [9.0 + q for q in flows]
        return Hy8Results({"flow": flows, "headwater": heads})

    monkeypatch.setattr(hydraulics, "_write_and_run", fake_run)
    # Execution is mocked, so constructor validation must not require native HY-8.
    executable = tmp_path / "unused.exe"
    executable.touch()
    crossing = CulvertCrossing(name="Synthetic", culverts=[CulvertBarrel()])
    if curve == "smooth":
        result = crossing.q_from_hw(10.0, q_hint=1.0, hy8=executable, workspace=tmp_path)
        assert result.computed_flow == pytest.approx(1.0)
    else:
        with pytest.raises(FlowSearchError):
            crossing.q_from_hw(10.0, q_hint=1.0, hy8=executable, workspace=tmp_path)
    assert len(evaluated) <= hydraulics.FLOW_SEARCH_MAX_RUNS
    assert len(evaluated) == len(set(evaluated))


@pytest.mark.requires_hy8
def test_native_assumed_eg11_resolution(tmp_path: Path) -> None:
    executable = Path("C:/Program Files/HY-8 8.00/HY864.exe")
    if not executable.exists():
        pytest.skip("Requires HY-8 8.0.1.2 on Windows")
    assert hashlib.sha256(executable.read_bytes()).hexdigest() == (
        "0b1c5e7fb6b48be9c675b5486ae9a84346f436c5c649aa5ed09a1552267ee806"
    )
    source = Path(__file__).parents[1] / "reference_docs/validation/2026-11-09-inverse-resolution/input.hy8"
    assert hashlib.sha256(source.read_bytes()).hexdigest() == (
        "b71007d8dc863703fd7177d05017aae9e1c2e101be3f416a02ccf02398a872cf"
    )
    project = load_project_from_hy8(source)
    crossing = project.crossings[0]
    heads = [
        crossing.hw_from_q(
            q, project=project, hy8=executable, workspace=tmp_path / f"q-{q}", keep_files=True
        ).computed_headwater
        for q in (0.05, 0.10, 0.149540795, 0.20)
    ]
    assert heads == [43.56, 43.56, 43.56, 43.57]
    with pytest.raises(FlowSearchError, match="report resolution"):
        crossing.q_from_hw(
            43.5636, q_hint=1.0, project=project, hy8=executable, workspace=tmp_path / "inverse", keep_files=True
        )
