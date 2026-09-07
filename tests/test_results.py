"""Focused tests for parsing HY-8 result reports."""

from __future__ import annotations

import math
from pathlib import Path

import pytest

from run_hy8 import Hy8CulvertResult
from run_hy8.results import Hy8CulvertSeries, Hy8Results, Hy8Series, parse_rst

MULTI_CULVERT_RST: str = """\
Culvert: 0
Dialog: Summary of Flows at Crossing - Two culverts
Headwater Elevation (m), 1.12, 5.14
Total Discharge (cms), 8.00, 30.00
Roadway Discharge (cms), 0.00, 0.00
Iterations, 7, 15

Culvert: 0
Dialog: Culvert Summary Table - Culvert 1
Culvert Discharge (cms), 7.98, 28.85
Inlet Control Depth(m), 0.92, 4.94
Outlet Control Depth(m), 0.64, 4.00
Flow Type, 5-S2n, 6-FFc
Outlet Velocity (m/s), 2.75, 5.67

Culvert: 1
Dialog: Culvert Summary Table - Culvert 2
Culvert Discharge (cms), 0.02, 1.15
Inlet Control Depth(m), 0.12, 3.39**
Outlet Control Depth(m), 0.0*, 4.14
Flow Type, 1-S2n, 6-FFc
Outlet Velocity (m/s), 1.06, 4.06

Culvert: 0
Dialog: Water Surface Profile Table - Culvert 1
Length Full (m), 0.00, 25.00
Length Free (m) , 25.00, 0.00

Culvert: 1
Dialog: Water Surface Profile Table - Culvert 2
Length Full (m), 0.00, 29.52
Length Free (m) , 29.50, 0.00

EndCrossing
"""


def test_parse_rst_exposes_diagnostics_for_each_culvert(tmp_path: Path) -> None:
    rst_path: Path = tmp_path / "multi.rst"
    rst_path.write_text(MULTI_CULVERT_RST, encoding="utf-8")

    parsed: dict[str, Hy8Series] = parse_rst(rst_path)
    crossing: Hy8Series = parsed["Two culverts"]
    culverts: list[Hy8CulvertSeries] = crossing["culverts"]

    assert crossing["flow"] == [8.0, 30.0]
    assert crossing["headwater"] == [1.12, 5.14]
    assert len(culverts) == 2
    assert culverts[0]["name"] == "Culvert 1"
    assert culverts[0]["inlet_control_depth"] == [0.92, 4.94]
    assert culverts[0]["full_length"] == [0.0, 25.0]
    assert culverts[0]["free_length"] == [25.0, 0.0]
    assert culverts[1]["index"] == 1
    assert culverts[1]["outlet_control_depth"] == [0.0, 4.14]
    assert culverts[1]["outlet_control_depth_qualifier"] == ["*", ""]
    assert culverts[1]["inlet_control_depth_qualifier"] == ["", "**"]


def test_hy8_results_adds_per_flow_culvert_diagnostics(tmp_path: Path) -> None:
    rst_path: Path = tmp_path / "multi.rst"
    rst_path.write_text(MULTI_CULVERT_RST, encoding="utf-8")
    crossing: Hy8Series = parse_rst(rst_path)["Two culverts"]

    rows = Hy8Results(crossing).rows

    assert len(rows) == 2
    assert len(rows[0].culverts) == 2
    assert isinstance(rows[0].culverts[0], Hy8CulvertResult)
    assert rows[0].culverts[0].discharge == pytest.approx(7.98)
    assert rows[0].culverts[0].free_length == pytest.approx(25.0)
    assert rows[0].culverts[1].outlet_control_depth == pytest.approx(0.0)
    assert rows[0].culverts[1].outlet_control_depth_qualifier == "*"
    assert rows[1].culverts[1].inlet_control_depth == pytest.approx(3.39)
    assert rows[1].culverts[1].inlet_control_depth_qualifier == "**"
    assert rows[1].culverts[1].full_length == pytest.approx(29.52)


def test_missing_culvert_columns_are_nan(tmp_path: Path) -> None:
    rst_path: Path = tmp_path / "partial.rst"
    rst_path.write_text(
        MULTI_CULVERT_RST.replace("Length Full (m), 0.00, 29.52", "Length Full (m), 0.00"),
        encoding="utf-8",
    )

    row = Hy8Results(parse_rst(rst_path)["Two culverts"]).rows[1]

    assert math.isnan(row.culverts[1].full_length)


def test_rst_diagnostics_accept_english_unit_labels(tmp_path: Path) -> None:
    rst_path: Path = tmp_path / "english.rst"
    english_report: str = MULTI_CULVERT_RST.replace("(cms)", "(cfs)").replace("(m/s)", "(ft/s)").replace("(m)", "(ft)")
    rst_path.write_text(english_report, encoding="utf-8")

    row = Hy8Results(parse_rst(rst_path)["Two culverts"]).rows[0]

    assert row.flow == pytest.approx(8.0)
    assert row.culverts[0].inlet_control_depth == pytest.approx(0.92)
    assert row.culverts[0].free_length == pytest.approx(25.0)
