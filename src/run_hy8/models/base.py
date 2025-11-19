"""Shared base helpers for HY-8 model dataclasses."""

from __future__ import annotations

from abc import abstractmethod
from typing import Any, Mapping, Sequence, cast
from _collections_abc import Mapping as ABCMapping, Sequence as ABCSequence

from loguru import logger

from src.run_hy8.classes_references import ValidationError

from ..type_helpers import TailwaterRatingPoint


class Validatable:
    """Mixin that supplies an assert_valid helper for domain models."""

    def assert_valid(self, prefix: str = "") -> None:
        errors: str = str(self.validate(prefix=prefix))
        if errors:
            logger.debug("Validation failed for {model}: {errors}", model=self.__class__.__name__, errors=errors)
            raise ValidationError(errors)
        logger.debug("Validation succeeded for {model}.", model=self.__class__.__name__)

    @abstractmethod
    def validate(self, prefix: str) -> list[str]:
        pass


def _float_list() -> list[float]:
    """Return a new list[float]; helper avoids mutable default arguments."""

    return []


def _string_list() -> list[str]:
    """Return a new list[str] for dataclass default_factory."""

    return []


def _rating_curve_list() -> list[TailwaterRatingPoint]:
    """Return an empty rating-curve list for dataclass defaults."""

    return []


def _crossing_list() -> list["CulvertCrossing"]:
    """Return a fresh list of CulvertCrossing objects for defaults."""

    return []


def _normalize_sequence(value: Any) -> Sequence[Any]:
    """Return sequences or fall back to an empty tuple for non-iterables."""

    if isinstance(value, ABCSequence) and not isinstance(value, (str, bytes)):
        return value
    return ()


def _normalize_mapping(value: Any) -> Mapping[str, Any]:
    """Return a mapping or an empty dict when the value is not mapping-like."""

    if isinstance(value, ABCMapping):
        return cast(Mapping[str, Any], value)
    return {}
