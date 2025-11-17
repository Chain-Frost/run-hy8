"""Simple CLI entry point for run-hy8."""

from __future__ import annotations

import argparse
from pathlib import Path
from subprocess import CompletedProcess
from typing import Sequence

from .config import load_project_from_json
from .executor import Hy8Executable
from .models import (
    CulvertBarrel,
    CulvertCrossing,
    FlowDefinition,
    FlowMethod,
    Hy8Project,
    RoadwayProfile,
    TailwaterDefinition,
)
from .writer import Hy8FileWriter


def main(argv: Sequence[str] | None = None) -> int:
    parser: argparse.ArgumentParser = argparse.ArgumentParser(
        description="Utilities for generating HY-8 project files."
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    demo_parser: argparse.ArgumentParser = subparsers.add_parser(
        name="demo",
        help="Write a demo .hy8 file that demonstrates the domain model and serialization.",
    )
    demo_parser.add_argument("--output", type=Path, default=Path("demo.hy8"), help="Destination .hy8 file.")
    demo_parser.add_argument("--overwrite", action="store_true", help="Replace output if it already exists.")

    build_parser: argparse.ArgumentParser = subparsers.add_parser(
        name="build",
        help="Generate a HY-8 file from a JSON configuration, optionally running HY-8 afterward.",
    )
    build_parser.add_argument(
        "--config",
        type=Path,
        required=True,
        help="Path to the JSON configuration file.",
    )
    build_parser.add_argument("--output", type=Path, required=True, help="Destination HY-8 file.")
    build_parser.add_argument("--overwrite", action="store_true", help="Replace the output file if it exists.")
    build_parser.add_argument(
        "--run-exe",
        type=Path,
        help="Optional HY-8 executable path. When provided, -OpenRunSave is executed after writing the project.",
    )
    build_parser.add_argument(
        "--validate-only",
        action="store_true",
        help="Validate the configuration without writing a .hy8 file or invoking HY-8.",
    )

    args: argparse.Namespace = parser.parse_args(list(argv) if argv is not None else None)
    if args.command == "demo":
        _run_demo(output=args.output, overwrite=args.overwrite)
        return 0
    if args.command == "build":
        _run_build(
            config_path=args.config,
            output=args.output,
            overwrite=args.overwrite,
            exe_path=args.run_exe,
            validate_only=args.validate_only,
        )
        return 0
    parser.error(message=f"Unhandled command {args.command}")
    return 1


def _run_demo(output: Path, overwrite: bool) -> None:
    project: Hy8Project = Hy8Project(title="run-hy8 demo project", designer="Codex scaffolding")
    crossing: CulvertCrossing = CulvertCrossing(name="Demo Crossing")
    crossing.notes = "Automatically generated demo crossing."
    crossing.flow = FlowDefinition(
        method=FlowMethod.MIN_DESIGN_MAX,
        minimum=5.0,
        design=10.0,
        maximum=15.0,
        user_values=[5.0, 10.0, 15.0],
    )
    crossing.tailwater = TailwaterDefinition(invert_elevation=99.0, constant_elevation=100.5)
    crossing.roadway = RoadwayProfile(
        width=40.0,
        stations=[-20.0, 0.0, 20.0],
        elevations=[102.0, 101.5, 102.0],
    )
    crossing.culverts.append(
        CulvertBarrel(
            name="Demo Culvert",
            span=4.0,
            rise=4.0,
            inlet_invert_elevation=99.0,
            outlet_invert_elevation=98.5,
        )
    )
    project.crossings.append(crossing)
    writer: Hy8FileWriter = Hy8FileWriter(project)
    path: Path = writer.write(output, overwrite=overwrite)
    print(f"Wrote demo HY-8 file to {path}")


def _run_build(
    config_path: Path,
    output: Path,
    overwrite: bool,
    exe_path: Path | None,
    validate_only: bool,
) -> None:
    try:
        project: Hy8Project = _load_project(config_path)
        _validate_project(project)
    except ValueError as exc:
        raise SystemExit(f"Invalid configuration: {exc}") from exc

    if validate_only:
        print(f"{config_path} is valid.")
        return

    writer: Hy8FileWriter = Hy8FileWriter(project=project)
    hy8_path: Path = writer.write(output_path=output, overwrite=overwrite)
    print(f"Wrote HY-8 file to {hy8_path}")
    if exe_path is not None:
        executor: Hy8Executable = Hy8Executable(exe_path=exe_path)
        result: CompletedProcess[str] = executor.open_run_save(hy8_file=hy8_path)
        if result.stdout.strip():
            print(result.stdout.strip())
        if result.stderr.strip():
            print(result.stderr.strip())


def _load_project(config_path: Path) -> Hy8Project:
    suffix: str = config_path.suffix.lower()
    if suffix == ".json":
        return load_project_from_json(config_path)
    raise ValueError(f"Unsupported configuration extension '{config_path.suffix}'. Use .json.")


def _validate_project(project: Hy8Project) -> None:
    errors: list[str] = project.validate()
    if errors:
        raise ValueError("Validation failed:\n" + "\n".join(errors))
