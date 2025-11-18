"""Public API for run-hy8."""

from .config import load_project_from_json, project_from_mapping
from .executor import Hy8Executable
from .hy8_path import read_hy8_path_file, resolve_hy8_path, save_hy8_path
from .hydraulics import HydraulicsResult
from .models import (
    CulvertBarrel,
    CulvertCrossing,
    CulvertMaterial,
    CulvertShape,
    FlowDefinition,
    FlowMethod,
    ImprovedInletEdgeType,
    Hy8Project,
    InletEdgeType,
    InletEdgeType71,
    InletType,
    RoadwayProfile,
    RoadwaySurface,
    TailwaterDefinition,
    TailwaterType,
    UnitSystem,
)
from .reader import culvert_dataframe, load_project_from_hy8
from .results import Hy8Results, parse_rsql, parse_rst
from .writer import Hy8FileWriter

__all__: list[str] = [
    "HydraulicsResult",
    "CulvertBarrel",
    "CulvertCrossing",
    "CulvertMaterial",
    "CulvertShape",
    "FlowDefinition",
    "FlowMethod",
    "ImprovedInletEdgeType",
    "Hy8Executable",
    "Hy8FileWriter",
    "Hy8Project",
    "InletEdgeType",
    "InletEdgeType71",
    "InletType",
    "RoadwayProfile",
    "RoadwaySurface",
    "TailwaterDefinition",
    "TailwaterType",
    "UnitSystem",
    "Hy8Results",
    "parse_rst",
    "parse_rsql",
    "culvert_dataframe",
    "load_project_from_json",
    "load_project_from_hy8",
    "project_from_mapping",
    "read_hy8_path_file",
    "resolve_hy8_path",
    "save_hy8_path",
]
