"""HY-8 Runner class that will create an HY-8 file and run HY-8."""

from __future__ import annotations

__copyright__ = "(C) Copyright Aquaveo 2024"
__license__ = "All rights reserved"
# This is not a FHWA product nor is it endorsed by FHWA.
# FHWA will not be providing any technical supporting, funding or maintenance.


class Hy8RunnerFlow:
    """A class that will create an HY-8 file and run HY-8."""

    def __init__(self) -> None:
        """Initializes the HY-8 Runner class."""
        self.method: str = "min-design-max"  # 'min-design-max', 'user-defined', or 'min-max-increment'
        self.flow_min: float = 0.0
        self.flow_design: float = 0.0
        self.flow_max: float = 0.0
        self.flow_increment: float = 0.0
        self.flow_list: list[float] = []

    def compute_list(self) -> None:
        """Compute the list of flows."""
        if self.method == "min-design-max":
            self.flow_list = [self.flow_min, self.flow_design, self.flow_max]
        elif self.method == "min-max-increment":
            self.flow_list = []
            flow = self.flow_min
            while flow <= self.flow_max:
                self.flow_list.append(flow)
                flow += self.flow_increment

    def validate_crossings_data(self, crossing_str: str) -> tuple[bool, str]:
        """Validate the data.

        Returns:
            bool: True if the data is valid.
            string: The error message if the data is not valid.
        """
        messages = ""
        result = True

        if self.method == "min-design-max":
            if self.flow_min >= self.flow_design:
                messages += f"{crossing_str}Minimum flow must be less than or equal to design flow.\n"
                result = False
            if self.flow_design >= self.flow_max:
                messages += f"{crossing_str}Design flow must be less than or equal to maximum flow.\n"
                result = False
            if self.flow_min < 0.0:
                messages += f"{crossing_str}Minimum flow must be zero or greater.\n"
                result = False
        elif self.method == "min-max-increment":
            if self.flow_min >= self.flow_max:
                messages += f"{crossing_str}Minimum flow must be less than maximum flow.\n"
                result = False
            if self.flow_min < 0.0:
                messages += f"{crossing_str}Minimum flow must be zero or greater.\n"
                result = False
            if self.flow_increment <= 0.0:
                messages += f"{crossing_str}Flow increment must be greater than zero.\n"
                result = False
        elif self.method == "user-defined":
            if len(self.flow_list) < 2:
                messages += f"{crossing_str}User-defined flow list must have at least two values.\n"
                result = False
            elif len(self.flow_list) >= 2:
                for i in range(len(self.flow_list) - 1):
                    if self.flow_list[i] >= self.flow_list[i + 1]:
                        messages += f"{crossing_str}Flow list values must increase in value.\n"
                        result = False
                        break
        else:
            messages += f"{crossing_str}Flow method must be min-design-max, user-defined, or min-max-increment.\n"
            result = False

        return result, messages
