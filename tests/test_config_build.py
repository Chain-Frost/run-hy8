"""End-to-end coverage for loading configs and writing HY-8 projects."""

from __future__ import annotations

from pathlib import Path

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

    assert "PROJTITLE  Sample Project" in contents
    assert 'STARTCROSSING   "Sample Crossing"' in contents
    assert "TAILWATERTYPE 6" in contents  # Constant tailwater
