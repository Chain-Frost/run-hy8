"""Flow definition and helpers for HY-8 crossings."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, ClassVar
from _collections_abc import Mapping

from loguru import logger

from .base import Validatable, float_list, string_list, normalize_sequence
from ..type_helpers import FlowMethod, coerce_enum


@dataclass(slots=True)
class FlowDefinition(Validatable):
    """Flow information for a crossing.

    FlowMethod.MIN_DESIGN_MAX problems must provide exactly three flows via
    `minimum`/`design`/`maximum` or `user_values`.
    FlowMethod.USER_DEFINED problems require at least one `user_values` and
    may include matching `user_value_labels`.
    """

    DUMMY_FLOW_LABEL: ClassVar[str] = "dummy flow"
    method: FlowMethod = FlowMethod.USER_DEFINED
    minimum: float = 0.0
    design: float = 0.0
    maximum: float = 0.0
    user_values: list[float] = field(default_factory=float_list)
    user_value_labels: list[str] = field(default_factory=string_list)

    def describe(self) -> str:
        try:
            values: list[float] = self.sequence()
        except ValueError:
            values = []
        preview: str = ", ".join(f"{value:.3f}" for value in values[:3])
        if len(values) > 3:
            preview += ", ..."
        return f"FlowDefinition(method={self.method.name}, count={len(values)}, values=[{preview}])"

    def __str__(self) -> str:
        return self.describe()

    def __repr__(self) -> str:
        return self.describe()

    def sequence(self) -> list[float]:
        """Return the flows HY-8 expects to see in the DISCHARGEXYUSER cards."""
        if self.method is FlowMethod.MIN_DESIGN_MAX:
            return self._min_design_max_values()
        if self.method is FlowMethod.USER_DEFINED:
            return list(self.user_values)
        raise ValueError(f"Flow method '{self.method}' is not supported.")

    def add_user_flow(self, value: float, label: str | None = None) -> "FlowDefinition":
        """Append a user-defined flow (and optional label) while maintaining invariants."""

        self.method = FlowMethod.USER_DEFINED
        self.user_values.append(value)
        if label is not None:
            while len(self.user_value_labels) < len(self.user_values) - 1:
                self.user_value_labels.append("")
            self.user_value_labels.append(label)
        elif self.user_value_labels:
            self.user_value_labels.append("")
        logger.debug(
            "Added user flow {flow:.4f} ({count} total) to {definition}",
            flow=value,
            count=len(self.user_values),
            definition=self.describe(),
        )
        return self

    def set_min_design_max(self, minimum: float, design: float, maximum: float) -> "FlowDefinition":
        """Flip this definition into the min/design/max mode."""

        self.method = FlowMethod.MIN_DESIGN_MAX
        self.minimum = minimum
        self.design = design
        self.maximum = maximum
        self.user_values.clear()
        self.user_value_labels.clear()
        logger.debug(
            "Configured min/design/max flows ({minimum:.4f}/{design:.4f}/{maximum:.4f}) for {definition}",
            minimum=minimum,
            design=design,
            maximum=maximum,
            definition=self.describe(),
        )
        return self

    def _min_design_max_values(self) -> list[float]:
        values: list[float] = []
        values.append(self.minimum)
        values.append(self.design)
        values.append(self.maximum)
        if len(values) != 3:
            raise ValueError("Min/Design/Max problems must provide exactly three flows.")
        return values

    def to_dict(self) -> dict[str, Any]:
        return {
            "method": self.method.name,
            "minimum": self.minimum,
            "design": self.design,
            "maximum": self.maximum,
            "user_values": list(self.user_values),
            "user_value_labels": list(self.user_value_labels),
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "FlowDefinition":
        method_value = data.get("method", FlowMethod.USER_DEFINED.name)
        method: FlowMethod = coerce_enum(FlowMethod, method_value, default=FlowMethod.USER_DEFINED)
        user_values_raw = normalize_sequence(data.get("user_values"))
        user_value_labels_raw = normalize_sequence(data.get("user_value_labels"))

        return cls(
            method=method,
            minimum=float(data.get("minimum", 0.0)),
            design=float(data.get("design", 0.0)),
            maximum=float(data.get("maximum", 0.0)),
            user_values=[float(value) for value in user_values_raw],
            user_value_labels=[str(value) for value in user_value_labels_raw],
        )

    def validate(self, prefix: str = "") -> list[str]:
        errors: list[str] = []
        if self.method is FlowMethod.MIN_DESIGN_MAX:
            if self.user_values and len(self.user_values) != 3:
                errors.append(f"{prefix}Provide exactly three flows for Min/Design/Max problems.")
            values: list[float] = self._min_design_max_values()
            if len(values) != 3:
                return errors
            if not values[0] < values[1] < values[2]:
                errors.append(f"{prefix}Min/Design/Max must be strictly increasing.")
            if values[0] < 0:
                errors.append(f"{prefix}Minimum flow must be >= 0.")
        elif self.method is FlowMethod.USER_DEFINED:
            if not self.user_values:
                errors.append(f"{prefix}Provide at least one user-defined flow value.")
            elif len(self.user_values) > 1 and any(a >= b for a, b in zip(self.user_values, self.user_values[1:])):
                errors.append(f"{prefix}User-defined flows must be strictly increasing.")
            if self.user_value_labels and len(self.user_value_labels) != len(self.user_values):
                errors.append(f"{prefix}Provide the same number of flow labels as flow values.")
        else:
            errors.append(f"{prefix}Flow method '{self.method}' is not supported.")
        return errors
