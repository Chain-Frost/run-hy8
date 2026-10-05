"""Execute small roadway input-parity cases and retain reproducible evidence."""

from __future__ import annotations

import argparse
import csv
import hashlib
import importlib.metadata
import json
import platform
import shutil
import subprocess
import sys
import tomllib
from dataclasses import asdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

import run_hy8
from run_hy8 import (
    CircularConcreteInlet,
    CulvertBarrel,
    CulvertCrossing,
    CulvertMaterial,
    FlowDefinition,
    FlowMethod,
    Hy8Executable,
    Hy8FileWriter,
    Hy8Project,
    Hy8Results,
    RoadwayOvertoppingPolicy,
    RoadwayProfile,
    RoadwayShape,
    RoadwaySurface,
    TailwaterDefinition,
    UnitSystem,
    check_roadway_overtopping,
    load_project_from_hy8,
    parse_rsql,
    parse_rst,
)
from run_hy8.units import weir_coefficient_to_si


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def build_case(
    case: str,
    surface: RoadwaySurface = RoadwaySurface.USER_DEFINED,
    coefficient: float = 1.6,
    units: UnitSystem = UnitSystem.SI,
) -> Hy8Project:
    irregular = case == "irregular-free"
    roadway = RoadwayProfile(
        width=10,
        shape=RoadwayShape.IRREGULAR if irregular else RoadwayShape.CONSTANT,
        surface=surface,
        discharge_coefficient=coefficient,
        stations=[0, 10, 20] if irregular else [0, 20],
        elevations=[12.5, 12, 12.5] if irregular else [12, 12],
    )
    crossing = CulvertCrossing(
        name="Roadway",
        flow=FlowDefinition(method=FlowMethod.USER_DEFINED, user_values=[2, 10, 20]),
        tailwater=TailwaterDefinition(constant_elevation=12.9 if case == "submerged" else 9.7, invert_elevation=9.7),
        roadway=roadway,
    )
    crossing.add_barrel(
        CulvertBarrel(
            name="Concrete",
            span=1.2,
            rise=1.2,
            material=CulvertMaterial.CONCRETE,
            inlet_configuration=CircularConcreteInlet.SQUARE_EDGE_WITH_HEADWALL,
            inlet_invert_elevation=10,
            outlet_invert_elevation=9.7,
            outlet_invert_station=30,
            manning_n_top=0.012,
            manning_n_bottom=0.012,
        )
    )
    return Hy8Project(title="Roadway input contract validation", units=units, crossings=[crossing])


def verify_saved_inputs(requested: Hy8Project, saved: Hy8Project) -> None:
    # Six-decimal English cards have up to 0.1524 micrometres of length rounding.
    expected, actual = requested.crossings[0], saved.crossings[0]
    if expected.roadway.shape != actual.roadway.shape or expected.roadway.surface != actual.roadway.surface:
        msg = "HY-8 changed the roadway shape or surface mode."
        raise ValueError(msg)
    for label, before, after, tolerance in [
        ("stations", expected.roadway.stations, actual.roadway.stations, 4e-7),
        ("elevations", expected.roadway.elevations, actual.roadway.elevations, 4e-7),
        ("width", [expected.roadway.width], [actual.roadway.width], 4e-7),
        ("tailwater", [expected.tailwater.constant_elevation], [actual.tailwater.constant_elevation], 4e-7),
        ("tailwater invert", [expected.tailwater.invert_elevation], [actual.tailwater.invert_elevation], 4e-7),
        ("flows", expected.flow.sequence(), actual.flow.sequence(), 1e-6),
    ]:
        if len(before) != len(after) or any(abs(a - b) > tolerance for a, b in zip(before, after, strict=True)):
            msg = f"HY-8 changed {label}: {before} -> {after}"
            raise ValueError(msg)
    before_c, after_c = expected.roadway.discharge_coefficient, actual.roadway.discharge_coefficient
    if before_c is None or after_c is None or abs(before_c - after_c) > 3e-7:
        msg = f"HY-8 changed WEIRCOEFF: {before_c} -> {after_c}"
        raise ValueError(msg)
    before_barrel, after_barrel = expected.culverts[0], actual.culverts[0]
    if before_barrel.inlet_configuration != after_barrel.inlet_configuration:
        msg = "HY-8 changed the inlet configuration."
        raise ValueError(msg)
    for name in [
        "span",
        "rise",
        "inlet_invert_station",
        "outlet_invert_station",
        "inlet_invert_elevation",
        "outlet_invert_elevation",
    ]:
        if abs(getattr(before_barrel, name) - getattr(after_barrel, name)) > 4e-7:
            msg = f"HY-8 changed culvert {name}."
            raise ValueError(msg)
    if before_barrel.number_of_barrels != after_barrel.number_of_barrels:
        msg = "HY-8 changed the barrel count."
        raise ValueError(msg)
    if before_barrel.resolved_manning_values() != after_barrel.resolved_manning_values():
        msg = "HY-8 changed Manning roughness."
        raise ValueError(msg)


def execute_case(
    project: Hy8Project,
    output: Path,
    executable: Hy8Executable,
    display_units: UnitSystem = UnitSystem.SI,
) -> dict[str, object]:
    output.mkdir(parents=True, exist_ok=True)
    path = Hy8FileWriter(project).write(output / "case.hy8")
    set_display_units(path, display_units)
    shutil.copyfile(path, output / "authored.hy8")
    executable.open_run_save(path)
    saved = load_project_from_hy8(path)
    verify_saved_inputs(project, saved)
    entry = parse_rst(path.with_suffix(".rst"))["Roadway"]
    profiles = parse_rsql(path.with_suffix(".rsql")).get("Roadway", [])
    results = Hy8Results(entry, profiles)
    check_roadway_overtopping(results, "Roadway", RoadwayOvertoppingPolicy.ALLOW)
    roundtrip = Hy8FileWriter(saved).write(output / "roundtrip.hy8")
    set_display_units(roundtrip, display_units)
    executable.open_run_save(roundtrip)
    verify_saved_inputs(saved, load_project_from_hy8(roundtrip))
    if parse_rst(roundtrip.with_suffix(".rst")) != {"Roadway": entry}:
        msg = "Reader/writer round-trip changed the executable report."
        raise ValueError(msg)
    row = results.nearest(20)
    if row is None:
        msg = "Missing requested discharge result."
        raise ValueError(msg)
    evidence: dict[str, object] = {
        "classification": "adapter input parity; no independent hydraulic comparison",
        "saved_inputs_verified": True,
        "report_roundtrip_equal": True,
        "display_units": display_units.name,
        "requested": project.to_dict(),
        "saved": saved.to_dict(),
        "requested_20_result": asdict(row),
        "profiles": [asdict(profile) for profile in profiles],
        "artifacts": {p.name: sha256(p) for p in output.iterdir() if p.suffix in {".hy8", ".rst", ".rsql", ".plt"}},
    }
    (output / "evidence.json").write_text(json.dumps(evidence, indent=2, allow_nan=True), encoding="utf-8")
    return evidence


def set_display_units(path: Path, units: UnitSystem) -> None:
    # The experiment varies only the display flag, leaving every English input
    # card identical. Existing EN-authored models use English geometry/flows.
    lines = path.read_text(encoding="utf-8").splitlines()
    lines = [f"UNITS                {units.project_flag}" if line.startswith("UNITS ") else line for line in lines]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def source_identity(executable: Hy8Executable) -> dict[str, object]:
    package = Path(run_hy8.__file__).resolve().parent
    git = shutil.which("git")
    if git is None:
        msg = "Git is required to record source identity."
        raise FileNotFoundError(msg)
    return {
        "python": platform.python_version(),
        "platform": platform.platform(),
        "package_path": str(package),
        "distribution_version": importlib.metadata.version("run-hy8"),
        "source_project_version": tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))["project"][
            "version"
        ],
        "git_head": subprocess.check_output([git, "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),  # noqa: S603 -- Fixed read-only Git arguments.
        "git_status": subprocess.check_output([git, "status", "--porcelain"], cwd=ROOT, text=True).splitlines(),  # noqa: S603 -- Fixed read-only Git arguments.
        "source_sha256": {str(p.relative_to(package)): sha256(p) for p in sorted(package.rglob("*.py"))},
        "hy8_sha256": sha256(executable.exe_path),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--case", choices=["constant-free", "irregular-free", "submerged", "all"], default="all")
    parser.add_argument("--surface", choices=["paved", "gravel", "user-defined"], default="user-defined")
    parser.add_argument(
        "--coefficient", type=float, default=1.6, help="SI coefficient; inactive in paved/gravel modes."
    )
    parser.add_argument("--units", choices=["si", "english"], default="si")
    parser.add_argument("--output", type=Path, default=ROOT / "validation_artifacts" / "roadway-validation")
    parser.add_argument("--exe", type=Path, default=Hy8Executable.default_path())
    parser.add_argument("--matrix", action="store_true", help="Run the retained 24-case input/unit/coefficient matrix.")
    parser.add_argument("--csv", type=Path, help="Write compact, portable adapter evidence to this CSV.")
    args = parser.parse_args()
    executable = Hy8Executable(args.exe)
    surface = RoadwaySurface[args.surface.upper().replace("-", "_")]
    units = UnitSystem.SI if args.units == "si" else UnitSystem.ENGLISH
    cases = ["constant-free", "irregular-free", "submerged"] if args.case == "all" else [args.case]
    specifications = [(case, surface, args.coefficient, units) for case in cases]
    if args.matrix:
        specifications = (
            [
                (case, mode, 1.6, UnitSystem.SI)
                for case in ["constant-free", "irregular-free", "submerged"]
                for mode in RoadwaySurface
            ]
            + [
                (case, RoadwaySurface.USER_DEFINED, 1.6, UnitSystem.ENGLISH)
                for case in ["constant-free", "irregular-free", "submerged"]
            ]
            + [
                (case, mode, weir_coefficient_to_si(coefficient), UnitSystem.SI)
                for case in ["constant-free", "submerged"]
                for mode in RoadwaySurface
                for coefficient in [2.5, 3.095]
            ]
        )
    records: dict[str, object] = {}
    compact: list[dict[str, object]] = []
    for case, mode, coefficient, display in specifications:
        key = f"{case}-{mode.name.lower()}-{display.name.lower()}-{coefficient:.9g}"
        project = build_case(case, mode, coefficient)
        record = execute_case(project, args.output / key, executable, display)
        records[key] = record
        row = record["requested_20_result"]
        compact.append(
            {
                "case": case,
                "surface": mode.name,
                "coefficient_si": coefficient,
                "display_units": display.name,
                "tailwater_m": project.crossings[0].tailwater.constant_elevation,
                "crest_points": len(project.crossings[0].roadway.stations),
                "crest_extent_m": 20,
                "top_width_m": 10,
                "requested_q_cms": 20,
                "reported_q_cms": row["flow"],
                "headwater_m": row["headwater_elevation"],
                "roadway_q_cms": row["roadway_discharge"],
                "culvert_q_cms": row["culverts"][0]["discharge"],
                "outlet_velocity_ms": row["velocity"],
                "flow_type": row["flow_type"],
                "saved_inputs_verified": True,
                "report_roundtrip_equal": True,
                "rst_sha256": record["artifacts"]["case.rst"],
                "rsql_sha256": record["artifacts"]["case.rsql"],
                "saved_hy8_sha256": record["artifacts"]["case.hy8"],
                "classification": record["classification"],
            }
        )
        print(f"{key}: saved inputs verified; reader/writer executable report equivalent")
    (args.output / "identity.json").write_text(json.dumps(source_identity(executable), indent=2), encoding="utf-8")
    (args.output / "summary.json").write_text(json.dumps(records, indent=2, allow_nan=True), encoding="utf-8")
    if args.csv:
        args.csv.parent.mkdir(parents=True, exist_ok=True)
        with args.csv.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=list(compact[0]))
            writer.writeheader()
            writer.writerows(compact)


if __name__ == "__main__":
    main()
