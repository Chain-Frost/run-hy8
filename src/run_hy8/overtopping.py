"""Result-time policy for intentional or unexpected roadway flow."""

from __future__ import annotations

import math
import warnings

from .results import Hy8Results
from .type_helpers import RoadwayOvertoppingPolicy

# Half of the SI .rst discharge reporting increment (0.01 m3/s).
ROADWAY_DISCHARGE_TOLERANCE: float = 0.005


class RoadwayOvertoppingWarning(UserWarning):
    """HY-8 returned roadway flow under the WARN policy."""


class RoadwayOvertoppingError(RuntimeError):
    """Unexpected roadway flow, retaining parsed results for inspection."""

    def __init__(self, message: str, crossing_name: str, results: Hy8Results) -> None:
        self.crossing_name: str = crossing_name
        self.results: Hy8Results = results
        super().__init__(message)


def check_roadway_overtopping(
    results: Hy8Results,
    crossing_name: str,
    policy: RoadwayOvertoppingPolicy = RoadwayOvertoppingPolicy.ERROR,
) -> None:
    """Apply policy to every parsed flow row, including inverse-search batches.

    Flags and water levels are not evidence of discharge. Missing or non-finite
    roadway discharge cannot establish safety and raises a parsing error.
    """
    policy = RoadwayOvertoppingPolicy(policy)
    if not results.rows or any(not math.isfinite(row.roadway_discharge) for row in results.rows):
        msg = f"HY-8 roadway discharge is missing or non-finite for crossing '{crossing_name}'."
        raise ValueError(msg)
    discharge = max(abs(row.roadway_discharge) for row in results.rows)
    if discharge <= ROADWAY_DISCHARGE_TOLERANCE or policy is RoadwayOvertoppingPolicy.ALLOW:
        return
    message = f"Crossing '{crossing_name}' has roadway discharge {discharge:.9g} m3/s (policy={policy.value})."
    if policy is RoadwayOvertoppingPolicy.ERROR:
        raise RoadwayOvertoppingError(message, crossing_name, results)
    warnings.warn(message, RoadwayOvertoppingWarning, stacklevel=2)
