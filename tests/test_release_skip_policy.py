"""Tests for immutable commit markers and explicit PR release labels."""

import importlib.util
from pathlib import Path

import pytest

_ROOT = Path(__file__).absolute().parents[1]
_SCRIPT = _ROOT / "scripts" / "release_skip_policy.py"
_SPEC = importlib.util.spec_from_file_location("release_skip_policy", _SCRIPT)
assert _SPEC is not None
assert _SPEC.loader is not None
_policy = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_policy)


@pytest.mark.parametrize(
    ("labels", "message", "expected"),
    [
        ([], "feat: new hydraulic model (#17)", False),
        (["docs"], "docs: update files", False),
        (["skip-release"], "docs: update files", True),
        (["SKIP-RELEASE"], "docs: update files", True),
        (["skip_release"], "docs: update files", False),
        ([], "docs: change [skip release] (#18)", True),
        ([], "docs: change [SKIP RELEASE]", True),
        ([], "docs: change skip release", False),
        (["maintenance", "skip-release"], "fix: unrelated", True),
    ],
)
def test_release_opt_out(labels: list[str], message: str, *, expected: bool) -> None:
    assert _policy.should_skip_release(labels, message) is expected


def test_all_release_workflows_are_merge_only() -> None:
    automatic = (_ROOT / ".github/workflows/auto-publish.yml").read_text(encoding="utf-8")
    publisher = (_ROOT / ".github/workflows/pypi-publish.yml").read_text(encoding="utf-8")
    assets = (_ROOT / ".github/workflows/sync-release-assets.yml").read_text(encoding="utf-8")
    for source in (automatic, publisher, assets):
        assert "\n  workflow_run:" in source
        assert "\n  schedule:" not in source
        assert "\n  workflow_dispatch:" not in source
        assert "\n  release:\n    types:" not in source
        assert "createWorkflowDispatch" not in source
    assert "workflows: [Python CI]" in automatic
    assert "workflows: [Release new verified main merges]" in publisher
    assert "workflows: [Publish to PyPI]" in assets
    assert "scripts/release_skip_policy.py" in automatic
    assert automatic.index("scripts/release_skip_policy.py") < automatic.index("const tags =")
    assert "pypa/gh-action-pypi-publish@release/v1" in publisher
