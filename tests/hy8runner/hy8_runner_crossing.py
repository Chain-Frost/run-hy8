"""HY-8 Runner class that will create an HY-8 file and run HY-8."""

from __future__ import annotations

from typing import IO

from .hy8_runner_flow import Hy8RunnerFlow
from .hy8_runner_culvert import Hy8RunnerCulvertBarrel

__copyright__ = "(C) Copyright Aquaveo 2024"
__license__ = "All rights reserved"
# This is not a FHWA product nor is it endorsed by FHWA.
# FHWA will not be providing any technical supporting, funding or maintenance.


class Hy8RunnerCulvertCrossing:
    """A class that will create an HY-8 file and run HY-8."""

    def __init__(self, count: int) -> None:
        """Initializes the HY-8 Runner class."""
        self.name: str = f"Crossing {count + 1}"
        self.notes: str = ""

        self.flow: Hy8RunnerFlow = Hy8RunnerFlow()

        self.tw_type: int = 1
        self.tw_bottom_width: float = 0.0
        self.tw_sideslope: float = 1.0
        self.tw_channel_slope: float = 0.0
        self.tw_manning_n: float = 0.0
        self.tw_constant_elevation: float = 0.0
        self.tw_invert_elevation: float = 0.0
        self.tw_rating_curve: list[list[float]] = []

        self.roadway_shape: int = 1
        self.roadway_width: float = 0.0
        self.roadway_stations: list[float] = []
        self.roadway_elevations: list[float] = []
        self.roadway_surface: str = "paved"

        self.culverts: list[Hy8RunnerCulvertBarrel] = [Hy8RunnerCulvertBarrel(0)]

        self.uuid: str | None = None

    def write_crossing_to_file(self, hy8_file: IO[str]) -> tuple[bool, str]:
        """Write the crossing data to the file.

        Args:
            f: The file object.

        Returns:
            bool: True if the file was created successfully.
            string: The error message if the file was not created successfully.
        """
        messages: str = ""
        result: bool = True

        hy8_file.write(f'STARTCROSSING   "{self.name}"\n')
        # Placeholders
        # hy8_file.write(f'LATITUDE {self.lattitude}\n')
        # hy8_file.write(f'LONGITUDE    {self.longitude}\n')
        # hy8_file.write(f'EXISTINGCROSSING {self.existing_crossing}\n')
        # hy8_file.write(f'DISTRICT {self.district}\n')
        # hy8_file.write(f'ADDRESS  {self.address}\n')
        # hy8_file.write(f'COUNTY   {self.county}\n')
        # hy8_file.write(f'CITY {self.city}\n')
        # hy8_file.write(f'STATE    {self.state}\n')
        # hy8_file.write(f'ZIP  {self.zip}\n')

        hy8_file.write(f'STARTCROSSNOTES    "{self.notes}"\n')

        # Discharge
        self.flow.compute_list()
        discharge_method: int = 0
        if self.flow.method != "min-design-max":
            discharge_method = 1
        # Recurrence Flow not currently supported
        hy8_file.write(f"DISCHARGERANGE {self.flow.flow_min} {self.flow.flow_design} {self.flow.flow_max}\n")
        hy8_file.write(f"DISCHARGEMETHOD {discharge_method}\n")
        hy8_file.write(f"DISCHARGEXYUSER {len(self.flow.flow_list)}\n")
        for flow in self.flow.flow_list:
            hy8_file.write(f"DISCHARGEXYUSER_Y {flow}\n")

        # Tailwater
        # 1 for rectangular, 2 for trapezoidal, 3 for triangle, 4 for irregular, 5 for rating curve, 6 for constant tw
        channel_type: int = self.tw_type
        hy8_file.write(f"TAILWATERTYPE {channel_type}\n")
        hy8_file.write(
            f"CHANNELGEOMETRY {self.tw_bottom_width} {self.tw_sideslope} {self.tw_channel_slope} "
            f"{self.tw_manning_n} {self.tw_invert_elevation}\n"
        )
        tw_list: list[float] = [self.tw_constant_elevation] * 6
        vel: float = 0.0
        shear: float = 0.0
        froude: float = 0.0
        hy8_file.write(f"NUMRATINGCURVE {len(tw_list)}\n")
        hy8_file.write(f"TWRATINGCURVE {tw_list[0]} {vel} {shear} {froude}\n")
        for tw in tw_list:
            hy8_file.write(f"              {tw} {vel} {shear} {froude}\n")
        # hy8_file.write(f'IRREGTWCHANNELPTS {num_channel_pts}\n')
        # hy8_file.write(f'IRREGTWCOORDS {station} {elevation} {self.tw_manning_n}\n')
        # for channel_pt in channel_pts:
        #     hy8_file.write(f'              {station} {elevation} {self.tw_manning_n}\n')
        # Additonal rating curve data
        size: int = len(self.tw_rating_curve)
        if size > 0:
            hy8_file.write("RATINGCURVE\n")
            hy8_file.write(f"NUMPOINTS {size}\n")
            for index in range(size):
                hy8_file.write(f"\tFLOW {self.tw_rating_curve[index][0]}\n")
                hy8_file.write(f"\tELEVATION {self.tw_rating_curve[index][1]}\n")
                hy8_file.write(f"\tVELOCITY {self.tw_rating_curve[index][2]}\n")
            hy8_file.write("END RATINGCURVE\n")

        # Roadway Data
        surface_index: int = 1
        if self.roadway_surface == "gravel":
            surface_index = 2
        elif self.roadway_surface == "user-defined":
            surface_index = 3
        hy8_file.write(f"ROADWAYSHAPE {self.roadway_shape}\n")
        hy8_file.write(f"ROADWIDTH {self.roadway_width}\n")
        # hy8_file.write(f'WEIRCOEFF {self.weir_coeff}\n')
        hy8_file.write(f"SURFACE {surface_index}\n")
        hy8_file.write(f"NUMSTATIONS {len(self.roadway_stations)}\n")
        roadway_cardname: str = "ROADWAYSECDATA"
        for station, elevation in zip(self.roadway_stations, self.roadway_elevations):
            hy8_file.write(f"{roadway_cardname} {station} {elevation}\n")
            roadway_cardname = "ROADWAYPOINT"

        # Culvert Data
        hy8_file.write(f"NUMCULVERTS  {len(self.culverts)}\n")

        for culvert in self.culverts:
            culvert.write_culvert_to_file(hy8_file)

        if self.uuid is not None:
            hy8_file.write(f"CROSSGUID            {self.uuid}\n")
        hy8_file.write("ENDCROSSING\n")

        return result, messages
