"""Install into temporary storage and import outside the checkout with isolated Python."""

from __future__ import annotations

import argparse
import subprocess
import sys
import tempfile
from pathlib import Path

from verify_wheel import PROJECT_ROOT, verify_wheel

SMOKE_CODE = """
import importlib.metadata, importlib.resources, pathlib, sys
root = pathlib.Path(sys.argv[1]).resolve()
sys.path.insert(0, str(root))
import run_hy8
if not pathlib.Path(run_hy8.__file__).resolve().is_relative_to(root):
    raise RuntimeError('Import resolved outside isolated install')
if importlib.metadata.version('run-hy8') != sys.argv[2]:
    raise RuntimeError('Installed version differs')
if not importlib.resources.files('run_hy8').joinpath('py.typed').is_file():
    raise RuntimeError('Missing typed marker')
for name in run_hy8.__all__:
    getattr(run_hy8, name)
print('Installed-wheel smoke test passed')
"""


def smoke_test(wheel: Path) -> None:
    with tempfile.TemporaryDirectory(prefix="run-hy8-smoke-") as temporary:
        root = Path(temporary)
        target = root / "installed"
        subprocess.run(  # noqa: S603 - fixed Python pip command
            [sys.executable, "-m", "pip", "install", "--target", str(target), str(wheel.resolve())],
            cwd=root,
            check=True,
        )
        subprocess.run(  # noqa: S603 - fixed isolated Python smoke test
            [sys.executable, "-I", "-c", SMOKE_CODE, str(target), wheel.name.split("-")[1]],
            cwd=root,
            check=True,
        )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("wheel", nargs="?", type=Path)
    args = parser.parse_args()
    wheels = list((PROJECT_ROOT / "dist").glob("run_hy8-*.whl"))
    if args.wheel is None and len(wheels) != 1:
        parser.error("Expected exactly one retained wheel")
    wheel = args.wheel if args.wheel is not None else wheels[0]
    verify_wheel(wheel)
    smoke_test(wheel)


if __name__ == "__main__":
    main()
