# Development and Contribution Guidelines

This project targets Windows and Python 3.14. The coding conventions in
[`agents.md`](agents.md) apply to human and automated contributors.

## Development setup

Create and activate a Python 3.14 virtual environment from the repository root.

For PowerShell:

```powershell
py -3.14 -m venv .venv
.venv\Scripts\Activate.ps1
```

For Command Prompt:

```cmd
py -3.14 -m venv .venv
.venv\Scripts\activate.bat
```

Install the package and development tools:

```powershell
python -m pip install -e .[dev]
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

The current wheel in `dist/` is intentionally committed so a known working
build can be shared directly from the repository. Keep only the current build,
replace it when the project version changes, and commit it with the source and
version update that produced it. These small wheels belong in ordinary Git and
must not be moved to Git LFS.
