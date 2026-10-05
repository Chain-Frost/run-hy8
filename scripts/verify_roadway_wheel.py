"""Verify roadway wheel, source snapshot, installed files and isolated import."""

from __future__ import annotations

import argparse
import hashlib
import importlib.metadata
import json
import site
import sys
import zipfile
from pathlib import Path


def fail(message: str) -> None:
    raise ValueError(message)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--wheel", type=Path, required=True)
    parser.add_argument("--installed", type=Path, required=True)
    parser.add_argument("--source", type=Path, default=Path(__file__).resolve().parents[1] / "src")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    installed = args.installed.resolve()
    files: dict[str, str] = {}
    with zipfile.ZipFile(args.wheel) as wheel:
        for name in wheel.namelist():
            if not name.startswith("run_hy8/") or not name.endswith((".py", "py.typed")):
                continue
            data = wheel.read(name)
            for root in [args.source.resolve(), installed]:
                path = root / name
                # Wheel/Windows installation may normalize newline bytes.
                if not path.exists() or path.read_bytes().replace(b"\r\n", b"\n") != data.replace(b"\r\n", b"\n"):
                    fail(f"Wheel mismatch: {path}")
            files[name] = hashlib.sha256(data).hexdigest()
    if "run_hy8/overtopping.py" not in files or "run_hy8/py.typed" not in files:
        fail("Wheel is missing roadway implementation or typing marker.")
    # -I excludes cwd/PYTHONPATH/user site. Explicitly expose installed runtime
    # dependencies after the target package; no checkout path is added.
    sys.path[:0] = [str(installed), site.getusersitepackages()]
    run_hy8 = importlib.import_module("run_hy8")

    if Path(run_hy8.__file__).resolve().parent != installed / "run_hy8":
        fail("Import did not resolve to the isolated wheel install.")
    road = run_hy8.RoadwayProfile(
        width=10,
        stations=[0, 20],
        elevations=[12, 12],
        surface=run_hy8.RoadwaySurface.USER_DEFINED,
        discharge_coefficient=1.6,
    )
    road.assert_valid()
    restored = run_hy8.RoadwayProfile.from_dict(road.to_dict())
    if restored.discharge_coefficient != 1.6:
        fail("Installed wheel coefficient smoke test failed.")
    distribution = importlib.metadata.distribution("run-hy8")
    if distribution.version != "2026.10.5.1":
        fail(f"Unexpected installed distribution version: {distribution.version}")
    evidence = {
        "version": distribution.version,
        "wheel_sha256": hashlib.sha256(args.wheel.read_bytes()).hexdigest(),
        "wheel_files_sha256": files,
        "source_text_matches_wheel": True,
        "installed_text_matches_wheel": True,
        "isolated_import_verified": True,
        "isolated_mode": sys.flags.isolated,
    }
    args.output.write_text(json.dumps(evidence, indent=2), encoding="utf-8")
    print(f"Verified {len(files)} package files, isolated import and roadway smoke test: {distribution.version}")


if __name__ == "__main__":
    main()
