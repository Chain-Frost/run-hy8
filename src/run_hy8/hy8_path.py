"""Helpers for locating and configuring the HY-8 executable."""

from __future__ import annotations

import os
from pathlib import Path

CONFIG_FILENAME = "HY8_PATH.txt"
DEFAULT_INSTALL_PATH = Path(r"C:\Program Files\HY-8 8.00\HY864.exe")


def hy8_path_file() -> Path:
    """Return the repository-level file that records the HY-8 location."""
    return Path(__file__).resolve().parents[2] / CONFIG_FILENAME


def read_hy8_path_file() -> Path | None:
    """Return the path saved in HY8_PATH.txt, if present."""
    path_file: Path = hy8_path_file()
    if not path_file.exists():
        return None
    text: str = path_file.read_text(encoding="utf-8").strip()
    if not text:
        return None
    return Path(text.strip('"')).expanduser()


def save_hy8_path(path: Path) -> Path:
    """Persist a HY-8 executable path to HY8_PATH.txt."""
    destination: Path = hy8_path_file()
    destination.write_text(str(Path(path)), encoding="utf-8")
    return destination


def resolve_hy8_path() -> Path:
    """Resolve the HY-8 executable path from env vars, the file, or the default install."""
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