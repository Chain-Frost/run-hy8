"""Tests for configuring HY-8 executable locations."""

from __future__ import annotations

import os
from pathlib import Path

import pytest

import run_hy8.hy8_path as hy8_path
from run_hy8.executor import Hy8Executable


def test_resolve_hy8_path_prefers_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("HY8_EXE", r"C:\custom\HY864.exe")
    monkeypatch.delenv("HY8_EXECUTABLE", raising=False)
    assert hy8_path.resolve_hy8_path() == Path(r"C:\custom\HY864.exe")


def test_resolve_hy8_path_reads_file(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    fake_file: Path = tmp_path / "HY8_PATH.txt"
    fake_file.write_text(r"C:\alt\HY864.exe", encoding="utf-8")
    monkeypatch.setattr(hy8_path, "hy8_path_file", lambda: fake_file)
    monkeypatch.delenv("HY8_EXE", raising=False)
    monkeypatch.delenv("HY8_EXECUTABLE", raising=False)

    assert hy8_path.resolve_hy8_path() == Path(r"C:\alt\HY864.exe")


def test_save_hy8_path_writes_file(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    fake_file: Path = tmp_path / "HY8_PATH.txt"
    monkeypatch.setattr(hy8_path, "hy8_path_file", lambda: fake_file)

    destination: Path = hy8_path.save_hy8_path(Path(r"C:\written\HY864.exe"))
    assert destination == fake_file
    assert fake_file.read_text(encoding="utf-8").strip() == r"C:\written\HY864.exe"
    assert hy8_path.read_hy8_path_file() == Path(r"C:\written\HY864.exe")


@pytest.mark.skipif(os.name != "nt", reason="HY-8 executable is only available on Windows.")
def test_hy8_executable_can_use_configured_path(tmp_path: Path) -> None:
    exe: Path = tmp_path / "HY864.exe"
    exe.write_text("", encoding="utf-8")
    prior: Path | None = Hy8Executable._default_path  # type: ignore[attr-defined]
    try:
        Hy8Executable.configure_default_path(exe)
        wrapper = Hy8Executable()
        assert wrapper.exe_path == exe
    finally:
        Hy8Executable._default_path = prior  # type: ignore[attr-defined]


@pytest.mark.skipif(os.name != "nt", reason="HY-8 executable is only available on Windows.")
def test_hy8_executable_persist_sets_file(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    fake_file: Path = tmp_path / "HY8_PATH.txt"
    exe: Path = tmp_path / "HY864.exe"
    exe.write_text("", encoding="utf-8")
    monkeypatch.setattr(hy8_path, "hy8_path_file", lambda: fake_file)
    prior: Path | None = Hy8Executable._default_path  # type: ignore[attr-defined]
    try:
        destination: Path = Hy8Executable.persist_default_path(exe)
        assert destination == fake_file
        assert fake_file.read_text(encoding="utf-8").strip() == str(exe)
        Hy8Executable._default_path = None  # type: ignore[attr-defined]
        assert Hy8Executable.default_path() == exe
    finally:
        Hy8Executable._default_path = prior  # type: ignore[attr-defined]


def test_resolve_falls_back_to_default(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("HY8_EXE", raising=False)
    monkeypatch.delenv("HY8_EXECUTABLE", raising=False)
    monkeypatch.setattr(hy8_path, "hy8_path_file", lambda: Path("nonexistent"))
    assert hy8_path.resolve_hy8_path() == hy8_path.DEFAULT_INSTALL_PATH
