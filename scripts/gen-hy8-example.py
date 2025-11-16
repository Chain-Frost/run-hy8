from pathlib import Path

from run_hy8 import Hy8FileWriter, load_project_from_hy8
from run_hy8.models import Hy8Project

root: Path = Path(__file__).resolve().parent.parent
source: Path = root / "tests" / "example_crossings.hy8"
output: Path = root / "tests" / "example_crossings_roundtrip.hy8"

project: Hy8Project = load_project_from_hy8(path=source)
Hy8FileWriter(project=project).write(output_path=output)
