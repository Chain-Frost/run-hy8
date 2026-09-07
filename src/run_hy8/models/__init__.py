"""
Domain models that describe HY-8 projects.

These data classes represent the various components of a HY-8 project,
such as crossings, culverts, and flow definitions, providing a structured,
in-memory representation that can be serialized to or from HY-8 files.
"""

from __future__ import annotations

from ..type_helpers import FlowMethod
from .base import Validatable
from .culvert_barrel import CulvertBarrel, LegacyInletConfigurationWarning
from .culvert_crossing import CulvertCrossing
from .flow_definition import FlowDefinition
from .project import Hy8Project
from .roadway_profile import RoadwayProfile
from .tailwater_definition import TailwaterDefinition

__all__: list[str] = [
    "CulvertBarrel",
    "CulvertCrossing",
    "FlowDefinition",
    "FlowMethod",
    "Hy8Project",
    "LegacyInletConfigurationWarning",
    "RoadwayProfile",
    "TailwaterDefinition",
    "Validatable",
]
