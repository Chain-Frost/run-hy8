"""Helpers for invoking the HY-8 executable on Windows."""

from __future__ import annotations

import os
import subprocess
from pathlib import Path
from _collections_abc import Sequence

from .hy8_path import resolve_hy8_path, save_hy8_path
from .classes_references import UnitSystem


class Hy8Executable:
    """
    A thin wrapper around the HY-8 command-line interface.

    This class provides methods to invoke the HY-8 executable with various
    automation switches for running analyses and generating reports. It also
    handles locating the executable on the system.

    Attributes:
        exe_path: The path to the resolved HY-8 executable.
    """

    _default_path: Path | None = None

    def __init__(self, exe_path: Path | None = None) -> None:
        """
        Initializes the Hy8Executable instance.

        Args:
            exe_path: An optional path to a specific HY-8 executable. If not
                provided, the path is resolved from environment variables, a
                configuration file, or the default installation location.
        """
        resolved: Path = Path(exe_path) if exe_path is not None else self.default_path()
        self.exe_path: Path = resolved
        self._ensure_windows()
        self._ensure_exists()

    @classmethod
    def default_path(cls) -> Path:
        """
        Return the configured default HY-8 executable path.

        The path is cached at the class level after the first resolution.
        """
        if cls._default_path is not None:
            return cls._default_path
        return resolve_hy8_path()

    @classmethod
    def configure_default_path(cls, path: Path) -> None:
        """
        Override the default HY-8 path for the current session.

        This does not persist the path to disk.

        Args:
            path: The path to set as the default for this class.
        """
        cls._default_path = Path(path)

    @classmethod
    def persist_default_path(cls, path: Path) -> Path:
        """
        Override and persist the default HY-8 path into HY8_PATH.txt.

        Args:
            path: The path to save to the configuration file.

        Returns:
            The path to the configuration file where the path was saved.
        """
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
        """
        Generate flow-tailwater tables using the -BuildFlowTwTable switch.

        Args:
            hy8_file: The path to the .hy8 project file.
            flow_coef: The flow coefficient.
            flow_const: The flow constant.
            unit_system: The unit system to use for the analysis.
            hw_increment: The headwater increment.
            tw_increment: The tailwater increment.
            check: If True, raises an exception if HY-8 returns a non-zero exit code.

        Returns:
            The completed subprocess result.
        """
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
        """
        Build headwater and tailwater tables using the -BuildHwTwTable switch.

        Args:
            hy8_file: The path to the .hy8 project file.
            unit_system: The unit system to use for the analysis.
            hw_increment: The headwater increment.
            tw_increment: The tailwater increment.
            check: If True, raises an exception if HY-8 returns a non-zero exit code.

        Returns:
            The completed subprocess result.
        """
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
