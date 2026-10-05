"""Create a multi-crossing project for a user-operated HY-8 GUI comparison."""

from __future__ import annotations

import argparse
import copy
import sys
import uuid
from pathlib import Path

from run_hy8.models.culvert_crossing import CulvertCrossing

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from run_hy8 import Hy8FileWriter, Hy8Project, RoadwayShape, RoadwaySurface, load_project_from_hy8


def build_review_project(fixture: Path) -> Hy8Project:
    """Retain the user's geometry and vary only the named test inputs."""
    project: Hy8Project = load_project_from_hy8(fixture)
    original: CulvertCrossing = copy.deepcopy(project.crossings[0])
    project.title = "Roadway GUI and command-line comparison"
    project.notes = "Adapter-generated test inputs. Save a separate copy from the GUI for comparison."
    project.crossings.clear()
    for group, shape, surface, flows in [
        ("Original-3Q", RoadwayShape.IRREGULAR, RoadwaySurface.PAVED, [8, 30, 100]),
        ("Irregular-6Q", RoadwayShape.IRREGULAR, RoadwaySurface.PAVED, [1, 2, 4, 8, 30, 100]),
        ("Irregular-C1.6", RoadwayShape.IRREGULAR, RoadwaySurface.USER_DEFINED, [1, 2, 4, 8, 30, 100]),
        ("Irregular-Gravel", RoadwayShape.IRREGULAR, RoadwaySurface.GRAVEL, [1, 2, 4, 8, 30, 100]),
        ("Constant-6Q", RoadwayShape.CONSTANT, RoadwaySurface.PAVED, [1, 2, 4, 8, 30, 100]),
    ]:
        for condition, tailwater in [("Free", 12.0), ("Submerged", 19.2)]:
            crossing: CulvertCrossing = copy.deepcopy(original)
            crossing.name = f"{group}-{condition}"
            crossing.uuid = str(uuid.uuid5(uuid.NAMESPACE_URL, f"run-hy8/roadway-review/{crossing.name}"))
            crossing.notes = f"{group}; constant tailwater {tailwater} m; flows in m3/s."
            crossing.flow.user_values = list(flows)
            crossing.flow.user_value_labels = [f"Q{flow}" for flow in flows]
            crossing.tailwater.constant_elevation = tailwater
            crossing.roadway.shape = shape
            crossing.roadway.surface = surface
            crossing.roadway.discharge_coefficient = 1.6 if surface == RoadwaySurface.USER_DEFINED else 0.0
            if shape == RoadwayShape.CONSTANT:
                crossing.roadway.stations = [original.roadway.stations[0], original.roadway.stations[-1]]
                crossing.roadway.elevations = [original.roadway.crest_elevation()] * 2
            project.crossings.append(crossing)
    return project


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fixture", type=Path, default=ROOT / "tests" / "floodway.hy8")
    parser.add_argument("--output", type=Path, default=ROOT / "tests" / "fixtures" / "roadway_gui_review.hy8")
    args = parser.parse_args()
    project: Hy8Project = build_review_project(args.fixture)
    output: Path = Hy8FileWriter(project).write(args.output, overwrite=False)
    print(f"Wrote {len(project.crossings)} crossings to {output}")


if __name__ == "__main__":
    main()
