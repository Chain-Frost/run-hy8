"""Tests for parsing existing HY-8 files."""

from __future__ import annotations

import os
import shutil
from pathlib import Path
from subprocess import CompletedProcess

import pytest

from run_hy8 import CulvertMaterial, UnitSystem
from run_hy8.executor import Hy8Executable
from run_hy8.models import CulvertCrossing, Hy8Project
from run_hy8.reader import load_project_from_hy8
from run_hy8.results import FlowProfile, Hy8Series, parse_rsql, parse_rst
from run_hy8.writer import Hy8FileWriter

EXAMPLE_FILE: Path = Path(__file__).resolve().parent / "example_crossings.hy8"


def test_loads_example_crossings(tmp_path: Path) -> None:
    project: Hy8Project = load_project_from_hy8(path=EXAMPLE_FILE)

    assert project.units is UnitSystem.SI
    assert len(project.crossings) == 7
    first: CulvertCrossing = project.crossings[0]
    assert first.name == "HDPE 900x11"
    assert first.flow.sequence() == pytest.approx(  # pyright: ignore[reportUnknownMemberType]
        expected=[282.517334, 317.832, 353.146667]
    )
    last: CulvertCrossing = project.crossings[-1]
    assert last.name == "Two culverts one crossing"
    assert len(last.culverts) == 2
    assert last.culverts[0].material is CulvertMaterial.HDPE

    generated: Path = Hy8FileWriter(project=project).write(output_path=tmp_path / "round_trip.hy8")
    assert generated.exists()


@pytest.mark.skipif(condition=os.name != "nt", reason="HY-8 automation is only available on Windows.")
def test_example_crossings_results_match(tmp_path: Path) -> None:
    hy8_exe_env: str | None = os.environ.get("HY8_EXE") or os.environ.get("HY8_EXECUTABLE")
    if not hy8_exe_env:
        pytest.skip(reason="Set HY8_EXE to compare HY-8 outputs.")
    hy8_path = Path(hy8_exe_env)
    if not hy8_path.exists():
        pytest.skip(reason=f"HY-8 executable not found: {hy8_path}")

    project: Hy8Project = load_project_from_hy8(EXAMPLE_FILE)
    regenerated: Path = Hy8FileWriter(project=project).write(output_path=tmp_path / "regenerated.hy8")
    original_copy: Path = tmp_path / "original.hy8"
    shutil.copy(src=EXAMPLE_FILE, dst=original_copy)

    executable = Hy8Executable(exe_path=hy8_path)

    _run_hy8_and_wait(executable=executable, hy8_file=original_copy)
    _run_hy8_and_wait(executable=executable, hy8_file=regenerated)

    original_rst: dict[str, Hy8Series] = parse_rst(path=original_copy.with_suffix(suffix=".rst"))
    regenerated_rst: dict[str, Hy8Series] = parse_rst(path=regenerated.with_suffix(suffix=".rst"))
    assert original_rst == regenerated_rst

    original_rsql: dict[str, list[FlowProfile]] = parse_rsql(path=original_copy.with_suffix(suffix=".rsql"))
    regenerated_rsql: dict[str, list[FlowProfile]] = parse_rsql(path=regenerated.with_suffix(suffix=".rsql"))
    assert original_rsql == regenerated_rsql


def _run_hy8_and_wait(executable: Hy8Executable, hy8_file: Path) -> None:
    """Execute HY-8 and ensure the results files were created."""
    completed: CompletedProcess[str] = executable.open_run_save(hy8_file=hy8_file)
    if completed.returncode != 0:  # pragma: no cover - defensive guard
        raise RuntimeError(f"HY-8 execution failed: {completed.stderr.strip()}")
