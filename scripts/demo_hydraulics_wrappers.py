"""Showcase the headwater helpers using the bundled HY-8 example project."""

from __future__ import annotations

import argparse
import math
import sys
from pathlib import Path
from typing import Iterable

ROOT = Path(__file__).resolve().parent.parent
SRC_ROOT = ROOT / "src"
for path in (ROOT, SRC_ROOT):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from run_hy8 import (  # noqa: E402
    CulvertBarrel,
    CulvertCrossing,
    CulvertMaterial,
    CulvertShape,
    FlowDefinition,
    FlowMethod,
    Hy8Project,
    InletEdgeType,
    InletType,
    ImprovedInletEdgeType,
    RoadwaySurface,
    UnitSystem,
    load_project_from_hy8,
)
from run_hy8.hydraulics import crossing_hw_from_q  # noqa: E402

EXAMPLE_FILE: Path = ROOT / "tests" / "example_crossings.hy8"
REFERENCE_NAME = "HDPE 900x11"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Demonstrate q_from_hw, q_for_hwd, and crossing_hw_from_q using "
            "the HDPE 900x11 crossing from tests/example_crossings.hy8."
        )
    )
    parser.add_argument(
        "--hy8",
        type=Path,
        help="Optional path to HY864.exe. Defaults to HY8_PATH.txt / HY8_EXE when omitted.",
    )
    parser.add_argument(
        "--flow",
        type=float,
        default=300.0,
        help="Discharge used for hw_from_q / crossing_hw_from_q (default: 300.0).",
    )
    parser.add_argument(
        "--hw-d",
        type=float,
        dest="hw_d_ratio",
        default=1.0,
        help="Headwater-to-diameter ratio for q_for_hwd (default: 1.0).",
    )
    return parser.parse_args()


def load_reference_crossing() -> tuple[Hy8Project, CulvertCrossing]:
    if not EXAMPLE_FILE.exists():
        raise FileNotFoundError(f"Example HY-8 file not found: {EXAMPLE_FILE}")
    project: Hy8Project = load_project_from_hy8(EXAMPLE_FILE)
    crossing = next((item for item in project.crossings if item.name == REFERENCE_NAME), None)
    if crossing is None:
        raise RuntimeError(f"Crossing '{REFERENCE_NAME}' was not found in {EXAMPLE_FILE}")
    return project, crossing


def build_manual_crossing() -> tuple[Hy8Project, CulvertCrossing]:
    project = Hy8Project(title="Manual HDPE example", units=UnitSystem.SI, exit_loss_option=0)
    crossing = CulvertCrossing(name=REFERENCE_NAME)

    flow = FlowDefinition(method=FlowMethod.USER_DEFINED)
    for value, label in (
        (282.517334, "q"),
        (317.832, "w"),
        (353.146667, "e"),
    ):
        flow.add_user_flow(value, label)
    crossing.flow = flow

    crossing.tailwater.set_constant(elevation=0.0, invert=0.0)

    crossing.roadway.width = 32.808399
    crossing.roadway.surface = RoadwaySurface.PAVED
    crossing.roadway.stations = [0.0, 32.808399]
    crossing.roadway.elevations = [30.183727, 30.183727]

    barrel = CulvertBarrel(
        name="Culvert 1",
        span=2.952756,
        rise=2.952756,
        shape=CulvertShape.CIRCLE,
        material=CulvertMaterial.HDPE,
        number_of_barrels=11,
        inlet_invert_station=0.0,
        inlet_invert_elevation=0.656168,
        outlet_invert_station=82.020997,
        outlet_invert_elevation=0.0,
        inlet_type=InletType.STRAIGHT,
        inlet_edge_type=InletEdgeType.THIN_EDGE_PROJECTING,
        improved_inlet_edge_type=ImprovedInletEdgeType.TYPE_1,
    )
    crossing.culverts.append(barrel)
    project.crossings.append(crossing)
    return project, crossing


def show_crossing_summary(title: str, crossing: CulvertCrossing) -> None:
    print(title)
    print(f"  Flow values: {format_sequence(crossing.flow.sequence())}")
    print(f"  Flow labels: {crossing.flow.user_value_labels}")
    print(
        f"  Tailwater elevation: {crossing.tailwater.constant_elevation:.3f} "
        f"(invert {crossing.tailwater.invert_elevation:.3f})"
    )
    print(f"  Roadway width: {crossing.roadway.width:.3f}")
    print(f"  Roadway stations: {format_sequence(crossing.roadway.stations)}")
    print(f"  Roadway elevations: {format_sequence(crossing.roadway.elevations)}")
    if crossing.culverts:
        barrel = crossing.culverts[0]
        print(
            f"  Culvert span/rise: {barrel.span:.6f} m x {barrel.rise:.6f} m "
            f"(material {barrel.material.name}, barrels {barrel.number_of_barrels})"
        )
        print(
            f"  Inlet/outlet invert: {barrel.inlet_invert_elevation:.6f} -> "
            f"{barrel.outlet_invert_elevation:.6f}"
        )
        print(
            f"  Inlet geometry: {barrel.inlet_type.name}, edge {barrel.inlet_edge_type.name}, "
            f"improved {barrel.improved_inlet_edge_type.name}"
        )


def ensure_manual_matches(reference: CulvertCrossing, manual: CulvertCrossing) -> None:
    checks: list[tuple[str, bool]] = [
        ("Flow values", sequences_close(reference.flow.sequence(), manual.flow.sequence())),
        ("Flow labels", reference.flow.user_value_labels == manual.flow.user_value_labels),
        (
            "Tailwater elevation",
            almost_equal(reference.tailwater.constant_elevation, manual.tailwater.constant_elevation),
        ),
        (
            "Tailwater invert",
            almost_equal(reference.tailwater.invert_elevation, manual.tailwater.invert_elevation),
        ),
        ("Roadway width", almost_equal(reference.roadway.width, manual.roadway.width)),
        ("Roadway stations", sequences_close(reference.roadway.stations, manual.roadway.stations)),
        ("Roadway elevations", sequences_close(reference.roadway.elevations, manual.roadway.elevations)),
    ]
    if reference.culverts and manual.culverts:
        ref_barrel = reference.culverts[0]
        manual_barrel = manual.culverts[0]
        checks.extend(
            [
                ("Culvert span", almost_equal(ref_barrel.span, manual_barrel.span)),
                ("Culvert rise", almost_equal(ref_barrel.rise, manual_barrel.rise)),
                ("Culvert material", ref_barrel.material is manual_barrel.material),
                ("Culvert barrels", ref_barrel.number_of_barrels == manual_barrel.number_of_barrels),
                ("Inlet invert", almost_equal(ref_barrel.inlet_invert_elevation, manual_barrel.inlet_invert_elevation)),
                ("Outlet invert", almost_equal(ref_barrel.outlet_invert_elevation, manual_barrel.outlet_invert_elevation)),
                ("Inlet type", ref_barrel.inlet_type is manual_barrel.inlet_type),
                ("Inlet edge type", ref_barrel.inlet_edge_type is manual_barrel.inlet_edge_type),
                (
                    "Improved inlet edge",
                    ref_barrel.improved_inlet_edge_type is manual_barrel.improved_inlet_edge_type,
                ),
            ]
        )
    mismatches = [label for label, matches in checks if not matches]
    if mismatches:
        joined = ", ".join(mismatches)
        raise ValueError(f"Manual crossing does not match reference fields: {joined}")


def run_wrapper_examples(
    *,
    label: str,
    project: Hy8Project,
    crossing: CulvertCrossing,
    hy8_path: Path | None,
    flow: float,
    hw_d_ratio: float,
) -> None:
    print(f"\nHydraulics helper output for {label}:")

    hw_result = crossing.hw_from_q(q=flow, hy8=hy8_path, project=project)
    print(f"  hw_from_q: flow {hw_result.computed_flow:.3f} -> HW {hw_result.computed_headwater:.3f}")

    func_result = crossing_hw_from_q(crossing=crossing, q=flow, hy8=hy8_path, project=project)
    delta = abs(func_result.computed_headwater - hw_result.computed_headwater)
    print(
        f"  crossing_hw_from_q: HW {func_result.computed_headwater:.3f} "
        f"(diff vs method {delta:.6f})"
    )

    target_hw = hw_result.computed_headwater
    q_result = crossing.q_from_hw(hw=target_hw, q_hint=flow, hy8=hy8_path, project=project)
    print(f"  q_from_hw: target HW {target_hw:.3f} -> flow {q_result.computed_flow:.3f}")

    ratio_result = crossing.q_for_hwd(hw_d_ratio=hw_d_ratio, q_hint=flow, hy8=hy8_path, project=project)
    if ratio_result.requested_headwater is not None:
        print(
            f"  q_for_hwd: HW/D {hw_d_ratio:.3f} "
            f"-> flow {ratio_result.computed_flow:.3f}, HW {ratio_result.requested_headwater:.3f}"
        )
    else:
        print(f"  q_for_hwd: HW/D {hw_d_ratio:.3f} -> flow {ratio_result.computed_flow:.3f}")


def format_sequence(values: Iterable[float]) -> str:
    return ", ".join(f"{value:.6f}" for value in values)


def almost_equal(a: float, b: float, *, tolerance: float = 1e-6) -> bool:
    return math.isclose(a, b, abs_tol=tolerance)


def sequences_close(values: Iterable[float], others: Iterable[float], *, tolerance: float = 1e-6) -> bool:
    a = list(values)
    b = list(others)
    if len(a) != len(b):
        return False
    return all(math.isclose(x, y, abs_tol=tolerance) for x, y in zip(a, b))


def main() -> None:
    args = parse_args()
    if args.hy8 and not args.hy8.exists():
        raise FileNotFoundError(f"HY-8 executable not found: {args.hy8}")

    print(f"Loading reference project from {EXAMPLE_FILE}")
    reference_project, reference_crossing = load_reference_crossing()
    manual_project, manual_crossing = build_manual_crossing()

    show_crossing_summary("\nReference crossing parameters", reference_crossing)
    show_crossing_summary("\nManual reconstruction", manual_crossing)
    ensure_manual_matches(reference_crossing, manual_crossing)
    print("\nManual crossing matches the HY-8 file values.")

    run_wrapper_examples(
        label="HY-8 file crossing",
        project=reference_project,
        crossing=reference_crossing,
        hy8_path=args.hy8,
        flow=args.flow,
        hw_d_ratio=args.hw_d_ratio,
    )
    run_wrapper_examples(
        label="manual crossing",
        project=manual_project,
        crossing=manual_crossing,
        hy8_path=args.hy8,
        flow=args.flow,
        hw_d_ratio=args.hw_d_ratio,
    )


if __name__ == "__main__":
    main()
