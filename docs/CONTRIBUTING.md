# Development and Contribution Guidelines

This project targets Windows and Python 3.13/3.14. The coding conventions in
[`agents.md`](agents.md) apply to human and automated contributors.

## Development setup

Use the selected user-level Python 3.14 installation directly. Install the
package and development tools from the repository root:

```powershell
python -m pip install --user -e ".[dev]"
```

## Required checks

Run these checks before committing:

```powershell
ruff format .
ruff check . --fix
pyright src/run_hy8
python -m pytest
```

GitHub Actions runs the non-HY-8 checks for pushes to `main` and for pull
requests. Tests marked `requires_hy8` are skipped when the HY-8 executable is
not installed.

## Git workflow

The repository uses two contribution paths:

- The maintainer and authorized local Codex sessions may commit directly to
  `main` after the required checks pass.
- External contributors must work on a branch or fork and open a pull request.
  Their changes are merged only after review and successful CI checks.

External contributors can start a branch with:

```powershell
git switch -c descriptive-change-name
```

Keep commits focused and use messages that describe the outcome of the change.
Do not force-push or delete `main`.

## Line endings

The checked-in `.gitattributes` file stores text as LF while keeping Windows
batch files as CRLF. Let Git perform this conversion; do not commit bulk
line-ending-only changes.

## Build artifacts

Do not commit wheels to `dist/`. For release-eligible merged PRs, the
automation builds and verifies the wheel, publishes it to PyPI and
attaches the identical distribution to the GitHub Release.

## Skipping a package release

Normal merged PRs create a PyPI release after post-merge CI succeeds.
For documentation-only or maintenance PRs, apply the exact label
`skip-release` **before merging**, or include `[skip release]` in the
**final squash-merge commit message**. A PR description or an individual
pre-squash commit is not sufficient for the commit-message alternative.

Release opt-outs do not skip CI, the strict MkDocs build or documentation
deployment. The release automation has no scheduled or manually dispatched
publication trigger; only a successful, eligible PR merge can publish.
