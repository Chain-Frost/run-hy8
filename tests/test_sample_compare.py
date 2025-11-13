"""Ensure the sample comparison workflow stays in sync with hy8runner."""

from __future__ import annotations

from pathlib import Path

from scripts.sample_crossing_compare import (
    _normalized_lines,
    build_project,
    load_scenarios_from_data_file,
    write_with_hy8runner,
    write_with_run_hy8,
)


SCENARIO_FILE = Path(__file__).resolve().parents[1] / "data" / "sample_scenarios.json"


def test_sample_scenario_files_match(tmp_path: Path) -> None:
    """Write sample scenarios with both implementations and compare the hy8 output."""

    scenarios, skipped = load_scenarios_from_data_file(SCENARIO_FILE, skip_zero_flow=True)
    assert scenarios, "expected at least one deterministic scenario"
    assert skipped == 0

    project = build_project("Sample Scenario Parity", scenarios[:5])
    run_hy8_path = write_with_run_hy8(project, tmp_path / "run_hy8")
    legacy_path = write_with_hy8runner(project, tmp_path / "hy8runner", hy8_exe=None)

    assert _normalized_lines(run_hy8_path) == _normalized_lines(
        legacy_path
    ), "run-hy8 and hy8runner outputs diverged"
