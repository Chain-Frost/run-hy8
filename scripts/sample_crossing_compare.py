"""Generate sample culvert crossings and compare run-hy8 with the legacy hy8runner."""

from __future__ import annotations

import argparse
import csv
import difflib
import json
import math
import re
import shutil
from subprocess import CompletedProcess
import sys
from pathlib import Path
from typing import Any, Iterable, Sequence

from run_hy8.models import FlowDefinition
from tests.hy8runner.hy8_runner_crossing import Hy8RunnerCulvertCrossing
from tests.hy8runner.hy8_runner_culvert import Hy8RunnerCulvertBarrel

ROOT: Path = Path(__file__).resolve().parent.parent
SRC_ROOT: Path = ROOT / "src"
for path in (ROOT, SRC_ROOT):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from run_hy8 import (  # noqa: E402
    CulvertBarrel,
    CulvertCrossing,
    CulvertMaterial,
    CulvertShape,
    FlowMethod,
    Hy8Executable,
    Hy8FileWriter,
    Hy8Project,
    RoadwaySurface,
    UnitSystem,
)
from run_hy8.results import FlowProfile, Hy8Series, parse_rsql, parse_rst  # noqa: E402
from scripts.batch_hy8_compare import Scenario, build_crossing, load_scenarios  # noqa: E402
from tests.hy8runner.hy8_runner import Hy8Runner  # noqa: E402

DEFAULT_SCENARIO_DATA: list[dict[str, float | int | str]] = [
    {
        "internal_name": "Dry Creek Reach 1",
        "chan_id": "DRY-01",
        "q": 7.5,
        "ds_headwater": 98.4,
        "length": 18.0,
        "mannings_n": 0.012,
        "us_invert": 96.8,
        "ds_invert": 96.3,
        "height_m": 2.8,
        "barrels": 1,
    },
    {
        "internal_name": "Middle Fork Crossing",
        "chan_id": "MF-12",
        "q": 15.0,
        "ds_headwater": 152.2,
        "length": 24.0,
        "mannings_n": 0.013,
        "us_invert": 150.1,
        "ds_invert": 149.7,
        "height_m": 3.6,
        "barrels": 2,
    },
    {
        "internal_name": "Box Culvert Demo",
        "chan_id": "BOX-77A",
        "q": 22.0,
        "ds_headwater": 205.7,
        "length": 12.0,
        "mannings_n": 0.014,
        "us_invert": 203.5,
        "ds_invert": 203.0,
        "height_m": 3.0,
        "barrels": 1,
    },
    {
        "internal_name": "Coastal Relief Pipe",
        "chan_id": "CRP-5",
        "q": 4.0,
        "ds_headwater": 12.8,
        "length": 10.0,
        "mannings_n": 0.015,
        "us_invert": 10.9,
        "ds_invert": 10.5,
        "height_m": 1.5,
        "barrels": 3,
    },
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Create a small sample HY-8 project, write it with run-hy8 and "
            "the legacy hy8runner, and optionally run both through HY-8."
        )
    )
    parser.add_argument(
        "--excel",
        type=Path,
        default=Path("tests/results-to-check.xlsx"),
        help="Optional Excel workbook to pull scenarios from (defaults to tests/results-to-check.xlsx).",
    )
    parser.add_argument(
        "--scenario-file",
        type=Path,
        help="CSV or JSON file containing deterministic scenario definitions (takes precedence over --excel).",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=3,
        help="Number of sample scenarios to include (0 = all available).",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("sample_compare"),
        help="Where to place generated HY-8 files and outputs.",
    )
    parser.add_argument(
        "--hy8-exe",
        type=Path,
        help="Path to the HY-8 executable. Provide this to run HY-8 and compare .rst/.rsql outputs.",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Overwrite the output directory if it already exists.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if args.hy8_exe and not args.hy8_exe.exists():
        raise FileNotFoundError(f"HY-8 executable not found: {args.hy8_exe}")

    output_dir: Path = prepare_output_dir(args.output_dir, overwrite=args.force)
    scenarios, source_message = select_scenarios(args.scenario_file, args.excel, args.limit)
    if not scenarios:
        raise RuntimeError("No scenarios were generated. Provide a workbook or adjust the built-in sample count.")
    print(source_message)

    project: Hy8Project = build_project(title="Sample Comparison", scenarios=scenarios)
    run_dir: Path = output_dir / "run_hy8"
    legacy_dir: Path = output_dir / "hy8runner"
    run_file: Path = write_with_run_hy8(project=project, directory=run_dir)
    legacy_file: Path = write_with_hy8runner(project=project, directory=legacy_dir, hy8_exe=args.hy8_exe)
    print(f"Wrote run-hy8 project to {run_file}")
    print(f"Wrote hy8runner project to {legacy_file}")

    diff = diff_files(run_file, legacy_file)
    if diff:
        print("Differences detected between the generated project files:")
        for line in diff:
            print(line)
    else:
        print("run-hy8 and hy8runner produced identical .hy8 files for the sample scenarios.")

    if args.hy8_exe:
        print("Running HY-8 for both projects ...")
        run_rst, run_rsql = run_hy8_outputs(args.hy8_exe, run_file)
        legacy_rst, legacy_rsql = run_hy8_outputs(args.hy8_exe, legacy_file)
        log_result_preview("run-hy8", run_rst)
        log_result_preview("hy8runner", legacy_rst)
        mismatches = compare_result_sets(run_rst, legacy_rst)
        if mismatches:
            print("HY-8 output differences detected:")
            for mismatch in mismatches:
                print(f"  - {mismatch}")
        else:
            print("HY-8 produced matching discharge/headwater/velocity series for both project files.")
        summarize_profile_differences(run_rsql, legacy_rsql)
    else:
        print("HY-8 executable not provided; skipping .rst/.rsql comparisons.")


def prepare_output_dir(path: Path, *, overwrite: bool) -> Path:
    if path.exists():
        if not overwrite:
            raise FileExistsError(f"{path} already exists. Re-run with --force to overwrite.")
        shutil.rmtree(path)
    path.mkdir(parents=True, exist_ok=True)
    return path


def select_scenarios(
    scenario_file: Path | None,
    excel_path: Path | None,
    limit: int,
) -> tuple[list[Scenario], str]:
    limit = max(0, limit)
    if scenario_file:
        if not scenario_file.exists():
            raise FileNotFoundError(f"Scenario file not found: {scenario_file}")
        scenarios, skipped = load_scenarios_from_data_file(scenario_file, skip_zero_flow=True)
        if not scenarios:
            raise RuntimeError(f"No scenarios were found in {scenario_file}.")
        count = len(scenarios) if limit == 0 else min(limit, len(scenarios))
        message = f"Loaded {count} scenarios from {scenario_file} " f"(skipped {skipped} rows with zero discharge)."
        return scenarios[:count], message
    if excel_path and excel_path.exists():
        scenarios, skipped = load_scenarios(excel_path, skip_zero_flow=True)
        if scenarios:
            count = len(scenarios) if limit == 0 else min(limit, len(scenarios))
            message = f"Loaded {count} scenarios from {excel_path} " f"(skipped {skipped} rows with zero discharge)."
            return scenarios[:count], message
        print(f"Workbook {excel_path} did not yield any valid scenarios; falling back to built-in samples.")
    fallback: list[Scenario] = build_builtin_scenarios()
    if not fallback:
        return [], "No built-in scenarios are available."
    count: int = len(fallback) if limit == 0 else min(limit, len(fallback))
    return fallback[:count], f"Using {count} built-in sample scenarios."


def build_builtin_scenarios() -> list[Scenario]:
    scenarios: list[Scenario] = []
    for index, spec in enumerate(DEFAULT_SCENARIO_DATA, start=1):
        height = float(spec["height_m"])
        crest = float(spec.get("roadway_crest") or (float(spec["us_invert"]) + 4 * height))
        scenarios.append(
            Scenario(
                index=index,
                internal_name=str(spec["internal_name"]),
                chan_id=str(spec["chan_id"]),
                q=float(spec["q"]),
                v_reported=math.nan,
                us_headwater_reported=math.nan,
                ds_headwater=float(spec["ds_headwater"]),
                length=float(spec["length"]),
                mannings_n=float(spec["mannings_n"]),
                us_invert=float(spec["us_invert"]),
                ds_invert=float(spec["ds_invert"]),
                height_m=height,
                barrels=int(spec["barrels"]),
                roadway_crest=crest,
            )
        )
    return scenarios


def build_project(title: str, scenarios: Sequence[Scenario]) -> Hy8Project:
    project = Hy8Project(title=title, designer="sample-tool", units=UnitSystem.SI)
    for scenario in scenarios:
        crossing: CulvertCrossing = build_crossing(scenario=scenario)
        project.crossings.append(crossing)
    return project


def write_with_run_hy8(project: Hy8Project, directory: Path) -> Path:
    directory.mkdir(parents=True, exist_ok=True)
    hy8_path: Path = directory / f"{slugify(name=project.title)}.hy8"
    Hy8FileWriter(project).write(hy8_path, overwrite=True)
    return hy8_path


def write_with_hy8runner(project: Hy8Project, directory: Path, hy8_exe: Path | None) -> Path:
    directory.mkdir(parents=True, exist_ok=True)
    hy8_path: Path = directory / f"{slugify(name=project.title)}.hy8"
    exe_dir: Path = hy8_exe.parent if hy8_exe else directory
    exe_path: Path = exe_dir / "HY864.exe" if not hy8_exe else hy8_exe
    if not exe_path.exists():
        exe_path.write_bytes(b"")

    runner = Hy8Runner(hy8_exe_path=str(exe_dir), hy8_file=str(hy8_path))
    runner.project_title = project.title
    runner.designer_name = project.designer
    runner.project_notes = project.notes
    runner.set_hy8_exe_path(hy8_exe_path=str(exe_dir))
    runner.set_hy8_file(hy8_file=str(hy8_path))
    type(runner).si_units = project.units is UnitSystem.SI
    type(runner).exit_loss_option = project.exit_loss_option

    while len(runner.crossings) < len(project.crossings):
        runner.add_crossing()
    while len(runner.crossings) > len(project.crossings):
        runner.delete_crossing(index=len(runner.crossings) - 1)

    for index, crossing in enumerate(project.crossings):
        runner.set_culvert_crossing_name(name=crossing.name, index=index)
        _configure_flow(runner=runner, crossing=crossing, index=index)
        runner.set_tw_constant(
            tw_invert_elevation=crossing.tailwater.invert_elevation,
            tw_constant_elevation=crossing.tailwater.constant_elevation,
            index=index,
        )
        runner.set_roadway_width(roadway_width=crossing.roadway.width, index=index)
        runner.set_roadway_surface(roadway_surface=_surface_name(surface=crossing.roadway.surface), index=index)
        runner.set_roadway_stations_and_elevations(
            stations=crossing.roadway.stations,
            elevations=crossing.roadway.elevations,
            index=index,
        )
        runner.crossings[index].roadway_shape = crossing.roadway.shape
        _synchronize_culverts(runner=runner, culverts=crossing.culverts, crossing_index=index)

    success, messages = runner.create_hy8_file()
    if not success:
        raise RuntimeError(f"hy8runner failed to create the project: {messages}")
    return hy8_path


def _configure_flow(runner: Hy8Runner, crossing: CulvertCrossing, index: int) -> None:
    flow: FlowDefinition = crossing.flow
    values: list[float] = flow.sequence()
    if flow.method is FlowMethod.MIN_DESIGN_MAX:
        if len(values) != 3:
            raise ValueError(f"{crossing.name}: Min/Design/Max problems require exactly three flows.")
        runner.set_discharge_min_design_max_flow(
            flow_min=values[0],
            flow_design=values[1],
            flow_max=values[2],
            index=index,
        )
    elif flow.method is FlowMethod.USER_DEFINED:
        if len(values) < 2:
            raise ValueError(f"{crossing.name}: Provide at least two user-defined flow values.")
        runner.set_discharge_user_list_flow(values, index=index)
    else:
        raise ValueError(f"{crossing.name}: Flow method '{flow.method.value}' is not supported by run-hy8.")


def _synchronize_culverts(runner: Hy8Runner, culverts: list[CulvertBarrel], crossing_index: int) -> None:
    crossing: Hy8RunnerCulvertCrossing = runner.crossings[crossing_index]
    while len(crossing.culverts) < len(culverts):
        runner.add_culvert_barrel(index_crossing=crossing_index)
    while len(crossing.culverts) > len(culverts):
        runner.delete_culvert_barrel(index_crossing=crossing_index, index_culvert=len(crossing.culverts) - 1)

    for culvert_index, culvert in enumerate(culverts):
        runner.set_culvert_barrel_name(
            name=culvert.name or f"Culvert {culvert_index + 1}",
            index_crossing=crossing_index,
            index_culvert=culvert_index,
        )
        runner.set_culvert_barrel_shape(
            shape=_shape_name(culvert.shape),
            index_crossing=crossing_index,
            index_culvert=culvert_index,
        )
        rise: float = culvert.rise if culvert.rise > 0 else culvert.span
        runner.set_culvert_barrel_span_and_rise(
            span=culvert.span,
            rise=rise,
            index_crossing=crossing_index,
            index_culvert=culvert_index,
        )
        runner.set_culvert_barrel_material(
            material=_material_name(material=culvert.material),
            index_crossing=crossing_index,
            index_culvert=culvert_index,
        )
        runner.set_culvert_barrel_site_data(
            inlet_invert_station=culvert.inlet_invert_station,
            inlet_invert_elevation=culvert.inlet_invert_elevation,
            outlet_invert_station=culvert.outlet_invert_station,
            outlet_invert_elevation=culvert.outlet_invert_elevation,
            index_crossing=crossing_index,
            index_culvert=culvert_index,
        )
        runner.set_culvert_barrel_number_of_barrels(
            number_of_barrels=culvert.number_of_barrels,
            index_crossing=crossing_index,
            index_culvert=culvert_index,
        )
        hy8_culvert: Hy8RunnerCulvertBarrel = runner.crossings[crossing_index].culverts[culvert_index]
        hy8_culvert.notes = culvert.notes
        hy8_culvert.manning_n_top = culvert.manning_n_top
        hy8_culvert.manning_n_bottom = culvert.manning_n_bottom


def diff_files(new_file: Path, legacy_file: Path) -> list[str]:
    new_lines: list[str] = _normalized_lines(path=new_file)
    legacy_lines: list[str] = _normalized_lines(path=legacy_file)
    return list(
        difflib.unified_diff(
            legacy_lines,
            new_lines,
            fromfile=str(legacy_file),
            tofile=str(new_file),
            lineterm="",
        )
    )


def run_hy8_outputs(exe_path: Path, hy8_path: Path) -> tuple[dict[str, Hy8Series], dict[str, list]]:
    executor = Hy8Executable(exe_path)
    result: CompletedProcess[str] = executor.open_run_save(hy8_file=hy8_path, check=False)
    if result.returncode != 0:
        print(f"HY-8 exited with {result.returncode} for {hy8_path}.")
        if result.stdout:
            print("stdout:")
            print(result.stdout.strip())
        if result.stderr:
            print("stderr:")
            print(result.stderr.strip())
    rst_path: Path = hy8_path.with_suffix(".rst")
    rsql_path: Path = hy8_path.with_suffix(".rsql")
    rst_data: dict[str, Hy8Series] = parse_rst(rst_path) if rst_path.exists() else {}
    rsql_data: dict[str, list[FlowProfile]] = parse_rsql(rsql_path) if rsql_path.exists() else {}
    return rst_data, rsql_data


def compare_result_sets(
    run_data: dict[str, Hy8Series],
    legacy_data: dict[str, Hy8Series],
    *,
    tolerance: float = 1e-6,
) -> list[str]:
    mismatches: list[str] = []
    all_names: list[str] = sorted({*run_data.keys(), *legacy_data.keys()})
    for name in all_names:
        run_entry: Hy8Series | None = run_data.get(name)
        legacy_entry: Hy8Series | None = legacy_data.get(name)
        if run_entry is None or legacy_entry is None:
            mismatches.append(f"{name}: missing from {'run-hy8' if legacy_entry else 'hy8runner'} results")
            continue
        for key in ("flow", "headwater", "velocity", "roadway"):
            run_series = list(run_entry.get(key) or [])
            legacy_series = list(legacy_entry.get(key) or [])
            if not sequences_close(run_series, legacy_series, tolerance):
                mismatches.append(f"{name}: {key} values differ")
        if run_entry.get("iterations") != legacy_entry.get("iterations"):
            mismatches.append(f"{name}: iteration summaries differ")
    return mismatches


def sequences_close(a: Iterable[float], b: Iterable[float], tolerance: float) -> bool:
    list_a: list[float] = list(a)
    list_b: list[float] = list(b)
    if len(list_a) != len(list_b):
        return False
    for left, right in zip(list_a, list_b, strict=False):
        if math.isnan(left) and math.isnan(right):
            continue
        if (math.isnan(left) and not math.isnan(right)) or (not math.isnan(left) and math.isnan(right)):
            return False
        if abs(left - right) > tolerance:
            return False
    return True


def log_result_preview(label: str, data: dict[str, Hy8Series], *, limit: int = 3) -> None:
    if not data:
        print(f"{label}: no .rst data found.")
        return
    print(f"{label}: previewing up to {limit} flow rows per crossing")
    for name, entry in data.items():
        flows: list[float] = list(entry.get("flow") or [])
        headwaters: list[float] = list(entry.get("headwater") or [])
        velocities: list[float] = list(entry.get("velocity") or [])
        sample_count: int = min(limit, len(flows))
        for idx in range(sample_count):
            flow: float = flows[idx]
            headwater: float = headwaters[idx] if idx < len(headwaters) else math.nan
            velocity: float = velocities[idx] if idx < len(velocities) else math.nan
            print(
                f"  {name} #{idx + 1}: "
                f"Q={_format_value(flow)} cms, HW={_format_value(headwater)} m, V={_format_value(velocity)} m/s"
            )


def summarize_profile_differences(
    run_profiles: dict[str, list],
    legacy_profiles: dict[str, list],
) -> None:
    if not run_profiles and not legacy_profiles:
        print("No .rsql flow profiles detected.")
        return
    all_names: list[str] = sorted({*run_profiles.keys(), *legacy_profiles.keys()})
    for name in all_names:
        run_list = run_profiles.get(name) or []
        legacy_list = legacy_profiles.get(name) or []
        if len(run_list) != len(legacy_list):
            print(f"{name}: profile counts differ ({len(run_list)} vs {len(legacy_list)})")
            continue
        print(f"{name}: {len(run_list)} flow profiles available.")


def slugify(name: str) -> str:
    safe: str = re.sub(r"[^A-Za-z0-9]+", "_", name.strip())
    return safe.strip("_") or "project"


def _surface_name(surface: RoadwaySurface) -> str:
    mapping: dict[RoadwaySurface, str] = {
        RoadwaySurface.PAVED: "paved",
        RoadwaySurface.GRAVEL: "gravel",
        RoadwaySurface.USER_DEFINED: "user-defined",
    }
    return mapping[surface]


def _shape_name(shape: CulvertShape) -> str:
    mapping: dict[CulvertShape, str] = {
        CulvertShape.CIRCLE: "circle",
        CulvertShape.BOX: "box",
    }
    return mapping[shape]


def _material_name(material: CulvertMaterial) -> str:
    mapping: dict[CulvertMaterial, str] = {
        CulvertMaterial.CONCRETE: "concrete",
        CulvertMaterial.CORRUGATED_STEEL: "corrugated steel",
    }
    return mapping[material]


def _format_value(value: float) -> str:
    if math.isnan(value):
        return "nan"
    return f"{value:.3f}"


def _normalized_lines(path: Path) -> list[str]:
    lines: list[str] = []
    for raw in path.read_text(encoding="utf-8").splitlines():
        if raw.startswith("PROJDATE"):
            continue
        if not raw or raw[0].isspace():
            continue
        if raw.startswith("HY8PROJECTFILE"):
            raw: str = _normalize_header(raw)
        tokens: list[str] = [_normalize_token(token) for token in raw.split()]
        lines.append(" ".join(tokens))
    return lines


def _normalize_token(token: str) -> str:
    try:
        value = float(token)
    except ValueError:
        return token
    formatted: str = f"{value:.6f}".rstrip("0").rstrip(".")
    if not formatted:
        return "0.0"
    if "." not in formatted:
        formatted = f"{formatted}.0"
    return formatted


def _normalize_header(line: str) -> str:
    prefix = "HY8PROJECTFILE"
    if not line.startswith(prefix):
        return line
    suffix: str = line[len(prefix) :]
    try:
        number = float(suffix)
    except ValueError:
        return line
    text: str = str(int(number)) if number.is_integer() else suffix
    return f"{prefix}{text}"


def load_scenarios_from_data_file(path: Path, *, skip_zero_flow: bool) -> tuple[list[Scenario], int]:
    suffix: str = path.suffix.lower()
    if suffix == ".json":
        return load_scenarios_from_json(path, skip_zero_flow=skip_zero_flow)
    if suffix == ".csv":
        return load_scenarios_from_csv(path, skip_zero_flow=skip_zero_flow)
    raise ValueError(f"Unsupported scenario file type: {path.suffix}")


def load_scenarios_from_json(path: Path, *, skip_zero_flow: bool) -> tuple[list[Scenario], int]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(data, dict):
        if "scenarios" in data:
            data = data["scenarios"]
        elif "data" in data:
            data = data["data"]
    if not isinstance(data, list):
        raise ValueError(f"JSON scenario file {path} must contain a list of scenario mappings.")
    return records_to_scenarios(data, skip_zero_flow=skip_zero_flow)


def load_scenarios_from_csv(path: Path, *, skip_zero_flow: bool) -> tuple[list[Scenario], int]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        reader: csv.DictReader[str] = csv.DictReader(handle)
        records = list(reader)
    return records_to_scenarios(records, skip_zero_flow=skip_zero_flow)


def records_to_scenarios(records: Sequence[dict[str, Any]], *, skip_zero_flow: bool) -> tuple[list[Scenario], int]:
    scenarios: list[Scenario] = []
    zero_flow_skipped = 0
    for sequence, record in enumerate(records):
        q: float = _float(record.get("Q"))
        if skip_zero_flow and not math.isnan(q) and abs(q) <= 1e-9:
            zero_flow_skipped += 1
            continue
        ds_headwater: float = _float(record.get("DS_h"))
        height: float = _float(record.get("Height"))
        if math.isnan(q) or math.isnan(ds_headwater) or math.isnan(height):
            continue
        index: int = _int(record.get("index"), default=sequence)
        us_invert: float = _float(record.get("US Invert"), fallback=ds_headwater)
        ds_invert: float = _float(record.get("DS Invert"), fallback=ds_headwater)
        crest_override: float = _float(record.get("roadway_crest"))
        roadway_crest: float = crest_override if not math.isnan(crest_override) else us_invert + 10.0 * max(0.1, height)
        mannings = _float(record.get("n or Cd"), fallback=0.0)
        barrels = record.get("number_interp", 1)
        scenarios.append(
            Scenario(
                index=index,
                internal_name=str(record.get("internalName", f"Scenario {sequence + 1}")),
                chan_id=str(record.get("Chan ID", f"CHAN-{sequence + 1:03d}")),
                q=q,
                v_reported=_float(record.get("V")),
                us_headwater_reported=_float(record.get("US_h")),
                ds_headwater=ds_headwater,
                length=_float(record.get("Length"), fallback=0.0),
                mannings_n=mannings,
                us_invert=us_invert,
                ds_invert=ds_invert,
                height_m=height,
                barrels=max(1, int(_int(barrels, default=1))),
                roadway_crest=roadway_crest,
            )
        )
    return scenarios, zero_flow_skipped


def _float(value: Any, fallback: float = math.nan) -> float:
    if value is None or value == "":
        return fallback
    try:
        return float(value)
    except (TypeError, ValueError):
        return fallback


def _int(value: Any, *, default: int) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


if __name__ == "__main__":
    main()
