"""Build and verify in unique staging before replacing retained wheels."""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

from verify_wheel import expected_filename, verify_wheel

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def run_build(source: Path, output: Path) -> None:
    subprocess.run(  # noqa: S603 - fixed Python build command
        [sys.executable, "-m", "build", "--wheel", "--outdir", str(output)], cwd=source, check=True
    )


def promote_wheel(wheel: Path, root: Path) -> Path:
    dist = root / "dist"
    dist.mkdir(exist_ok=True)
    destination = dist / wheel.name
    with tempfile.NamedTemporaryFile(dir=dist, prefix=".run-hy8-", suffix=".incoming", delete=False) as handle:
        incoming = Path(handle.name)
    try:
        shutil.copyfile(wheel, incoming)
        incoming.replace(destination)
    finally:
        incoming.unlink(missing_ok=True)
    for artifact in dist.glob("run_hy8-*.whl"):
        if artifact != destination:
            artifact.unlink()
    return destination


def build_and_promote(root: Path, *, stage_parent: Path | None = None) -> Path:
    # Metadata and generated state are only touched in this invocation's staging copy.
    with tempfile.TemporaryDirectory(prefix="run-hy8-build-", dir=stage_parent) as temporary:
        staging = Path(temporary)
        source = staging / "project"
        source.mkdir()
        for name in ("pyproject.toml", "README.md", "LICENSE"):
            shutil.copy2(root / name, source / name)
        shutil.copytree(
            root / "src", source / "src", ignore=shutil.ignore_patterns("__pycache__", "*.pyc", "*.pyo", "*.egg-info")
        )
        output = staging / "wheels"
        run_build(source, output)
        wheels = list(output.glob("*.whl"))
        expected = output / expected_filename(root)
        if wheels != [expected]:
            msg = f"Expected exactly one candidate named {expected.name}, found {[wheel.name for wheel in wheels]}"
            raise ValueError(msg)
        verify_wheel(expected, root)
        return promote_wheel(expected, root)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--skip-pip", action="store_true", help="Use the installed build frontend.")
    args = parser.parse_args(argv)
    try:
        if not args.skip_pip:
            subprocess.run([sys.executable, "-m", "pip", "install", "--upgrade", "build"], check=True)
        parent = os.environ.get("RUN_HY8_STAGE_ROOT")
        stage_parent = Path(parent) if parent else None
        if stage_parent is not None:
            stage_parent.mkdir(parents=True, exist_ok=True)
        wheel = build_and_promote(PROJECT_ROOT, stage_parent=stage_parent)
    except (OSError, ValueError, subprocess.CalledProcessError) as error:
        print(f"Build failed: {error}", file=sys.stderr)
        return 1
    print(f"Built and verified: {wheel}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
