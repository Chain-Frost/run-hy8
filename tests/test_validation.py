"""Targeted validation coverage for the run_hy8 domain model."""

from __future__ import annotations
from pathlib import Path

import pytest

from run_hy8.classes_references import ValidationError
from run_hy8 import TailwaterType
from run_hy8.models import FlowDefinition, FlowMethod, Hy8Project
from run_hy8.writer import Hy8FileWriter

from .sample_data import build_sample_project


def test_tailwater_must_be_constant(tmp_path: Path) -> None:
    project: Hy8Project = build_sample_project()
    project.crossings[0].tailwater.tw_type = TailwaterType.RECTANGULAR

    errors: list[str] = project.crossings[0].validate("Sample Crossing: ")
    assert any("not supported" in message for message in errors)

    with pytest.raises(ValueError, match="Tailwater type"):
        Hy8FileWriter(project=project).write(tmp_path / "invalid.hy8")


def test_tailwater_cannot_reach_roadway() -> None:
    project: Hy8Project = build_sample_project()
    project.crossings[0].tailwater.constant_elevation = 102.5  # higher than crest (101.5)
    errors: list[str] = project.crossings[0].validate("Sample Crossing: ")
    assert any("roadway crest" in message for message in errors)


def test_assert_valid_only_raises_for_invalid_models() -> None:
    project: Hy8Project = build_sample_project()
    project.assert_valid()

    project.crossings.clear()
    with pytest.raises(ValidationError, match="At least one crossing"):
        project.assert_valid()


def test_user_defined_flows_must_increase() -> None:
    flow = FlowDefinition(method=FlowMethod.USER_DEFINED, user_values=[10.0, 5.0])
    errors: list[str] = flow.validate("Flow: ")
    assert any("increasing" in message for message in errors)


def test_user_defined_flows_require_at_least_one_value() -> None:
    flow = FlowDefinition(method=FlowMethod.USER_DEFINED, user_values=[])
    errors: list[str] = flow.validate("Flow: ")
    assert any("at least one" in message for message in errors)


def test_single_user_defined_flow_is_allowed() -> None:
    flow = FlowDefinition(method=FlowMethod.USER_DEFINED, user_values=[10.0])
    assert flow.validate("Flow: ") == []


def test_min_design_max_requires_three_flows() -> None:
    flow = FlowDefinition(method=FlowMethod.MIN_DESIGN_MAX, user_values=[1.0, 2.0])
    errors: list[str] = flow.validate("Flow: ")
    assert any("exactly three flows" in message for message in errors)
