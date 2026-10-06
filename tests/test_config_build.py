"""End-to-end coverage for loading configs and writing HY-8 projects."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from run_hy8 import (
    CircularCorrugatedSteelInlet,
    CulvertShape,
    EllipticalConcreteInlet,
    LegacyInletConfigurationWarning,
)
from run_hy8.config import load_project_from_json
from run_hy8.models import Hy8Project
from run_hy8.writer import Hy8FileWriter

from .sample_data import CONFIG_JSON


def test_build_from_json_config(tmp_path: Path) -> None:
    config_path: Path = tmp_path / "project.json"
    config_path.write_text(data=CONFIG_JSON, encoding="utf-8")

    project: Hy8Project = load_project_from_json(path=config_path)
    hy8_path: Path = Hy8FileWriter(project=project).write(output_path=tmp_path / "sample.hy8")
    contents: str = hy8_path.read_text(encoding="utf-8")
    lines: list[str] = contents.splitlines()

    assert any(line.startswith("PROJTITLE") and "Sample Project" in line for line in lines)
    assert any(line.startswith("STARTCROSSING") and '"Sample Crossing"' in line for line in lines)
    assert any(line.startswith("TAILWATERTYPE") and "6" in line for line in lines)  # Constant tailwater


def test_build_concrete_ellipse_from_json(tmp_path: Path) -> None:
    config: dict[str, Any] = json.loads(CONFIG_JSON)
    culvert = config["crossings"][0]["culverts"][0]
    culvert["shape"] = "elliptical"
    culvert["material"] = "concrete"
    culvert["span"] = 1.5
    culvert["rise"] = 0.95
    culvert["inlet_configuration"] = "grooved-edge-with-headwall"
    config_path = tmp_path / "ellipse.json"
    config_path.write_text(json.dumps(config), encoding="utf-8")

    project = load_project_from_json(config_path)
    barrel = project.crossings[0].culverts[0]

    assert barrel.shape is CulvertShape.ELLIPTICAL
    assert barrel.inlet_configuration is EllipticalConcreteInlet.GROOVED_EDGE_WITH_HEADWALL
    assert barrel.manning_values() == (0.012, 0.012)

    output = Hy8FileWriter(project).write(tmp_path / "ellipse.hy8")
    lines = output.read_text(encoding="utf-8").splitlines()
    assert any(line.startswith("CULVERTSHAPE") and line.split()[-1] == "3" for line in lines)
    assert any(line.startswith("INLETEDGETYPE71") and line.split()[-1] == "1" for line in lines)


def test_config_rejects_min_max_increment(tmp_path: Path) -> None:
    config: dict[str, Any] = json.loads(CONFIG_JSON)
    config["crossings"][0]["flow"]["method"] = "min-max-increment"
    config_path: Path = tmp_path / "invalid.json"
    config_path.write_text(json.dumps(config), encoding="utf-8")

    with pytest.raises(expected_exception=ValueError, match="not supported"):
        load_project_from_json(path=config_path)


def test_legacy_inlet_config_warns(tmp_path: Path) -> None:
    config: dict[str, Any] = json.loads(CONFIG_JSON)
    culvert = config["crossings"][0]["culverts"][0]
    culvert["shape"] = "circle"
    culvert["material"] = "corrugated steel"
    culvert.pop("inlet_configuration")
    culvert["inlet_edge_type"] = "THIN_EDGE_PROJECTING"
    config_path = tmp_path / "legacy-inlet.json"
    config_path.write_text(json.dumps(config), encoding="utf-8")

    with pytest.warns(LegacyInletConfigurationWarning):
        project = load_project_from_json(config_path)

    assert project.crossings[0].culverts[0].inlet_configuration is CircularCorrugatedSteelInlet.THIN_EDGE_PROJECTING
