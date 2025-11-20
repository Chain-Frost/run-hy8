"""Core data classes and references for run-hy8."""
from _collections_abc import Sequence
from enum import Enum


class UnitSystem(Enum):
    """Supported unit systems."""

    ENGLISH = ("EN", 0)
    SI = ("SI", 1)

    def __init__(self, cli_flag: str, project_flag: int) -> None:
        self.cli_flag: str = cli_flag
        self.project_flag: int = project_flag


class ValidationError(ValueError):
    """Exception raised when a model fails validation."""

    def __init__(self, errors: Sequence[str]) -> None:
        self.errors: list[str] = list(errors)
        message: str = "; ".join(self.errors) if self.errors else "Unknown validation error."
        super().__init__(message)