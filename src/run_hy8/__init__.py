"""Public API for run-hy8, a package to interact with the HY-8 hydraulics program."""

from .classes_references import UnitSystem
from .config import load_project_from_json, project_from_mapping
from .executor import Hy8Executable
from .hydraulics import HydraulicsResult
from .hy8_path import read_hy8_path_file, resolve_hy8_path, save_hy8_path
from .inlet_configurations import (
    CircularConcreteInlet,
    CircularCorrugatedSteelInlet,
    CircularHdpeInlet,
    ConcreteBoxInlet,
    SupportedInletConfiguration,
)
from .models import (
    CulvertBarrel,
    CulvertCrossing,
    FlowDefinition,
    Hy8Project,
    LegacyInletConfigurationWarning,
    RoadwayProfile,
    TailwaterDefinition,
)
from .reader import culvert_dataframe, load_project_from_hy8
from .results import Hy8Results, parse_rsql, parse_rst
from .type_helpers import (
    CulvertMaterial,
    CulvertShape,
    FlowMethod,
    ImprovedInletEdgeType,
    InletEdgeType,
    InletEdgeType71,
    InletType,
    RoadwaySurface,
    TailwaterType,
)
from .writer import Hy8FileWriter

__all__: list[str] = [
    "HydraulicsResult",
    "CulvertBarrel",
    "CulvertCrossing",
    "CulvertMaterial",
    "CulvertShape",
    "CircularConcreteInlet",
    "CircularCorrugatedSteelInlet",
    "CircularHdpeInlet",
    "ConcreteBoxInlet",
    "FlowDefinition",
    "FlowMethod",
    "ImprovedInletEdgeType",
    "Hy8Executable",
    "Hy8FileWriter",
    "Hy8Project",
    "InletEdgeType",
    "InletEdgeType71",
    "InletType",
    "LegacyInletConfigurationWarning",
    "RoadwayProfile",
    "RoadwaySurface",
    "SupportedInletConfiguration",
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
