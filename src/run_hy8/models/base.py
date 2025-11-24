"""Shared base helpers for HY-8 model dataclasses."""

from __future__ import annotations
from abc import abstractmethod
from typing import Any, Mapping, Sequence, TYPE_CHECKING, cast
from _collections_abc import Mapping as ABCMapping, Sequence as ABCSequence
from loguru import logger
from ..classes_references import ValidationError
from ..type_helpers import TailwaterRatingPoint

if TYPE_CHECKING:
    from .culvert_crossing import CulvertCrossing


class Validatable:
    """
    A mixin class that provides a validation interface for domain models.

    Classes that inherit from `Validatable` must implement the `validate` method.
    This mixin supplies the `assert_valid` helper, which invokes `validate` and
    raises a `ValidationError` if any errors are found.
    """

    def assert_valid(self, prefix: str = "") -> None:
        """
        Raise a `ValidationError` if the model is invalid.

        Args:
            prefix: An optional string to prepend to each validation error message.
        """
        errors: str = str(self.validate(prefix=prefix))
        if errors:
            logger.debug("Validation failed for {model}: {errors}", model=self.__class__.__name__, errors=errors)
            raise ValidationError(errors)
        logger.debug("Validation succeeded for {model}.", model=self.__class__.__name__)

    @abstractmethod
    def validate(self, prefix: str) -> list[str]:
        """
        Return a list of validation errors, or an empty list if the model is valid.

        This method must be implemented by any class that inherits from `Validatable`.

        Args:
            prefix: A string to prepend to each validation error message for context.
        """
        pass


def float_list() -> list[float]:
    """
    Return a new `list[float]`.

    This helper function is used as a `default_factory` in dataclasses to avoid
    the use of mutable default arguments.
    """

    return []


def string_list() -> list[str]:
    """
    Return a new `list[str]`.

    This helper function is used as a `default_factory` in dataclasses to avoid
    the use of mutable default arguments.
    """

    return []


def rating_curve_list() -> list[TailwaterRatingPoint]:
    """
    Return an empty list of `TailwaterRatingPoint` objects.

    This helper function is used as a `default_factory` in dataclasses to avoid
    the use of mutable default arguments.
    """

    return []


def crossing_list() -> list["CulvertCrossing"]:
    """
    Return a new list of `CulvertCrossing` objects.

    This helper function is used as a `default_factory` in dataclasses to avoid
    the use of mutable default arguments.
    """

    return []


def normalize_sequence(value: Any) -> list[Any]:
    """Return a list or fall back to an empty list for non-sequence values."""

    if isinstance(value, ABCSequence) and not isinstance(value, (str, bytes)):
        return list(cast(Sequence[Any], value))
    return []


def normalize_mapping(value: Any) -> Mapping[str, Any]:
    """Return a mapping or an empty dict if the value is not mapping-like."""

    if isinstance(value, ABCMapping):
        return cast(Mapping[str, Any], value)
    return {}
