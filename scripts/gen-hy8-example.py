from pathlib import Path
import sys

SCRIPT_DIR: Path = Path(__file__).resolve().parent
REPO_ROOT: Path = SCRIPT_DIR.parent
SRC_PATH: Path = REPO_ROOT / "src"
src_str: str = str(SRC_PATH)
if src_str not in sys.path:
    sys.path.insert(0, src_str)

from run_hy8 import Hy8FileWriter, load_project_from_hy8
from run_hy8.models import Hy8Project

root: Path = Path(__file__).resolve().parent.parent
source: Path = root / "tests" / "example_crossings.hy8"
output: Path = root / "tests" / "example_crossings_roundtrip.hy8"

project: Hy8Project = load_project_from_hy8(path=source)
Hy8FileWriter(project=project).write(output_path=output)
