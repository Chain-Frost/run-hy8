## Agent & Contributor Notes

These utilities are edited frequently by automated agents in the Codex CLI. Keep these conventions in mind so strict
type checking and future automation continue to work smoothly.

- **Type hints everywhere.** `pyright` runs in `strict` mode. Prefer explicit local annotations, and introduce helper
  `TypedDict`s or `Literal` keys when parsing loosely typed inputs. Run `pyright src/run_hy8` before sending changes.
- **Use `typing.cast` after validation checks.** When a `dict`/`list` comes from JSON or another untyped source, first
  guard it with `isinstance` and then apply `cast` so static analysis understands the type. Avoid `assert` for this flow
  because assertions are removed with `python -O` and won't convince `pyright`.
- **Prefer `rg` for searches and `apply_patch` for one-file edits.** The CLI is configured so `rg` is fast and always
  available. `apply_patch` keeps diffs small and reviewable; only switch to other tools for multi-file refactors or
  generated changes.
- **Honor existing git changes.** The repo may already have modifications; do not revert files you didn't touch.
- **Keep edits ASCII by default** and be liberal with helpful comments so human readers can quickly grasp intent,
  algorithm choices, and any gotchas.
- **Default HY-8 executable path.** Unless the user specifies otherwise, assume HY-8 lives at
  `C:\Program Files\HY-8 8.00\HY864.exe` and pass that path to `Hy8Executable`/`--run-exe`.
- **Windows command tips.** All shell commands run via `powershell.exe` with the working directory set explicitly (for
  example, `E:\Github\run-hy8`). PowerShell does not support heredoc syntax like `python - <<'PY'`; use `python -c` or
  `Get-Content` instead, and escape Windows paths (e.g., `Path(r"C:\Program Files\...")` or double backslashes).

Following these guidelines keeps the codebase predictable for both humans and future agents.
