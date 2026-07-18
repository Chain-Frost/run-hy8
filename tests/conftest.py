"""Pytest configuration for run-hy8 tests."""

from __future__ import annotations

import sys
import pytest
from pathlib import Path
from run_hy8.executor import Hy8Executable

PROJECT_ROOT: Path = Path(__file__).resolve().parents[1]
SRC_PATH: Path = PROJECT_ROOT / "src"

if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

def pytest_runtest_setup(item: pytest.Item) -> None:
    """Skip tests marked with requires_hy8 if the executable is not available."""
    if "requires_hy8" in item.keywords:
        # Check if we are on Windows
        if sys.platform != "win32":
            pytest.skip("HY-8 executable is only supported on Windows")
        
        # Check if the executable is configured/available
        try:
            Hy8Executable()
        except Exception:
            pytest.skip("HY-8 executable not found or not configured")
