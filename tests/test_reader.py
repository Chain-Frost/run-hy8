"""Tests for parsing existing HY-8 files."""

from __future__ import annotations

import shutil
from pathlib import Path
from subprocess import CompletedProcess

import pytest

from run_hy8 import CulvertMaterial, UnitSystem
from run_hy8.executor import Hy8Executable
from run_hy8.models import CulvertBarrel, CulvertCrossing, Hy8Project
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
    assert first.flow.user_value_labels == ["q", "w", "e"]
    first_culvert: CulvertBarrel = first.culverts[0]
    assert first_culvert.inlet_type == 1
    assert first_culvert.inlet_edge_type == 0
    assert first_culvert.inlet_edge_type71 == 0
    assert first_culvert.improved_inlet_edge_type == 1
    last: CulvertCrossing = project.crossings[-1]
    assert last.name == "Two culverts one crossing"
    assert len(last.culverts) == 2
    assert last.culverts[0].material is CulvertMaterial.HDPE

    generated: Path = Hy8FileWriter(project=project).write(output_path=tmp_path / "round_trip.hy8")
    assert generated.exists()
    lines = generated.read_text(encoding="utf-8").splitlines()
    assert any(line.startswith("DISCHARGEXYUSER_NAME") and '"q"' in line for line in lines)
    assert any(line.startswith("ENDCULVERT") and '"Culvert 1"' in line for line in lines)
    assert any(line.startswith("ENDCROSSING") and '"Two culverts one crossing"' in line for line in lines)


def test_example_crossings_results_match(tmp_path: Path) -> None:
    hy8_path: Path = Hy8Executable.default_path()
    if not hy8_path.exists():
        pytest.fail(f"HY-8 executable not found at {hy8_path}. Update HY8_PATH.txt or HY8_EXE.")

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
