"""Culvert crossing definition that bundles flow/tailwater/culvert data."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Mapping, TYPE_CHECKING, cast
from _collections_abc import Mapping
from loguru import logger
from .base import Validatable, normalize_mapping, normalize_sequence
from ..classes_references import UnitSystem
from .flow_definition import FlowDefinition
from .tailwater_definition import TailwaterDefinition
from .roadway_profile import RoadwayProfile
from .culvert_barrel import CulvertBarrel


if TYPE_CHECKING:
    from ..executor import Hy8Executable
    from ..hydraulics import HydraulicsResult
    from .project import Hy8Project


def _culvert_list() -> list["CulvertBarrel"]:
    """Return a fresh list of CulvertBarrel objects for defaults."""

    return []


@dataclass(slots=True)
class CulvertCrossing(Validatable):
    """A culvert crossing which may contain multiple barrels."""

    name: str
    notes: str = ""
    flow: FlowDefinition = field(default_factory=FlowDefinition)
    tailwater: TailwaterDefinition = field(default_factory=TailwaterDefinition)
    roadway: RoadwayProfile = field(default_factory=RoadwayProfile)
    culverts: list[CulvertBarrel] = field(default_factory=_culvert_list)
    uuid: str | None = None

    def describe(self) -> str:
        barrel_count: int = len(self.culverts)
        crest: float | None = None
        if self.roadway.elevations:
            crest = self.roadway.crest_elevation()
        crest_str: str = f", crest={crest:.3f}" if crest is not None else ""
        return (
            f"CulvertCrossing(name={self.name}, barrels={barrel_count}, flow_method={self.flow.method.name}"
            f"{crest_str})"
        )

    def __str__(self) -> str:
        return self.describe()

    def __repr__(self) -> str:
        return self.describe()

    def validate(self, prefix: str = "") -> list[str]:
        errors: list[str] = []
        flow_prefix: str = f"{prefix}Flow: "
        errors.extend(self.flow.validate(flow_prefix))
        tw_prefix: str = f"{prefix}Tailwater: "
        errors.extend(self.tailwater.validate(tw_prefix))
        roadway_prefix: str = f"{prefix}Roadway: "
        errors.extend(self.roadway.validate(roadway_prefix))
        if not self.culverts:
            errors.append(f"{prefix}At least one culvert barrel is required.")
        for index, culvert in enumerate(self.culverts, start=1):
            culvert_prefix: str = f"{prefix}Culvert #{index} ({culvert.name}): "
            errors.extend(culvert.validate(culvert_prefix))
        if self.roadway.elevations:
            road_crest: float = self.roadway.crest_elevation()
            if self.tailwater.constant_elevation >= road_crest:
                errors.append(
                    f"{prefix}Constant tailwater elevation ({self.tailwater.constant_elevation}) "
                    f"reaches or exceeds the roadway crest ({road_crest}). "
                    "Lower the tailwater or use the HY-8 GUI for overtopping conditions."
                )
        return errors

    def add_barrel(self, barrel: CulvertBarrel | None = None, **kwargs: Any) -> CulvertBarrel:
        """Append a barrel definition, optionally constructing one from kwargs."""

        if barrel is not None and kwargs:
            raise ValueError("Provide either a barrel instance or keyword arguments, not both.")
        if barrel is None:
            options: dict[str, Any] = dict(kwargs)
            options.setdefault("name", f"Barrel {len(self.culverts) + 1}")
            barrel = CulvertBarrel(**options)
        self.culverts.append(barrel)
        logger.debug("Added barrel {barrel} to crossing {crossing}", barrel=barrel.describe(), crossing=self.name)
        return barrel

    def hw_from_q(
        self,
        q: float,
        *,
        hy8: "Hy8Executable | Path | None" = None,
        project: "Hy8Project | None" = None,
        units: UnitSystem | None = None,
        exit_loss_option: int | None = None,
        workspace: Path | None = None,
        keep_files: bool = False,
    ) -> "HydraulicsResult":
        """Run HY-8 for a specific discharge and return the resulting headwater."""
        from ..hydraulics import crossing_hw_from_q

        logger.info("Crossing {name} running hw_from_q for flow {flow:.4f}", name=self.name, flow=q)
        result: HydraulicsResult = crossing_hw_from_q(
            crossing=self,
            q=q,
            hy8=hy8,
            project=project,
            units=units,
            exit_loss_option=exit_loss_option,
            workspace=workspace,
            keep_files=keep_files,
        )
        logger.debug(
            "Crossing {name} hw_from_q computed headwater {headwater:.4f} for flow {flow:.4f}",
            name=self.name,
            headwater=result.computed_headwater,
            flow=result.computed_flow,
        )
        return result

    def q_from_hw(
        self,
        hw: float,
        *,
        q_hint: float | None = None,
        hy8: "Hy8Executable | Path | None" = None,
        project: "Hy8Project | None" = None,
        units: UnitSystem | None = None,
        exit_loss_option: int | None = None,
        workspace: Path | None = None,
        keep_files: bool = False,
    ) -> "HydraulicsResult":
        """Iteratively run HY-8 to find the discharge that produces the requested headwater."""
        from ..hydraulics import crossing_q_from_hw

        logger.info("Crossing {name} running q_from_hw for HW {headwater:.4f}", name=self.name, headwater=hw)
        result: HydraulicsResult = crossing_q_from_hw(
            crossing=self,
            hw=hw,
            q_hint=q_hint,
            hy8=hy8,
            project=project,
            units=units,
            exit_loss_option=exit_loss_option,
            workspace=workspace,
            keep_files=keep_files,
        )
        logger.debug(
            "Crossing {name} q_from_hw computed flow {flow:.4f} for headwater {headwater:.4f}",
            name=self.name,
            flow=result.computed_flow,
            headwater=result.requested_headwater or hw,
        )
        return result

    def q_for_hwd(
        self,
        hw_d_ratio: float,
        *,
        q_hint: float | None = None,
        hy8: "Hy8Executable | Path | None" = None,
        project: "Hy8Project | None" = None,
        units: UnitSystem | None = None,
        exit_loss_option: int | None = None,
        workspace: Path | None = None,
        keep_files: bool = False,
    ) -> "HydraulicsResult":
        """Run HY-8 to find the discharge that satisfies a headwater-to-diameter ratio (optionally seeding with q_hint)."""
        from ..hydraulics import crossing_q_for_hwd

        logger.info("Crossing {name} running q_for_hwd for ratio {ratio:.4f}", name=self.name, ratio=hw_d_ratio)
        result: HydraulicsResult = crossing_q_for_hwd(
            crossing=self,
            hw_d_ratio=hw_d_ratio,
            q_hint=q_hint,
            hy8=hy8,
            project=project,
            units=units,
            exit_loss_option=exit_loss_option,
            workspace=workspace,
            keep_files=keep_files,
        )
        logger.debug(
            "Crossing {name} q_for_hwd computed flow {flow:.4f} for HW/D {ratio:.4f}",
            name=self.name,
            flow=result.computed_flow,
            ratio=hw_d_ratio,
        )
        return result

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "notes": self.notes,
            "flow": self.flow.to_dict(),
            "tailwater": self.tailwater.to_dict(),
            "roadway": self.roadway.to_dict(),
            "culverts": [culvert.to_dict() for culvert in self.culverts],
            "uuid": self.uuid,
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "CulvertCrossing":
        flow_data: FlowDefinition = FlowDefinition.from_dict(normalize_mapping(data.get("flow")))
        tailwater_data: TailwaterDefinition = TailwaterDefinition.from_dict(normalize_mapping(data.get("tailwater")))
        roadway_data: RoadwayProfile = RoadwayProfile.from_dict(normalize_mapping(data.get("roadway")))
        culvert_data: list[CulvertBarrel] = [
            CulvertBarrel.from_dict(cast(Mapping[str, Any], raw))
            for raw in normalize_sequence(data.get("culverts"))
            if isinstance(raw, Mapping)
        ]
        return cls(
            name=data.get("name", "Crossing"),
            notes=str(data.get("notes", "")),
            flow=flow_data,
            tailwater=tailwater_data,
            roadway=roadway_data,
            culverts=culvert_data,
            uuid=data.get("uuid"),
        )
