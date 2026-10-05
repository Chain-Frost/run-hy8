"""Verify wheel identity, metadata, licence and exact package contents."""

from __future__ import annotations

import argparse
import hashlib
import re
import tomllib
import zipfile
from email.parser import BytesParser
from pathlib import Path

from packaging.version import Version

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def project_metadata(root: Path) -> dict[str, str]:
    return tomllib.loads((root / "pyproject.toml").read_text(encoding="utf-8"))["project"]


def expected_filename(root: Path) -> str:
    project = project_metadata(root)
    name = re.sub(r"[-_.]+", "_", project["name"])
    return f"{name}-{Version(project['version'])}-py3-none-any.whl"


def verify_wheel(wheel: Path, root: Path = PROJECT_ROOT) -> None:
    project = project_metadata(root)
    if wheel.name != expected_filename(root):
        msg = f"Unexpected wheel filename: {wheel.name}"
        raise ValueError(msg)
    info = wheel.name.removesuffix("-py3-none-any.whl") + ".dist-info"
    with zipfile.ZipFile(wheel) as archive:
        members = archive.namelist()
        names = set(members)
        if len(names) != len(members) or archive.testzip() is not None:
            msg = "Wheel contains duplicate or corrupt members"
            raise ValueError(msg)
        metadata = BytesParser().parsebytes(archive.read(f"{info}/METADATA"))
        for field, expected in {
            "Name": project["name"],
            "Version": str(Version(project["version"])),
            "License-Expression": project["license"],
            "License-File": "LICENSE",
            "Requires-Python": project["requires-python"],
        }.items():
            if metadata.get_all(field) != [expected]:
                msg = f"Wheel metadata mismatch: {field}"
                raise ValueError(msg)
        license_content = archive.read(f"{info}/licenses/LICENSE").replace(b"\r\n", b"\n")
        if license_content != (root / "LICENSE").read_bytes().replace(b"\r\n", b"\n"):
            msg = "Wheel LICENSE differs from repository LICENSE"
            raise ValueError(msg)
        source = root / "src" / "run_hy8"
        required = {
            f"run_hy8/{path.relative_to(source).as_posix()}": path
            for path in source.rglob("*")
            if path.is_file() and path.suffix in (".py", ".typed")
        }
        if "run_hy8/py.typed" not in names:
            msg = "Wheel is missing py.typed"
            raise ValueError(msg)
        allowed_info = {
            f"{info}/{name}" for name in ("METADATA", "WHEEL", "RECORD", "top_level.txt", "licenses/LICENSE")
        }
        unexpected = names - required.keys() - allowed_info
        if unexpected:
            msg = f"Wheel contains unexpected development or generated files: {sorted(unexpected)}"
            raise ValueError(msg)
        for name, path in required.items():
            if name not in names or archive.read(name) != path.read_bytes():
                msg = f"Wheel source missing or different: {name}"
                raise ValueError(msg)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("wheel", nargs="?", type=Path)
    args = parser.parse_args(argv)
    wheels = list((PROJECT_ROOT / "dist").glob("run_hy8-*.whl"))
    if args.wheel is None and len(wheels) != 1:
        parser.error("Expected exactly one retained run-hy8 wheel")
    wheel = args.wheel if args.wheel is not None else wheels[0]
    verify_wheel(wheel)
    print(f"Verified: {wheel.name} (sha256={hashlib.sha256(wheel.read_bytes()).hexdigest()})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
