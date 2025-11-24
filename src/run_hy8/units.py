"""Unit conversion helpers shared across the run-hy8 domain."""

FT_TO_METRES = 0.3048
METRES_TO_FEET: float = 1 / FT_TO_METRES
FT_TO_MM = 304.8
MM_TO_FT: float = 1 / FT_TO_MM
IN_TO_MM = 25.4
MM_TO_IN: float = 1 / IN_TO_MM
CFS_TO_CMS = 0.028316846592
CMS_TO_CFS: float = 1 / CFS_TO_CMS
FTS_TO_MS = 0.3048
MS_TO_FTS: float = 1 / FTS_TO_MS


def feet_to_metres(value: float) -> float:
    """Convert feet into metres."""
    return value * FT_TO_METRES


def metres_to_feet(value: float) -> float:
    """Convert metres into feet."""
    return value * METRES_TO_FEET


def feet_to_millimetres(value: float) -> float:
    """Convert feet into millimetres."""
    return value * FT_TO_MM


def millimetres_to_feet(value: float) -> float:
    """Convert millimetres into feet."""
    return value * MM_TO_FT


def inches_to_millimetres(value: float) -> float:
    """Convert inches into millimetres."""
    return value * IN_TO_MM


def millimetres_to_inches(value: float) -> float:
    """Convert millimetres into inches."""
    return value * MM_TO_IN


def cfs_to_cms(value: float) -> float:
    """Convert cubic feet per second into cubic metres per second."""
    return value * CFS_TO_CMS


def cms_to_cfs(value: float) -> float:
    """Convert cubic metres per second into cubic feet per second."""
    return value * CMS_TO_CFS


def feet_per_second_to_metres_per_second(value: float) -> float:
    """Convert feet per second into metres per second."""
    return value * FTS_TO_MS


def metres_per_second_to_feet_per_second(value: float) -> float:
    """Convert metres per second into feet per second."""
    return value * MS_TO_FTS