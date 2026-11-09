"""Reproduce issue #19 using the retained assumed tutorial input, in a fresh workspace.

Run with the published installed package and --baseline first; then use the
candidate source or isolated installed wheel without --baseline. No GUI needed.
"""

# This bounded diagnostic deliberately instruments private search state.
# ruff: noqa: INP001, SLF001
# pyright: reportPrivateUsage=false

from __future__ import annotations

import argparse
import hashlib
import importlib.metadata
import json
import re
import shutil
import sys
from pathlib import Path
from typing import Any

from loguru import logger

from run_hy8 import hydraulics, load_project_from_hy8
from run_hy8.hydraulics import FlowSearchError
from run_hy8.results import Hy8ResultRow
from run_hy8.units import cfs_to_cms


def sha256(path: Path) -> str:
    """Hash retained bytes without modifying them."""
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    """Run the bounded reproduction and retain its evidence."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workspace", type=Path, required=True, help="New directory; existing paths are refused.")
    parser.add_argument("--baseline", action="store_true", help="Expect the published 2026.10.18.2 premature success.")
    args = parser.parse_args()
    root: Path = args.workspace.absolute()
    source = Path(__file__).absolute().with_name("input.hy8")
    executable = Path("C:/Program Files/HY-8 8.00/HY864.exe")
    if sha256(source) != "b71007d8dc863703fd7177d05017aae9e1c2e101be3f416a02ccf02398a872cf":
        msg = "Input fixture hash mismatch"
        raise ValueError(msg)
    if sha256(executable) != "0b1c5e7fb6b48be9c675b5486ae9a84346f436c5c649aa5ed09a1552267ee806":
        msg = "Requires the verified HY-8 8.0.1.2 executable"
        raise ValueError(msg)
    if args.baseline and importlib.metadata.version("run-hy8") != "2026.10.18.2":
        msg = "Baseline requires installed run-hy8==2026.10.18.2"
        raise ValueError(msg)
    root.mkdir(parents=True, exist_ok=False)
    logger.remove()
    project = load_project_from_hy8(source)
    crossing = project.crossings[0]
    candidates: list[dict[str, float]] = []
    original = hydraulics._FlowSearch.record

    def record(self: hydraulics._FlowSearch, flow: float, row: Hy8ResultRow) -> hydraulics._FlowSample:
        candidates.append({"requested_q": flow, "parsed_q": row.flow, "rst_hw": row.headwater_elevation})
        return original(self, flow, row)

    hydraulics._FlowSearch.record = record
    try:
        try:
            result = crossing.q_from_hw(
                43.5636, q_hint=1.0, project=project, hy8=executable, workspace=root / "inverse", keep_files=True
            )
        except FlowSearchError as error:
            if args.baseline:
                raise
            inverse: dict[str, Any] = {"outcome": "FlowSearchError", "message": str(error)}
        else:
            if not args.baseline or result.computed_flow != 0.05:
                msg = "Unexpected inverse success"
                raise AssertionError(msg)
            inverse = {"outcome": "success", "q": result.computed_flow, "hw": result.computed_headwater}
    finally:
        hydraulics._FlowSearch.record = original
    forward: list[dict[str, float]] = []
    for q in (0.05, 0.10, 0.149540795, 0.20):
        result = crossing.hw_from_q(q, project=project, hy8=executable, workspace=root / f"q-{q}", keep_files=True)
        plot = next((root / f"q-{q}").glob("*.plt")).read_text()
        profiles = re.split(r"(?m)^FlowProfile: \d+", plot)[1:]

        def profile_distance(block: str, target: float = q) -> float:
            match = re.search(r"FlowProfileFlow: (\S+)", block)
            if match is None:
                message = "Missing PLT flow identifier"
                raise ValueError(message)
            return abs(cfs_to_cms(float(match[1])) - target)

        profile = min(
            profiles,
            key=profile_distance,
        )
        heads = re.findall(r"Series:\s*Headwater\s+point:\s*\S+\s+(\S+)", profile)
        if len(heads) != 1:
            msg = "Expected one PLT Headwater series"
            raise AssertionError(msg)
        forward.append({"requested_q": q, "rst_hw": result.computed_headwater, "plt_hw": float(heads[0])})
    if [row["rst_hw"] for row in forward] != [43.56, 43.56, 43.56, 43.57]:
        msg = "Native RST reproduction differs"
        raise AssertionError(msg)
    # A well-conditioned circular inverse remains usable with the same geometry.
    well = crossing.hw_from_q(1.0, project=project, hy8=executable, workspace=root / "well-forward", keep_files=True)
    resolved = crossing.q_from_hw(
        well.computed_headwater,
        q_hint=1.0,
        project=project,
        hy8=executable,
        workspace=root / "well-inverse",
        keep_files=True,
    )
    if abs(resolved.computed_flow - 1.0) > 0.02:
        msg = "Well-conditioned inverse regressed"
        raise AssertionError(msg)
    shutil.copyfile(source, root / "input.hy8")
    payload = {
        "python": sys.version,
        "distribution_metadata_version": importlib.metadata.version("run-hy8"),
        "hydraulics_sha256": sha256(Path(hydraulics.__file__)),
        "executable_sha256": sha256(executable),
        "input_sha256": sha256(source),
        "target_hw_m": 43.5636,
        "tailwater_m": 43.5542,
        "inverse": inverse,
        "candidates": candidates,
        "forward": forward,
        "well_conditioned_inverse_q": resolved.computed_flow,
        "artifacts": {
            path.relative_to(root).as_posix(): sha256(path) for path in sorted(root.rglob("*")) if path.is_file()
        },
    }
    (root / "evidence.json").write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"workspace": str(root), "inverse": inverse, "forward": forward}, indent=2))


if __name__ == "__main__":
    main()
