"""Benchmark multiple HY-8 runs to compare batching strategies."""

from __future__ import annotations

import argparse
from concurrent.futures._base import Future
import csv
import math
import shutil
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from pathlib import Path
from subprocess import CompletedProcess
from time import perf_counter
from typing import Iterable, Sequence

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
    parse_rsql,
    parse_rst,
)
from run_hy8.results import FlowProfile, Hy8Series

SUMMARY_FIELDS: list[str] = [
    "repeat",
    "batch_size",
    "workers",
    "batches",
    "crossings",
    "wall_time_s",
    "time_per_crossing_s",
    "time_per_batch_s",
    "sum_batch_time_s",
    "hy8_time_s",
    "write_time_s",
    "parse_time_s",
    "hy8_failures",
    "parse_failures",
    "max_batch_time_s",
    "min_batch_time_s",
]

DETAIL_FIELDS: list[str] = [
    "repeat",
    "batch_size",
    "workers",
    "batch_index",
    "crossings",
    "hy8_file",
    "write_time_s",
    "hy8_time_s",
    "parse_time_s",
    "total_time_s",
    "returncode",
    "parsed_ok",
    "rows_parsed",
    "message",
]


@dataclass(slots=True)
class CrossingSpec:
    """Parameters used to synthesize consistent benchmark crossings."""

    index: int
    design_flow: float
    diameter: float
    length: float
    slope: float
    barrels: int
    ds_invert: float

    def build(self) -> CulvertCrossing:
        name: str = f"Benchmark_{self.index:04d}"
        crossing = CulvertCrossing(name=name)

        design: float = max(0.01, self.design_flow)
        minimum: float = max(0.005, design * 0.9)
        maximum: float = design * 1.1
        flow = FlowDefinition(method=FlowMethod.MIN_DESIGN_MAX)
        flow.minimum = minimum
        flow.design = design
        flow.maximum = maximum
        flow.user_values = [minimum, design, maximum]
        crossing.flow = flow

        ds_invert: float = self.ds_invert
        us_invert: float = ds_invert + self.slope * self.length
        tailwater: float = ds_invert + 0.3 * self.diameter
        crest: float = us_invert + self.diameter + 1.0
        crossing.tailwater.constant_elevation = tailwater
        crossing.tailwater.invert_elevation = ds_invert

        width: float = max(6.0, self.diameter * 6)
        crossing.roadway.width = width
        crossing.roadway.surface = RoadwaySurface.PAVED
        crossing.roadway.stations = [-width / 2, 0.0, width / 2]
        crossing.roadway.elevations = [crest, crest, crest]

        barrel = CulvertBarrel(name=f"Barrel_{self.index:04d}")
        barrel.shape = CulvertShape.CIRCLE
        barrel.material = CulvertMaterial.CONCRETE
        barrel.span = self.diameter
        barrel.rise = self.diameter
        barrel.number_of_barrels = self.barrels
        barrel.inlet_invert_station = 0.0
        barrel.outlet_invert_station = self.length
        barrel.inlet_invert_elevation = us_invert
        barrel.outlet_invert_elevation = ds_invert
        crossing.culverts.append(barrel)

        return crossing


@dataclass(slots=True)
class BatchResult:
    """Timing/result metadata for one HY-8 batch file."""

    repeat: int
    batch_size: int
    workers: int
    batch_index: int
    crossings: int
    hy8_file: Path
    write_time: float
    hy8_time: float
    parse_time: float
    total_time: float
    returncode: int
    parsed_ok: bool
    rows_parsed: int
    message: str

    def to_row(self) -> dict[str, str | float | int]:
        return {
            "repeat": self.repeat,
            "batch_size": self.batch_size,
            "workers": self.workers,
            "batch_index": self.batch_index,
            "crossings": self.crossings,
            "hy8_file": str(self.hy8_file),
            "write_time_s": self.write_time,
            "hy8_time_s": self.hy8_time,
            "parse_time_s": self.parse_time,
            "total_time_s": self.total_time,
            "returncode": self.returncode,
            "parsed_ok": int(self.parsed_ok),
            "rows_parsed": self.rows_parsed,
            "message": self.message,
        }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Benchmark HY-8 throughput vs batch strategy.")
    parser.add_argument("--total-crossings", type=int, default=1_000, help="Crossings to synthesize.")
    parser.add_argument("--flow", type=float, default=25.0, help="Design discharge (cms).")
    parser.add_argument("--diameter", type=float, default=2.0, help="Barrel diameter (m).")
    parser.add_argument("--length", type=float, default=30.0, help="Culvert length (m).")
    parser.add_argument("--slope", type=float, default=0.005, help="Invert slope (m/m).")
    parser.add_argument("--barrels", type=int, default=1, help="Number of barrels per crossing.")
    parser.add_argument(
        "--batch-sizes",
        type=int,
        nargs="+",
        default=[25, 50, 100, 250],
        help="Crossings per HY-8 file to test.",
    )
    parser.add_argument(
        "--worker-counts",
        type=int,
        nargs="+",
        default=[1, 4],
        help="Thread counts controlling concurrent HY-8 executions.",
    )
    parser.add_argument("--repeats", type=int, default=2, help="Repeat each configuration this many times.")
    parser.add_argument(
        "--workdir",
        type=Path,
        default=Path("hy8_benchmark_runs"),
        help="Working directory for generated HY-8 files.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("hy8_benchmark_summary.csv"),
        help="Summary CSV output path.",
    )
    parser.add_argument(
        "--details-output",
        type=Path,
        default=Path("hy8_benchmark_batches.csv"),
        help="Detailed per-batch CSV output path.",
    )
    parser.add_argument("--keep-workdir", action="store_true", help="Do not delete existing workdir before running.")
    parser.add_argument(
        "--unit-system",
        choices=[u.name for u in UnitSystem],
        default=UnitSystem.SI.name,
        help="HY-8 unit system.",
    )
    return parser.parse_args()


def build_crossing_specs(args: argparse.Namespace) -> list[CrossingSpec]:
    specs: list[CrossingSpec] = []
    base_invert = 100.0
    for idx in range(args.total_crossings):
        ds_invert: float = base_invert + (idx % 10) * 0.05
        specs.append(
            CrossingSpec(
                index=idx + 1,
                design_flow=args.flow,
                diameter=args.diameter,
                length=args.length,
                slope=args.slope,
                barrels=args.barrels,
                ds_invert=ds_invert,
            )
        )
    return specs


def ensure_workdir(path: Path, *, keep_existing: bool) -> Path:
    if path.exists() and not keep_existing:
        shutil.rmtree(path)
    path.mkdir(parents=True, exist_ok=True)
    return path


def chunk_specs(specs: Sequence[CrossingSpec], batch_size: int) -> list[list[CrossingSpec]]:
    return [list(specs[i : i + batch_size]) for i in range(0, len(specs), batch_size)]


def build_project(chunk: Sequence[CrossingSpec], *, batch_index: int, units: UnitSystem) -> Hy8Project:
    project = Hy8Project(
        title=f"Benchmark batch {batch_index}",
        designer="run-hy8 benchmark",
        units=units,
    )
    for spec in chunk:
        project.crossings.append(spec.build())
    return project


def run_batch(
    *,
    chunk: Sequence[CrossingSpec],
    batch_index: int,
    repeat: int,
    batch_size: int,
    workers: int,
    hy8_path: Path,
    units: UnitSystem,
) -> BatchResult:
    project: Hy8Project = build_project(chunk=chunk, batch_index=batch_index, units=units)
    writer = Hy8FileWriter(project=project)

    write_start: float = perf_counter()
    project_path: Path = writer.write(output_path=hy8_path)
    write_time: float = perf_counter() - write_start

    exe = Hy8Executable()
    hy8_start: float = perf_counter()
    completed: CompletedProcess[str] = exe.open_run_save(hy8_file=project_path, check=False)
    hy8_time: float = perf_counter() - hy8_start

    stdout_path: Path = project_path.with_suffix(".stdout.txt")
    stderr_path: Path = project_path.with_suffix(".stderr.txt")
    stdout_path.write_text(completed.stdout or "", encoding="utf-8", errors="ignore")
    stderr_path.write_text(completed.stderr or "", encoding="utf-8", errors="ignore")

    parse_time = 0.0
    parsed_ok = False
    rows = 0
    notes: list[str] = []
    if completed.returncode == 0:
        parse_start: float = perf_counter()
        rst_path: Path = project_path.with_suffix(".rst")
        rsql_path: Path = project_path.with_suffix(".rsql")
        try:
            rst_data: dict[str, Hy8Series] = parse_rst(path=rst_path)
            _: dict[str, list[FlowProfile]] = parse_rsql(path=rsql_path)
            rows: int = sum(len(series.get("flow", [])) for series in rst_data.values())
            parsed_ok = bool(rst_data)
        except FileNotFoundError as exc:
            notes.append(str(exc))
        parse_time: float = perf_counter() - parse_start
    else:
        notes.append(f"HY-8 returned {completed.returncode}")

    total_time: float = write_time + hy8_time + parse_time
    message: str = "; ".join(notes) if notes else "ok"
    return BatchResult(
        repeat=repeat,
        batch_size=batch_size,
        workers=workers,
        batch_index=batch_index,
        crossings=len(chunk),
        hy8_file=project_path,
        write_time=write_time,
        hy8_time=hy8_time,
        parse_time=parse_time,
        total_time=total_time,
        returncode=completed.returncode,
        parsed_ok=parsed_ok,
        rows_parsed=rows,
        message=message,
    )


def summarize_configuration(records: Sequence[BatchResult], wall_time: float) -> dict[str, float | int | str]:
    if not records:
        return {}
    sum_batch_time: float = sum(r.total_time for r in records)
    hy8_time: float = sum(r.hy8_time for r in records)
    write_time: float = sum(r.write_time for r in records)
    parse_time: float = sum(r.parse_time for r in records)
    crossings: int = sum(r.crossings for r in records)
    num_batches: int = len(records)
    repeat: int = records[0].repeat
    batch_size: int = records[0].batch_size
    workers: int = records[0].workers
    return {
        "repeat": repeat,
        "batch_size": batch_size,
        "workers": workers,
        "batches": num_batches,
        "crossings": crossings,
        "wall_time_s": wall_time,
        "time_per_crossing_s": wall_time / crossings if crossings else math.nan,
        "time_per_batch_s": wall_time / num_batches if num_batches else math.nan,
        "sum_batch_time_s": sum_batch_time,
        "hy8_time_s": hy8_time,
        "write_time_s": write_time,
        "parse_time_s": parse_time,
        "hy8_failures": sum(1 for r in records if r.returncode != 0),
        "parse_failures": sum(1 for r in records if not r.parsed_ok),
        "max_batch_time_s": max(r.total_time for r in records),
        "min_batch_time_s": min(r.total_time for r in records),
    }


def run_configuration(
    *,
    specs: Sequence[CrossingSpec],
    batch_size: int,
    workers: int,
    repeat: int,
    workdir: Path,
    units: UnitSystem,
) -> tuple[list[BatchResult], float]:
    batches: list[list[CrossingSpec]] = chunk_specs(specs=specs, batch_size=batch_size)
    run_dir: Path = workdir / f"bs{batch_size}_w{workers}_r{repeat}"
    if run_dir.exists():
        shutil.rmtree(run_dir)
    run_dir.mkdir(parents=True, exist_ok=True)

    results: list[BatchResult] = []
    wall_start: float = perf_counter()
    with ThreadPoolExecutor(max_workers=workers) as executor:
        futures: dict[Future[BatchResult], int] = {
            executor.submit(
                run_batch,
                chunk=batch,
                batch_index=index,
                repeat=repeat,
                batch_size=batch_size,
                workers=workers,
                hy8_path=run_dir / f"batch_{index:04d}.hy8",
                units=units,
            ): index
            for index, batch in enumerate(batches, start=1)
        }
        for future in as_completed(futures):
            results.append(future.result())
    results.sort(key=lambda r: r.batch_index)
    wall_time: float = perf_counter() - wall_start
    return results, wall_time


def write_csv(path: Path, fieldnames: list[str], rows: Iterable[dict[str, float | int | str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer: csv.DictWriter[str] = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def main() -> None:
    args: argparse.Namespace = parse_args()
    if args.total_crossings <= 0:
        raise SystemExit("total-crossings must be positive.")
    if min(args.batch_sizes) <= 0:
        raise SystemExit("batch sizes must be positive.")
    if min(args.worker_counts) <= 0:
        raise SystemExit("worker counts must be positive.")

    specs: list[CrossingSpec] = build_crossing_specs(args)
    unit_system: UnitSystem = UnitSystem[args.unit_system]
    workdir: Path = ensure_workdir(args.workdir, keep_existing=args.keep_workdir)

    detailed_rows: list[dict[str, float | int | str]] = []
    summary_rows: list[dict[str, float | int | str]] = []

    for repeat in range(1, args.repeats + 1):
        for batch_size in args.batch_sizes:
            for workers in args.worker_counts:
                print(f"Running repeat {repeat} batch-size {batch_size} workers {workers}...")
                records, wall_time = run_configuration(
                    specs=specs,
                    batch_size=batch_size,
                    workers=workers,
                    repeat=repeat,
                    workdir=workdir,
                    units=unit_system,
                )
                detailed_rows.extend(record.to_row() for record in records)
                summary: dict[str, float | int | str] = summarize_configuration(records=records, wall_time=wall_time)
                summary_rows.append(summary)
                print(
                    f"Completed repeat {repeat}, batch-size {batch_size}, workers {workers}: "
                    f"{summary['wall_time_s']:.1f}s wall, "
                    f"{summary['time_per_crossing_s']:.3f}s/crossing."
                )

    write_csv(args.details_output, DETAIL_FIELDS, detailed_rows)
    write_csv(args.output, SUMMARY_FIELDS, summary_rows)
    print(f"Wrote summary to {args.output} and batch details to {args.details_output}")


if __name__ == "__main__":
    main()
