# Development and Contribution Guidelines

This document outlines the development process and coding standards for the `run-hy8` project. It is intended for the primary author and authorized AI agents who perform modifications to the codebase.

The goal is to maintain a high level of code quality, consistency, and automation. All contributions, whether from a human or an agent, must adhere to these guidelines.

## Core Principles

The foundational conventions for all code changes are defined in `docs/agents.md`. This file is the source of truth for coding standards. Key principles include:

*   **Strict Type Hinting**: All code must be `pyright`-clean in strict mode. No exceptions.
*   **Automated Tooling**: Code is formatted with `ruff format` and linted with `ruff check`. All changes must pass these checks.
*   **Testing**: New features require corresponding tests. Bug fixes should include a regression test to prevent recurrence.
*   **Clarity and Simplicity**: Code should be clear, well-commented, and easy for both human and AI agents to understand and modify.

## Development Environment Setup

To get your development environment set up, please follow these steps:

1.  Ensure you are in the root directory of the repository.
2.  Create and activate a virtual environment. This is the recommended approach to ensure dependency isolation. This project requires Python 3.13+.

    For **PowerShell**:
    ```powershell
    python -m venv .venv
    .venv\Scripts\Activate.ps1
    ```
    For **Command Prompt** (`cmd.exe`):
    ```cmd
    python -m venv .venv
    .venv\Scripts\activate.bat
    ```
3.  Install the project in editable mode with all development dependencies:
    ```powershell
    pip install -e .[dev]
    ```

## Development Workflow

All changes, whether for new features, bug fixes, or refactoring, should follow this process:

1.  Create a new feature branch from `main`:
    ```powershell
    git checkout -b name-of-your-change
    ```
2.  Make the necessary code modifications.
3.  Apply formatting and linting:
    ```powershell
    ruff format .
    ruff check . --fix
    ```
4.  Verify correctness with the type checker and test suite:
    ```powershell
    pyright src/run_hy8
    python -m pytest
    ```
5.  Commit the changes with a clear and descriptive commit message.
6.  Once work is complete and verified, merge the changes back into the `main` branch.
    ```powershell
    git checkout main
    git merge name-of-your-change
    git branch -d name-of-your-change
    ```