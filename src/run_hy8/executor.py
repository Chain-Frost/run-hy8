"""Helpers for invoking the HY-8 executable on Windows."""

from __future__ import annotations

import os
import subprocess
from pathlib import Path
from typing import Sequence

from .models import UnitSystem


class Hy8Executable:
    """Thin wrapper around the HY-8 command line switches."""

    def __init__(self, exe_path: Path) -> None:
        self.exe_path: Path = exe_path
        self._ensure_windows()
        self._ensure_exists()

    def run(self, hy8_file: Path, *args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
        return self._execute(hy8_file, list(args), check=check)

    def build_full_report(self, hy8_file: Path, check: bool = True) -> subprocess.CompletedProcess[str]:
        return self._execute(hy8_file, ["-BuildFullReport"], check=check)

    def open_run_save(self, hy8_file: Path, check: bool = True) -> subprocess.CompletedProcess[str]:
        return self._execute(hy8_file, ["-OpenRunSave"], check=check)

    def open_run_save_plots(self, hy8_file: Path, check: bool = True) -> subprocess.CompletedProcess[str]:
        return self._execute(hy8_file, ["-OpenRunSavePlots"], check=check)

    def build_flow_tw_table(
        self,
        hy8_file: Path,
        *,
        flow_coef: float = 1.1,
        flow_const: float = 0.25,
        unit_system: UnitSystem = UnitSystem.ENGLISH,
        hw_increment: float = 0.25,
        tw_increment: float = 0.25,
        check: bool = True,
    ) -> subprocess.CompletedProcess[str]:
        args: list[str] = [
            "-BuildFlowTwTable",
            "FLOWCOEF",
            str(flow_coef),
            "FLOWCONST",
            str(flow_const),
            "UNITS",
            unit_system.cli_flag,
            "HWINC",
            str(hw_increment),
            "TWINC",
            str(tw_increment),
        ]
        return self._execute(hy8_file, args, check=check)

    def build_hw_tw_table(
        self,
        hy8_file: Path,
        *,
        unit_system: UnitSystem = UnitSystem.ENGLISH,
        hw_increment: float = 0.25,
        tw_increment: float = 0.25,
        check: bool = True,
    ) -> subprocess.CompletedProcess[str]:
        args: list[str] = [
            "-BuildHwTwTable",
            "UNITS",
            unit_system.cli_flag,
            "HWINC",
            str(hw_increment),
            "TWINC",
            str(tw_increment),
        ]
        return self._execute(hy8_file, args, check=check)

    def _execute(self, hy8_file: Path, args: Sequence[str], *, check: bool) -> subprocess.CompletedProcess[str]:
        hy8_file = hy8_file.with_suffix(".hy8")
        if not hy8_file.exists():
            raise FileNotFoundError(f"HY-8 project not found: {hy8_file}")
        command: list[str] = [str(self.exe_path), *args, str(hy8_file)]
        return subprocess.run(command, check=check, capture_output=True, text=True)

    @staticmethod
    def _ensure_windows() -> None:
        if os.name != "nt":
            raise OSError("The HY-8 executable is only available on Windows.")

    def _ensure_exists(self) -> None:
        if not self.exe_path.exists():
            raise FileNotFoundError(f"HY-8 executable not found: {self.exe_path}")
