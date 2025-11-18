"""Helpers for invoking the HY-8 executable on Windows."""

from __future__ import annotations

import os
import subprocess
from pathlib import Path
from typing import Sequence

from .hy8_path import resolve_hy8_path, save_hy8_path
from .models import UnitSystem


class Hy8Executable:
    """Thin wrapper around the HY-8 command line switches."""

    _default_path: Path | None = None

    def __init__(self, exe_path: Path | None = None) -> None:
        resolved: Path = Path(exe_path) if exe_path is not None else self.default_path()
        self.exe_path: Path = resolved
        self._ensure_windows()
        self._ensure_exists()

    @classmethod
    def default_path(cls) -> Path:
        """Return the configured default HY-8 executable path."""
        if cls._default_path is not None:
            return cls._default_path
        return resolve_hy8_path()

    @classmethod
    def configure_default_path(cls, path: Path) -> None:
        """Override the default HY-8 path used when none is provided."""
        cls._default_path = Path(path)

    @classmethod
    def persist_default_path(cls, path: Path) -> Path:
        """Override and persist the default HY-8 path into HY8_PATH.txt."""
        destination: Path = save_hy8_path(path=path)
        cls.configure_default_path(path=path)
        return destination

    def run(self, hy8_file: Path, *args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
        """Invoke HY-8 with a custom list of switches."""
        return self._execute(hy8_file=hy8_file, args=list(args), check=check)

    def build_full_report(self, hy8_file: Path, check: bool = True) -> subprocess.CompletedProcess[str]:
        """Trigger HY-8's -BuildFullReport automation hook."""
        return self._execute(hy8_file=hy8_file, args=["-BuildFullReport"], check=check)

    def open_run_save(self, hy8_file: Path, check: bool = True) -> subprocess.CompletedProcess[str]:
        """Open and re-run the project in HY-8 using the -OpenRunSave switch."""
        return self._execute(hy8_file=hy8_file, args=["-OpenRunSave"], check=check)

    def open_run_save_plots(self, hy8_file: Path, check: bool = True) -> subprocess.CompletedProcess[str]:
        """Open, rerun, and capture plots via the -OpenRunSavePlots switch."""
        return self._execute(hy8_file=hy8_file, args=["-OpenRunSavePlots"], check=check)

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
        """Generate flow-tailwater tables by automating the HY-8 CLI."""
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
        return self._execute(hy8_file=hy8_file, args=args, check=check)

    def build_hw_tw_table(
        self,
        hy8_file: Path,
        *,
        unit_system: UnitSystem = UnitSystem.ENGLISH,
        hw_increment: float = 0.25,
        tw_increment: float = 0.25,
        check: bool = True,
    ) -> subprocess.CompletedProcess[str]:
        """Build headwater and tailwater tables for the provided project."""
        args: list[str] = [
            "-BuildHwTwTable",
            "UNITS",
            unit_system.cli_flag,
            "HWINC",
            str(hw_increment),
            "TWINC",
            str(tw_increment),
        ]
        return self._execute(hy8_file=hy8_file, args=args, check=check)

    def _execute(self, hy8_file: Path, args: Sequence[str], *, check: bool) -> subprocess.CompletedProcess[str]:
        """Run HY-8 with shared validation and capture stdout/stderr."""
        hy8_file = hy8_file.with_suffix(".hy8")
        if not hy8_file.exists():
            raise FileNotFoundError(f"HY-8 project not found: {hy8_file}")
        command: list[str] = [str(self.exe_path), *args, str(hy8_file)]
        return subprocess.run(command, check=check, capture_output=True, text=True)

    @staticmethod
    def _ensure_windows() -> None:
        """Make sure the caller is on Windows before shelling out."""
        if os.name != "nt":
            raise OSError("The HY-8 executable is only available on Windows.")

    def _ensure_exists(self) -> None:
        """Ensure the resolved executable path exists before invoking."""
        if not self.exe_path.exists():
            raise FileNotFoundError(f"HY-8 executable not found: {self.exe_path}")
