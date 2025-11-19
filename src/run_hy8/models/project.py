"""HY-8 project container that holds multiple crossings."""

from __future__ import annotations

from collections import OrderedDict
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Mapping, Sequence, TYPE_CHECKING, cast
from _collections_abc import Mapping as ABCMapping

from loguru import logger

from .base import Validatable, crossing_list, normalize_sequence
from ..classes_references import UnitSystem
from ..type_helpers import coerce_enum
from .culvert_crossing import CulvertCrossing

if TYPE_CHECKING:
    from ..hydraulics import HydraulicsResult

if TYPE_CHECKING:
    from ..executor import Hy8Executable


@dataclass(slots=True)
class Hy8Project(Validatable):
    """A full HY-8 project containing one or more crossings."""

    title: str = ""
    designer: str = ""
    notes: str = ""
    units: UnitSystem = UnitSystem.SI
    exit_loss_option: int = 0
    crossings: list[CulvertCrossing] = field(default_factory=crossing_list)

    @staticmethod
    def project_timestamp_hours() -> float:
        """HY-8 expects the project date as hours since epoch."""

        return datetime.now().timestamp() / 3600.0

    def describe(self) -> str:
        return f"Hy8Project(title={self.title or '<untitled>'}, crossings={len(self.crossings)})"

    def __str__(self) -> str:
        return self.describe()

    def __repr__(self) -> str:
        return self.describe()

    def validate(self, prefix: str = "") -> list[str]:
        errors: list[str] = []
        if not self.crossings:
            errors.append(f"{prefix}At least one crossing is required.")
        for index, crossing in enumerate(self.crossings, start=1):
            crossing_prefix: str = f"{prefix}Crossing #{index} ({crossing.name}): "
            errors.extend(crossing.validate(crossing_prefix))
        return errors

    def add_crossing(self, crossing: CulvertCrossing | None = None) -> CulvertCrossing:
        if crossing is None:
            crossing = CulvertCrossing(name=f"Crossing {len(self.crossings) + 1}")
        self.crossings.append(crossing)
        logger.debug(
            "Added crossing {crossing} to project {project}",
            crossing=crossing.name,
            project=self.title or "<untitled>",
        )
        return crossing

    def flow_values(self) -> Sequence[list[float]]:
        return [crossing.flow.sequence() for crossing in self.crossings]

    def hw_from_q(
        self,
        q: float,
        *,
        hy8: "Hy8Executable | Path | None" = None,
        workspace: Path | None = None,
        keep_files: bool = False,
    ) -> "OrderedDict[str, HydraulicsResult]":
        """Return per-crossing headwater elevations by running HY-8 for the specified discharge."""
        from ..hydraulics import project_hw_from_q

        logger.info(
            "Project {project} running hw_from_q for flow {flow:.4f}", project=self.title or "<untitled>", flow=q
        )
        results: OrderedDict[str, "HydraulicsResult"] = project_hw_from_q(
            project=self,
            q=q,
            hy8=hy8,
            workspace=workspace,
            keep_files=keep_files,
        )
        logger.debug(
            "Project hw_from_q complete for flow {flow:.4f} across {count} crossings",
            flow=q,
            count=len(results),
        )
        return results

    def q_from_hw(
        self,
        hw: float,
        *,
        q_hint: float | None = None,
        hy8: "Hy8Executable | Path | None" = None,
        workspace: Path | None = None,
        keep_files: bool = False,
    ) -> "OrderedDict[str, HydraulicsResult]":
        """Return per-crossing discharges for a requested headwater."""
        from ..hydraulics import project_q_from_hw

        logger.info(
            "Project {project} running q_from_hw for HW {headwater:.4f}",
            project=self.title or "<untitled>",
            headwater=hw,
        )
        results: OrderedDict[str, "HydraulicsResult"] = project_q_from_hw(
            project=self,
            hw=hw,
            q_hint=q_hint,
            hy8=hy8,
            workspace=workspace,
            keep_files=keep_files,
        )
        logger.debug(
            "Project q_from_hw complete for HW {headwater:.4f} across {count} crossings",
            headwater=hw,
            count=len(results),
        )
        return results

    def q_for_hwd(
        self,
        hw_d_ratio: float,
        *,
        q_hint: float | None = None,
        hy8: "Hy8Executable | Path | None" = None,
        workspace: Path | None = None,
        keep_files: bool = False,
    ) -> "OrderedDict[str, HydraulicsResult]":
        """Return per-crossing discharges for a headwater-to-diameter ratio (optionally seeded by q_hint)."""
        from ..hydraulics import project_q_for_hwd

        logger.info(
            "Project {project} running q_for_hwd for ratio {ratio:.4f}",
            project=self.title or "<untitled>",
            ratio=hw_d_ratio,
        )
        results: OrderedDict[str, "HydraulicsResult"] = project_q_for_hwd(
            project=self,
            hw_d_ratio=hw_d_ratio,
            q_hint=q_hint,
            hy8=hy8,
            workspace=workspace,
            keep_files=keep_files,
        )
        logger.debug(
            "Project q_for_hwd complete for ratio {ratio:.4f} across {count} crossings",
            ratio=hw_d_ratio,
            count=len(results),
        )
        return results

    def to_dict(self) -> dict[str, Any]:
        return {
            "title": self.title,
            "designer": self.designer,
            "notes": self.notes,
            "units": self.units.name,
            "exit_loss_option": self.exit_loss_option,
            "crossings": [crossing.to_dict() for crossing in self.crossings],
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "Hy8Project":
        return cls(
            title=data.get("title", ""),
            designer=data.get("designer", ""),
            notes=data.get("notes", ""),
            units=coerce_enum(UnitSystem, data.get("units"), default=UnitSystem.SI),
            exit_loss_option=int(data.get("exit_loss_option", 0)),
            crossings=[
                CulvertCrossing.from_dict(cast(Mapping[str, Any], raw))
                for raw in normalize_sequence(data.get("crossings"))
                if isinstance(raw, Mapping)
            ],
        )
