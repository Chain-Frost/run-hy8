"""Ensure the sample comparison workflow stays in sync with hy8runner."""

from __future__ import annotations

from pathlib import Path

import pytest

from run_hy8.models.project import Hy8Project
from scripts.batch_hy8_compare import Scenario
from scripts.sample_crossing_compare import (
    build_builtin_scenarios,
    _normalized_lines,
    build_project,
    write_with_hy8runner,
    write_with_run_hy8,
)

pytestmark: pytest.MarkDecorator = pytest.mark.legacy_parity


@pytest.mark.requires_hy8
def test_sample_scenario_files_match(tmp_path: Path) -> None:
    """Write sample scenarios with both implementations and compare the hy8 output."""

    scenarios: list[Scenario] = build_builtin_scenarios()
    assert scenarios, "expected at least one deterministic scenario"

    project: Hy8Project = build_project(title="Sample Scenario Parity", scenarios=scenarios[:5])
    run_hy8_path: Path = write_with_run_hy8(project=project, directory=tmp_path / "run_hy8")
    legacy_path: Path = write_with_hy8runner(project=project, directory=tmp_path / "hy8runner", hy8_exe=None)

    assert _normalized_lines(path=run_hy8_path) == _normalized_lines(
        path=legacy_path
    ), "run-hy8 and hy8runner outputs diverged"
