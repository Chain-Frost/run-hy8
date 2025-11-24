"""
Domain models that describe HY-8 projects.

These data classes represent the various components of a HY-8 project,
such as crossings, culverts, and flow definitions, providing a structured,
in-memory representation that can be serialized to or from HY-8 files.
"""

from __future__ import annotations

from .base import Validatable
from .flow_definition import FlowDefinition
from .tailwater_definition import TailwaterDefinition
from .roadway_profile import RoadwayProfile
from .culvert_barrel import CulvertBarrel
from .culvert_crossing import CulvertCrossing
from .project import Hy8Project

__all__: list[str] = [
    "Validatable",
    "FlowDefinition",
    "TailwaterDefinition",
    "RoadwayProfile",
    "CulvertBarrel",
    "CulvertCrossing",
    "Hy8Project",
]
