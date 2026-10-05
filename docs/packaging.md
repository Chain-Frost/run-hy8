# Verified package builds

Run `build_package.bat` or `python scripts/build_library.py`. Use `--skip-pip`
when the build frontend is already installed. The declared project version is
preserved; wheel filenames use its normalized Python packaging form.

Each build gets its own temporary source copy, so setuptools does not alter
repository metadata or reuse stale build files. Set `RUN_HY8_STAGE_ROOT` to
choose a local staging parent for network checkouts. The parent is preserved;
only the invocation's temporary directory is cleaned up.

Before promotion, the candidate must match the project name, version, Python
requirement and licence, include the exact Python sources and `py.typed`, and
exclude development files. This package currently has no runtime data files.
New runtime data must be declared in setuptools and added to the verifier's
required contents together.

The verified wheel is copied onto the destination filesystem and replaced
atomically. Older `run_hy8-*.whl` files are removed after replacement, while
unrelated artifacts remain. Failed builds or verification leave existing wheels
and repository metadata untouched. `package_and_install.bat` stops immediately
on a failed build and propagates installer failures.

Validate the retained artifact with:

```powershell
python scripts/verify_wheel.py
python scripts/smoke_test_installed_wheel.py
```

The smoke test installs the wheel and its dependencies into a temporary target, then checks
all exported symbols, version and typed marker from outside the checkout using
isolated Python. It does not replace your installed package or modify your user Python dependencies.
