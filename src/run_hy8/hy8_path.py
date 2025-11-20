"""Helpers for locating and configuring the HY-8 executable."""

from __future__ import annotations

import os
from pathlib import Path

CONFIG_FILENAME = "HY8_PATH.txt"
DEFAULT_INSTALL_PATH = Path(r"C:\Program Files\HY-8 8.00\HY864.exe")


def hy8_path_file() -> Path:
    """
    Return the path to the configuration file that stores the HY-8 executable location.

    This file is expected to be at the root of the project, two levels up
    from this source file.
    """
    return Path(__file__).resolve().parents[2] / CONFIG_FILENAME


def read_hy8_path_file() -> Path | None:
    """
    Read and return the path from the HY8_PATH.txt configuration file.

    Returns:
        The path to the HY-8 executable if the file exists and is not empty,
        otherwise None.
    """
    path_file: Path = hy8_path_file()
    if not path_file.exists():
        return None
    text: str = path_file.read_text(encoding="utf-8").strip()
    if not text:
        return None
    return Path(text.strip('"')).expanduser()


def save_hy8_path(path: Path) -> Path:
    """
    Persist a HY-8 executable path to the HY8_PATH.txt configuration file.

    Args:
        path: The path to the HY-8 executable to save.

    Returns:
        The path to the configuration file that was written.
    """
    destination: Path = hy8_path_file()
    destination.write_text(str(Path(path)), encoding="utf-8")
    return destination


def resolve_hy8_path() -> Path:
    """
    Resolve the HY-8 executable path from various sources in order of precedence.

    The resolution order is:
    1. `HY8_EXE` or `HY8_EXECUTABLE` environment variables.
    2. The path stored in the `HY8_PATH.txt` configuration file.
    3. The default installation path for HY-8 8.00.

    Returns:
        The resolved path to the HY-8 executable.
    """
    env: str | None = os.environ.get("HY8_EXE") or os.environ.get("HY8_EXECUTABLE")
    if env:
        return Path(env).expanduser()
    configured: Path | None = read_hy8_path_file()
    if configured:
        return configured
    return DEFAULT_INSTALL_PATH


__all__: list[str] = [
    "CONFIG_FILENAME",
    "DEFAULT_INSTALL_PATH",
    "hy8_path_file",
    "read_hy8_path_file",
    "resolve_hy8_path",
    "save_hy8_path",
]
