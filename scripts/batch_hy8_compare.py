"""Batch HY-8 runner that compares spreadsheet values against HY-8 outputs."""

from __future__ import annotations

import argparse
import math
import os
import re
import shutil
from dataclasses import dataclass
from pathlib import Path

import concurrent.futures
import pandas as pd
from pandas import DataFrame

from run_hy8 import (
    CulvertBarrel,
    CulvertCrossing,
    CulvertMaterial,
    CulvertShape,
    FlowDefinition,
    FlowMethod,
    Hy8Executable,
    Hy8FileWriter,
    Hy8Project,
    RoadwaySurface,
    UnitSystem,
)
from run_hy8.results import Hy8Results, parse_rst, parse_rsql


@dataclass(slots=True)
class Scenario:
    index: int
    internal_name: str
    chan_id: str
    q: float
    v_reported: float
    us_headwater_reported: float
    ds_headwater: float
    length: float
    mannings_n: float
    us_invert: float
    ds_invert: float
    height_m: float
    barrels: int
    roadway_crest: float

    @property
    def crossing_name(self) -> str:
        safe_chan = re.sub(r"[^A-Za-z0-9]+", "_", self.chan_id or "CHAN")
        return f"S{self.index:05d}_{safe_chan}"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate HY-8 velocities/headwaters for spreadsheet scenarios.")
    parser.add_argument(
        "--input",
        type=Path,
        default=Path("results-to-check.xlsx"),
        help="Excel source file.",
    )
    parser.add_argument(
        "--exe",
        type=Path,
        default=Path(r"C:\Program Files\HY-8 8.00\HY864.exe"),
        help="HY-8 executable path.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("hy8_velocity_comparison.csv"),
        help="CSV comparison output.",
    )
    parser.add_argument(
        "--workdir",
        type=Path,
        default=Path("hy8_batches"),
        help="Temporary working directory.",
    )
    parser.add_argument("--batch-size", type=int, default=75, help="Number of crossings per HY-8 batch.")
    parser.add_argument(
        "--max-batches",
        type=int,
        default=0,
        help="Optional limit on processed batches (0 = all).",
    )
    parser.add_argument(
        "--workers",
        type=int,
        default=max(1, (os.cpu_count() or 4) // 2),
        help="Parallel HY-8 processes.",
    )
    parser.add_argument(
        "--max-scenarios",
        type=int,
        default=20,
        help="Maximum number of scenarios to process (0 = all).",
    )
    return parser.parse_args()


def prepare_workdir(path: Path) -> Path:
    if not path.exists():
        path.mkdir(parents=True, exist_ok=True)
        return path
    try:
        shutil.rmtree(path)
    except OSError:
        suffix = 1
        while True:
            candidate = path.with_name(f"{path.name}_{suffix}")
            if not candidate.exists():
                candidate.mkdir(parents=True, exist_ok=True)
                return candidate
            suffix += 1
    path.mkdir(parents=True, exist_ok=True)
    return path


def load_scenarios(path: Path, *, skip_zero_flow: bool = True) -> tuple[list[Scenario], int]:
    df = pd.read_excel(path)  # type: ignore
    required: list[str] = [
        "internalName",
        "Chan ID",
        "Q",
        "V",
        "US_h",
        "DS_h",
        "Length",
        "n or Cd",
        "US Invert",
        "DS Invert",
        "Height",
        "number_interp",
    ]
    missing: list[str] = [col for col in required if col not in df.columns]
    if missing:
        raise ValueError(f"Missing columns: {missing}")

    df: DataFrame = df.dropna(subset=["Q", "DS_h", "Height"])  # type: ignore
    zero_flow_skipped = 0
    if skip_zero_flow:
        mask = df["Q"].astype(float).abs() <= 1e-9
        zero_flow_skipped = int(mask.sum())
        if zero_flow_skipped:
            df = df.loc[~mask]
    scenarios: list[Scenario] = []
    for idx, row in df.iterrows():
        diameter_m = max(0.1, float(row["Height"]))
        roadway_crest = float(row.get("US Invert", row["DS_h"])) + 10 * diameter_m
        scenarios.append(
            Scenario(
                index=int(idx),  # type: ignore
                internal_name=str(row["internalName"]).strip(),
                chan_id=str(row["Chan ID"]).strip(),
                q=float(row["Q"]),
                v_reported=float(row.get("V", float("nan"))),
                us_headwater_reported=float(row.get("US_h", float("nan"))),
                ds_headwater=float(row["DS_h"]),
                length=float(row.get("Length", 0.0) or 0.0),
                mannings_n=float(row.get("n or Cd", 0.0) or 0.0),
                us_invert=float(row.get("US Invert", row["DS_h"])),
                ds_invert=float(row.get("DS Invert", row["DS_h"])),
                height_m=float(row["Height"]),
                barrels=max(1, int(round(row.get("number_interp", 1.0) or 1.0))),
                roadway_crest=roadway_crest,
            )
        )
    return scenarios, zero_flow_skipped


def partition_batches(items: list[Scenario], batch_size: int) -> list[list[Scenario]]:
    return [items[i : i + batch_size] for i in range(0, len(items), batch_size)]


def build_crossing(scenario: Scenario) -> CulvertCrossing:
    crossing = CulvertCrossing(name=scenario.crossing_name)
    flow = FlowDefinition(method=FlowMethod.MIN_DESIGN_MAX)
    flow.minimum, flow.design, flow.maximum = build_flow_range(scenario.q)
    crossing.flow = flow
    tailwater_constant = scenario.ds_headwater
    if tailwater_constant <= scenario.ds_invert:
        tailwater_constant = scenario.ds_invert + 0.01
    crossing.tailwater.constant_elevation = tailwater_constant
    invert_elevation = min(scenario.ds_invert, scenario.us_invert, tailwater_constant - 0.01)
    crossing.tailwater.invert_elevation = invert_elevation

    diameter_m = max(0.1, scenario.height_m)
    roadway_width = max(5.0, diameter_m * 6)
    crest = scenario.roadway_crest
    crossing.roadway.width = roadway_width
    crossing.roadway.stations = [-roadway_width / 2, 0.0, roadway_width / 2]
    crossing.roadway.elevations = [crest, crest, crest]
    crossing.roadway.surface = RoadwaySurface.PAVED

    barrel = CulvertBarrel(name="Barrel 1")
    barrel.shape = CulvertShape.CIRCLE
    barrel.material = CulvertMaterial.CONCRETE
    barrel.span = diameter_m
    barrel.rise = diameter_m
    barrel.number_of_barrels = scenario.barrels
    barrel.inlet_invert_elevation = scenario.us_invert
    barrel.outlet_invert_elevation = scenario.ds_invert
    barrel.inlet_invert_station = 0.0
    barrel.outlet_invert_station = scenario.length if scenario.length > 0 else diameter_m
    if scenario.mannings_n > 0:
        barrel.manning_n_top = scenario.mannings_n
        barrel.manning_n_bottom = scenario.mannings_n
    crossing.culverts.append(barrel)
    return crossing


def build_flow_range(q: float) -> tuple[float, float, float]:
    design = max(0.01, q)
    minimum = max(0.005, design * 0.9)
    maximum = max(design + 0.01, design * 1.1)
    if minimum >= design:
        design = minimum + 0.01
    if design >= maximum:
        maximum = design + 0.01
    return minimum, design, maximum


def summarize_process_stream(stream: str, limit: int = 12) -> str:
    lines = [line.strip() for line in stream.splitlines() if line.strip()]
    if not lines:
        return ""
    if len(lines) > limit:
        lines = lines[-limit:]
        lines.insert(0, f"... ({len(stream.splitlines()) - limit} omitted) ...")
    return "\n".join(lines)


def process_batch(
    scenarios: list[Scenario],
    batch_index: int,
    exe_path: Path,
    workdir: Path,
) -> list[dict[str, float | str]]:
    batch_dir = workdir / f"batch_{batch_index:04d}"
    batch_dir.mkdir(parents=True, exist_ok=True)
    project = Hy8Project(title=f"batch_{batch_index}", designer="batch-tool", units=UnitSystem.SI)
    for scenario in scenarios:
        project.crossings.append(build_crossing(scenario))
    hy8_path = batch_dir / "batch.hy8"
    Hy8FileWriter(project).write(hy8_path, overwrite=True)
    executor = Hy8Executable(exe_path)
    result = executor.open_run_save(hy8_path, check=False)
    if result.returncode != 0:
        print(f"HY-8 returned {result.returncode} for {hy8_path}. Attempting to continue.")
        stdout_summary = summarize_process_stream(result.stdout)
        stderr_summary = summarize_process_stream(result.stderr)
        if stdout_summary:
            print("  stdout tail:")
            for line in stdout_summary.splitlines():
                print(f"    {line}")
        if stderr_summary:
            print("  stderr tail:")
            for line in stderr_summary.splitlines():
                print(f"    {line}")
    rst_path = hy8_path.with_suffix(".rst")
    if not rst_path.exists():
        message = "RST not found"
        if result.returncode != 0:
            message = f"HY-8 returned {result.returncode}; RST not found"
        return [
            build_record(scenario, status="error", message=message, workdir=str(batch_dir)) for scenario in scenarios
        ]
    parsed = parse_rst(rst_path)
    rsql_path = hy8_path.with_suffix(".rsql")
    rsql_data = parse_rsql(rsql_path) if rsql_path.exists() else {}
    records: list[dict[str, float | str]] = []
    for scenario in scenarios:
        entry = parsed.get(scenario.crossing_name)
        if not entry:
            records.append(
                build_record(
                    scenario,
                    status="error",
                    message="Missing entry in RST",
                    workdir=str(batch_dir),
                )
            )
            continue
        profiles = rsql_data.get(scenario.crossing_name)
        results = Hy8Results(entry, profiles)
        row = results.nearest(scenario.q)
        if row is None:
            records.append(
                build_record(
                    scenario,
                    status="error",
                    message="No discharge values in HY-8 output",
                    workdir=str(batch_dir),
                )
            )
            continue
        flow_used = row.flow
        velocity_calc = row.velocity
        headwater_calc = row.headwater_elevation
        if not math.isnan(row.headwater_depth):
            headwater_calc = scenario.us_invert + row.headwater_depth
        roadway_max = results.roadway_max()
        overtopping_detected = row.overtopping
        status = "ok"
        message = ""
        crest = scenario.roadway_crest
        overtopping = overtopping_detected and not math.isnan(headwater_calc) and headwater_calc >= crest - 1e-3
        if headwater_calc >= crest - 1e-3 or overtopping:
            status = "error"
            reason = "Headwater exceeds crest" if headwater_calc >= crest - 1e-3 else "Overtopping reported"
            message = f"{reason}: HW {headwater_calc:.3f} crest {crest:.3f} (roadway max {roadway_max:.3f} cms)"
        records.append(
            build_record(
                scenario,
                status=status,
                message=message,
                workdir=str(batch_dir),
                flow_used=flow_used,
                velocity_calc=velocity_calc,
                headwater_calc=headwater_calc,
                roadway_max=roadway_max,
                overtopping=overtopping,
                flow_type=row.flow_type,
            )
        )
    return records


def build_record(
    scenario: Scenario,
    *,
    status: str,
    message: str,
    workdir: str,
    flow_used: float = math.nan,
    velocity_calc: float = math.nan,
    headwater_calc: float = math.nan,
    roadway_max: float = 0.0,
    overtopping: bool = False,
    flow_type: str = "",
) -> dict[str, float | str]:
    return {
        "index": scenario.index,
        "internalName": scenario.internal_name,
        "Chan ID": scenario.chan_id,
        "Q_input": scenario.q,
        "Q_used": flow_used,
        "V_reported": scenario.v_reported,
        "V_calc": velocity_calc,
        "V_diff": (
            velocity_calc - scenario.v_reported
            if not math.isnan(scenario.v_reported) and not math.isnan(velocity_calc)
            else math.nan
        ),
        "US_h_reported": scenario.us_headwater_reported,
        "US_h_calc": headwater_calc,
        "US_h_diff": (
            headwater_calc - scenario.us_headwater_reported
            if not math.isnan(scenario.us_headwater_reported) and not math.isnan(headwater_calc)
            else math.nan
        ),
        "DS_h": scenario.ds_headwater,
        "Length": scenario.length,
        "n_or_Cd": scenario.mannings_n,
        "US Invert": scenario.us_invert,
        "DS Invert": scenario.ds_invert,
        "Height_m": scenario.height_m,
        "Barrels": scenario.barrels,
        "RoadwayCrest": scenario.roadway_crest,
        "RoadwayDischargeMax": roadway_max,
        "Overtopping": overtopping,
        "FlowType": flow_type,
        "status": status,
        "message": message,
        "workdir": workdir,
    }


def main() -> None:
    args = parse_args()
    scenarios, skipped_zero_flow = load_scenarios(args.input, skip_zero_flow=True)
    if args.max_scenarios:
        if len(scenarios) > args.max_scenarios:
            print(f"Limiting to first {args.max_scenarios} scenarios (from {len(scenarios)}).")
            scenarios = scenarios[: args.max_scenarios]
    print(f"Loaded {len(scenarios)} scenarios (skipped {skipped_zero_flow} zero-flow rows).")
    batches = partition_batches(scenarios, args.batch_size)
    if args.max_batches:
        batches = batches[: args.max_batches]
    workdir = prepare_workdir(args.workdir)

    all_records: list[dict[str, float | str]] = []
    total = len(batches)
    with concurrent.futures.ThreadPoolExecutor(max_workers=args.workers) as executor:
        futures = {
            executor.submit(process_batch, batch, batch_index, args.exe, workdir): (
                batch_index,
                len(batch),
            )
            for batch_index, batch in enumerate(batches, start=1)
        }
        for future in concurrent.futures.as_completed(futures):
            batch_index, size = futures[future]
            try:
                batch_records = future.result()
                all_records.extend(batch_records)
                print(f"Completed batch {batch_index}/{total} ({size} crossings).")
            except Exception as exc:  # noqa: BLE001
                print(f"Batch {batch_index} failed: {exc}")
    df = pd.DataFrame(all_records)
    df.sort_values(by="index", inplace=True)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(args.output, index=False)
    errors: DataFrame = df[df["status"] != "ok"]
    print(f"Wrote {len(df)} rows to {args.output} ({len(errors)} errors).")
    if not errors.empty:
        print("First errors:")
        print(errors.head())


if __name__ == "__main__":
    main()
