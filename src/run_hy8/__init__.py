"""Public API for run-hy8, a package to interact with the HY-8 hydraulics program."""

from .classes_references import UnitSystem
from .config import load_project_from_json, project_from_mapping
from .executor import Hy8Executable
from .hy8_path import read_hy8_path_file, resolve_hy8_path, save_hy8_path
from .hydraulics import HydraulicsResult
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
    "CircularConcreteInlet",
    "CircularCorrugatedSteelInlet",
    "CircularHdpeInlet",
    "ConcreteBoxInlet",
    "CulvertBarrel",
    "CulvertCrossing",
    "CulvertMaterial",
    "CulvertShape",
    "FlowDefinition",
    "FlowMethod",
    "Hy8Executable",
    "Hy8FileWriter",
    "Hy8Project",
    "Hy8Results",
    "HydraulicsResult",
    "ImprovedInletEdgeType",
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
    "culvert_dataframe",
    "load_project_from_hy8",
    "load_project_from_json",
    "parse_rsql",
    "parse_rst",
    "project_from_mapping",
    "read_hy8_path_file",
    "resolve_hy8_path",
    "save_hy8_path",
]
