"""HY-8 Runner class that will create an HY-8 file and run HY-8."""

from __future__ import annotations

from typing import IO

__copyright__ = "(C) Copyright Aquaveo 2024"
__license__ = "All rights reserved"
# This is not a FHWA product nor is it endorsed by FHWA.
# FHWA will not be providing any technical supporting, funding or maintenance.


class Hy8RunnerCulvertBarrel:
    """A class that will create an HY-8 file and run HY-8."""

    def __init__(self, count: int) -> None:
        """Initializes the HY-8 Runner class."""
        self.name: str = f"Culvert {count + 1}"
        self.notes: str = ""

        self.shape: str = "circle"  # or 'box'
        self.material: str = "concrete"  # or 'corrugated steel'
        self.span: float = 0.0
        self.rise: float = 0.0

        self.inlet_invert_elevation: float = 0.0
        self.inlet_invert_station: float = 0.0
        self.outlet_invert_elevation: float = 0.0
        self.outlet_invert_station: float = 0.0

        self.number_of_barrels: int = 1
        self.roadway_station: float = 0.0
        self.barrel_spacing: float = 0.0

    def write_culvert_to_file(self, hy8_file: IO[str]) -> tuple[bool, str]:
        """Write the culvert data to the file.

        Args:
            f: The file object.

        Returns:
            bool: True if the file was created successfully.
            string: The error message if the file was not created successfully.
        """
        messages = ""
        result = True

        hy8_file.write(f'STARTCULVERT    "{self.name}"\n')

        # Barrel data
        culvert_shape = 1
        culvert_material = 1
        if self.material == "corrugated steel":
            culvert_material = 2
        if self.shape == "box":
            culvert_shape = 2
            culvert_material = 1  # boxes must be concrete (0)

        n_top = 0.012
        n_bot = 0.012
        if culvert_material == 2:
            n_top = 0.024
            n_bot = 0.024
        hy8_file.write(f"CULVERTSHAPE    {culvert_shape}\n")
        hy8_file.write(f"CULVERTMATERIAL {culvert_material}\n")
        hy8_file.write(f"BARRELDATA  {self.span} {self.rise} {n_top} {n_bot}\n")

        # Site Data
        hy8_file.write("EMBANKMENTTYPE 2\n")
        hy8_file.write(f"NUMBEROFBARRELS {self.number_of_barrels}\n")
        hy8_file.write(
            f"INVERTDATA {self.inlet_invert_station} {self.inlet_invert_elevation} "
            f"{self.outlet_invert_station} {self.outlet_invert_elevation}\n"
        )

        # Optional for plotting front view
        self.roadway_station = 0.0
        hy8_file.write(f"ROADCULVSTATION {self.roadway_station}\n")
        self.barrel_spacing = 1.5 * self.span
        hy8_file.write(f"BARRELSPACING {self.barrel_spacing}\n")

        hy8_file.write(f'STARTCULVNOTES "{self.notes}"\nENDCULVNOTES\n')

        hy8_file.write("ENDCULVERT\n")

        return result, messages
