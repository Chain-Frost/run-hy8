"""CLI-level tests."""

from __future__ import annotations

from pathlib import Path

from run_hy8 import Hy8Project
from run_hy8 import cli
from run_hy8.config import load_project_from_json

from .sample_data import CONFIG_JSON


def test_validate_only_mode(tmp_path: Path) -> None:
    config_path: Path = tmp_path / "project.json"
    config_path.write_text(CONFIG_JSON, encoding="utf-8")
    output_path: Path = tmp_path / "result.hy8"

    exit_code: int = cli.main(
        [
            "build",
            "--config",
            str(config_path),
            "--output",
            str(output_path),
            "--validate-only",
        ]
    )
    assert exit_code == 0
    assert not output_path.exists()

    # Sanity-check that the configuration can still be built when needed.
    project: Hy8Project = load_project_from_json(path=config_path)
    assert isinstance(project, Hy8Project)
