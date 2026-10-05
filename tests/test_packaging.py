"""Regression tests for packaging failures and artifact preservation."""

from __future__ import annotations

import importlib.util
import os
import subprocess
import sys
import zipfile
from pathlib import Path

import pytest

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
# Standalone build helpers intentionally live outside the public package.
sys.path.insert(0, str(SCRIPTS))
spec = importlib.util.spec_from_file_location("packaging_builder", SCRIPTS / "build_library.py")
assert spec is not None
assert spec.loader is not None
builder = importlib.util.module_from_spec(spec)
spec.loader.exec_module(builder)
sys.path.remove(str(SCRIPTS))


@pytest.fixture
def project(tmp_path: Path) -> Path:
    (tmp_path / "src" / "run_hy8").mkdir(parents=True)
    (tmp_path / "pyproject.toml").write_bytes(b'[project]\r\nname = "run-hy8"\r\nversion = "2026.09.08.1"\r\n')
    for name in ("README.md", "LICENSE"):
        (tmp_path / name).write_text(name)
    (tmp_path / "dist").mkdir()
    (tmp_path / "dist" / "run_hy8-old.whl").write_bytes(b"previous wheel")
    (tmp_path / "dist" / "unrelated.whl").write_bytes(b"unrelated")
    return tmp_path


@pytest.mark.parametrize("failure", ["build", "missing", "multiple", "verification", "copy", "replace"])
def test_failure_preserves_artifact_and_metadata(project: Path, monkeypatch: pytest.MonkeyPatch, failure: str) -> None:
    original = (project / "pyproject.toml").read_bytes()

    def fake_build(source: Path, output: Path) -> None:
        # Even backend changes to metadata stay in the temporary staging copy.
        (source / "pyproject.toml").write_text("changed by backend")
        if failure == "build":
            raise subprocess.CalledProcessError(7, "build")
        output.mkdir()
        if failure != "missing":
            (output / builder.expected_filename(project)).write_bytes(b"candidate")
        if failure == "multiple":
            (output / "unexpected.whl").write_bytes(b"extra")

    def fake_verify(_wheel: Path, _root: Path) -> None:
        if failure == "verification":
            msg = "invalid wheel"
            raise ValueError(msg)

    monkeypatch.setattr(builder, "run_build", fake_build)
    monkeypatch.setattr(builder, "verify_wheel", fake_verify)
    if failure == "copy":
        original_copy = builder.shutil.copyfile

        def fail_copy(source: Path, destination: Path, **kwargs: object) -> Path:
            if Path(destination).suffix == ".incoming":
                msg = "copy failed"
                raise OSError(msg)
            return original_copy(source, destination, **kwargs)

        monkeypatch.setattr(builder.shutil, "copyfile", fail_copy)
    if failure == "replace":

        def fail_replace(_self: Path, _target: Path) -> None:
            msg = "replace failed"
            raise OSError(msg)

        monkeypatch.setattr(Path, "replace", fail_replace)
    with pytest.raises((ValueError, OSError, subprocess.CalledProcessError)):
        builder.build_and_promote(project)
    assert (project / "pyproject.toml").read_bytes() == original
    assert (project / "dist" / "run_hy8-old.whl").read_bytes() == b"previous wheel"
    assert (project / "dist" / "unrelated.whl").read_bytes() == b"unrelated"
    assert not list((project / "dist").glob("*.incoming"))


def test_promotion_preserves_unrelated_artifacts(project: Path, tmp_path: Path) -> None:
    candidate = tmp_path / "run_hy8-new.whl"
    candidate.write_bytes(b"new wheel")
    destination = builder.promote_wheel(candidate, project)
    assert destination.read_bytes() == b"new wheel"
    assert list((project / "dist").glob("run_hy8-*.whl")) == [destination]
    assert (project / "dist" / "unrelated.whl").read_bytes() == b"unrelated"


@pytest.mark.skipif(sys.platform != "win32", reason="Windows batch wrapper")
def test_wrapper_never_installs_after_failure(tmp_path: Path) -> None:
    wrapper = SCRIPTS.parent / "package_and_install.bat"
    (tmp_path / wrapper.name).write_bytes(wrapper.read_bytes())
    (tmp_path / "build_package.bat").write_text("@exit /b 7\n")
    (tmp_path / "force_reinstall_package.bat").write_text("@echo installed>installed.txt\n")
    result = subprocess.run(  # noqa: S603 - execute controlled batch fixtures
        [os.environ["COMSPEC"], "/c", str(tmp_path / wrapper.name)],
        cwd=tmp_path,
        check=False,
    )
    assert result.returncode == 7
    assert not (tmp_path / "installed.txt").exists()


@pytest.mark.parametrize("defect", ["version", "license", "typed", "source", "development", "filename"])
def test_verifier_rejects_invalid_contents(tmp_path: Path, defect: str) -> None:
    root = tmp_path / "project"
    package = root / "src" / "run_hy8"
    package.mkdir(parents=True)
    (package / "__init__.py").write_bytes(b"# package\n")
    (package / "py.typed").write_bytes(b"")
    (root / "LICENSE").write_bytes(b"licence\n")
    (root / "pyproject.toml").write_text(
        '[project]\nname="run-hy8"\nversion="2026.09.08.1"\nlicense="SUL-1.0"\nrequires-python=">=3.14"\n'
    )
    info = "run_hy8-2026.9.8.1.dist-info"
    members = {
        "run_hy8/__init__.py": b"# package\n",
        "run_hy8/py.typed": b"",
        f"{info}/licenses/LICENSE": b"licence\n",
        f"{info}/METADATA": (
            b"Name: run-hy8\nVersion: 2026.9.8.1\nLicense-Expression: SUL-1.0\n"
            b"License-File: LICENSE\nRequires-Python: >=3.14\n\n"
        ),
    }
    if defect == "version":
        members[f"{info}/METADATA"] = members[f"{info}/METADATA"].replace(b"2026.9.8.1", b"2025.1.1.1")
    elif defect == "license":
        members[f"{info}/licenses/LICENSE"] = b"wrong licence"
    elif defect == "typed":
        del members["run_hy8/py.typed"]
    elif defect == "source":
        members["run_hy8/__init__.py"] = b"stale source"
    elif defect == "development":
        members["tests/test_dev.py"] = b"development"
    wheel = tmp_path / ("wrong.whl" if defect == "filename" else builder.expected_filename(root))
    with zipfile.ZipFile(wheel, "w") as archive:
        for name, content in members.items():
            archive.writestr(name, content)
    with pytest.raises(ValueError, match=r"filename|metadata|LICENSE|typed|source|development"):
        builder.verify_wheel(wheel, root)
