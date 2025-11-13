"""Targeted validation coverage for the run_hy8 domain model."""

from __future__ import annotations
from pathlib import Path

import pytest

from run_hy8 import TailwaterType
from run_hy8.models import FlowDefinition, FlowMethod, Hy8Project
from run_hy8.writer import Hy8FileWriter

from .sample_data import build_sample_project


def test_tailwater_must_be_constant(tmp_path: Path) -> None:
    project: Hy8Project = build_sample_project()
    project.crossings[0].tailwater.type = TailwaterType.RECTANGULAR

    errors: list[str] = project.crossings[0].validate("Sample Crossing: ")
    assert any("not supported" in message for message in errors)

    with pytest.raises(ValueError, match="Tailwater type"):
        Hy8FileWriter(project=project).write(tmp_path / "invalid.hy8")


def test_tailwater_cannot_reach_roadway() -> None:
    project: Hy8Project = build_sample_project()
    project.crossings[0].tailwater.constant_elevation = 102.5  # higher than crest (101.5)
    errors: list[str] = project.crossings[0].validate("Sample Crossing: ")
    assert any("roadway crest" in message for message in errors)


def test_user_defined_flows_must_increase() -> None:
    flow = FlowDefinition(method=FlowMethod.USER_DEFINED, user_values=[10.0, 5.0])
    errors: list[str] = flow.validate("Flow: ")
    assert any("increasing" in message for message in errors)
