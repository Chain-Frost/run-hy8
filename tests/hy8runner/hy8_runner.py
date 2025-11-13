"""HY-8 Runner class that will create an HY-8 file and run HY-8."""

from __future__ import annotations

# 1. Standard python modules
import datetime
import os
import subprocess
from _collections_abc import Sequence

# 2. Third party modules

# 3. Aquaveo modules

# 4. Local modules
from .hy8_runner_crossing import Hy8RunnerCulvertCrossing
from .hy8_runner_culvert import Hy8RunnerCulvertBarrel

__copyright__ = "(C) Copyright Aquaveo 2024"
__license__ = "All rights reserved"
# This is not a FHWA product nor is it endorsed by FHWA.
# FHWA will not be providing any technical supporting, funding or maintenance.

__all__: list[str] = ["Hy8Runner"]


class Hy8Runner:
    """A class that will create an HY-8 file and run HY-8."""

    hy8_exe_path: str = ""
    hy8_basename_exe: str = "HY864.exe"
    version: float = 80.0

    si_units: bool = False
    exit_loss_option: int = 0  # 0 for standard or 1 for USU

    name_counter: int = 0

    def __init__(self, hy8_exe_path: str = "", hy8_file: str = "") -> None:
        """Initializes the HY-8 Runner class.

        Args:
            hy8_exe_path (string): The path to the HY-8 executable.
            hy8_file (string): The path to the HY-8 file.
        """
        Hy8Runner.name_counter += 1

        self.crossings: list[Hy8RunnerCulvertCrossing] = [Hy8RunnerCulvertCrossing(0)]
        self.hy8_file: str = hy8_file
        if hy8_exe_path != "":
            Hy8Runner.hy8_exe_path = hy8_exe_path

        self.project_title: str = ""
        self.designer_name: str = ""
        self.project_notes: str = ""

    def set_hy8_exe_path(self, hy8_exe_path: str) -> None:
        """Set the path to the HY-8 executable.

        Args:
            hy8_exe_path (string): The path to the HY-8 executable.
        """
        self.hy8_exe_path = hy8_exe_path

    def set_hy8_file(self, hy8_file: str) -> None:
        """Set the path to the HY-8 file that we will create.

        Args:
            hy8_file (string): The path to the HY-8 file.
        """
        if not hy8_file.lower().endswith(".hy8"):
            hy8_file += ".hy8"
        self.hy8_file = hy8_file

    def add_crossing(self) -> int:
        """Set the path to the HY-8 executable.

        Returns:
            int: The index of the new crossing.
        """
        self.crossings.append(Hy8RunnerCulvertCrossing(len(self.crossings)))
        return len(self.crossings) - 1

    def delete_crossing(self, index: int | None = None) -> None:
        """Set the path to the HY-8 executable.
        Args:
            index (int): The index of the crossing.
        """
        if index is None or index >= len(self.crossings):
            index = len(self.crossings) - 1
        del self.crossings[index]
        if len(self.crossings) == 0:
            self.add_crossing()

    def add_culvert_barrel(self, index_crossing: int | None = None) -> int:
        """Set the path to the HY-8 executable.
        Args:
            index_crossing (int): The index of the crossing.

        Returns:
            int: The index of the new culvert.
        """
        if index_crossing is None:
            index_crossing = len(self.crossings) - 1
        if index_crossing >= len(self.crossings):
            return -1

        self.crossings[index_crossing].culverts.append(
            Hy8RunnerCulvertBarrel(len(self.crossings[index_crossing].culverts))
        )
        return len(self.crossings[index_crossing].culverts) - 1

    def delete_culvert_barrel(self, index_crossing: int | None = None, index_culvert: int | None = None) -> None:
        """Set the path to the HY-8 executable.
        Args:
            index_crossing (int): The index of the crossing.
            index_culvert (int): The index of the culvert_barrel.
        """
        if index_crossing is None:
            index_crossing = len(self.crossings) - 1
        if index_crossing >= len(self.crossings):
            return
        if index_culvert is None:
            index_culvert = len(self.crossings[index_crossing].culverts) - 1
        if index_culvert >= len(self.crossings[index_crossing].culverts):
            return
        del self.crossings[index_crossing].culverts[index_culvert]
        if len(self.crossings[index_crossing].culverts) == 0:
            self.add_culvert_barrel(index_crossing)

    def set_culvert_crossing_name(self, name: str, index: int | None = None) -> None:
        """Set the name of the culvert crossing.

        Args:
            name (string): The name of the crossing.
            index (int): The index of the crossing.
        """
        if index is None or index >= len(self.crossings):
            index = len(self.crossings) - 1
        self.crossings[index].name = name

    def set_discharge_min_design_max_flow(
        self,
        flow_min: float,
        flow_design: float,
        flow_max: float,
        index: int | None = None,
    ) -> None:
        """Set the flow values for the culvert crossing.

        Args:
            flow_min (float): The minimum flow.
            flow_design (float): The design flow.
            flow_max (float): The maximum flow.
            index (int): The index of the crossing.
        """
        if index is None or index >= len(self.crossings):
            index = len(self.crossings) - 1

        self.crossings[index].flow.method = "min-design-max"
        self.crossings[index].flow.flow_min = flow_min
        self.crossings[index].flow.flow_design = flow_design
        self.crossings[index].flow.flow_max = flow_max

    def set_discharge_user_list_flow(self, flow_list: Sequence[float], index: int | None = None) -> None:
        """Set the flow values for the culvert crossing.

        Args:
            flow_list (list of floats): The list of flows.
            index (int): The index of the crossing.
        """
        if index is None or index >= len(self.crossings):
            index = len(self.crossings) - 1

        self.crossings[index].flow.method = "user-defined"
        self.crossings[index].flow.flow_list = list(flow_list)

    def set_discharge_min_max_inc_flow(
        self,
        flow_min: float,
        flow_max: float,
        flow_increment: float,
        index: int | None = None,
    ) -> None:
        """Set the flow values for the culvert crossing.

        Args:
            flow_min (float): The minimum flow.
            flow_max (float): The maximum flow.
            flow_increment (float): The flow increment.
            index (int): The index of the crossing.
        """
        if index is None or index >= len(self.crossings):
            index = len(self.crossings) - 1

        self.crossings[index].flow.method = "min-max-increment"
        self.crossings[index].flow.flow_min = flow_min
        self.crossings[index].flow.flow_max = flow_max
        self.crossings[index].flow.flow_increment = flow_increment
        self.crossings[index].flow.compute_list()

    def set_tw_rectangular(
        self,
        bottom_width: float,
        channel_slope: float,
        manning_n: float,
        invert_elevation: float,
        index: int | None = None,
    ) -> None:
        """Set the tailwater values for the culvert crossing.

        Args:
            tw_invert_elevation (float): The tailwater invert elevation.
            tw_constant_elevation (float): The constant tailwater elevation.
            index (int): The index of the crossing.
        """
        if index is None or index >= len(self.crossings):
            index = len(self.crossings) - 1
        self.crossings[index].tw_type = 1
        self.crossings[index].tw_bottom_width = bottom_width
        self.crossings[index].tw_channel_slope = channel_slope
        self.crossings[index].tw_manning_n = manning_n
        self.crossings[index].tw_invert_elevation = invert_elevation

    def set_tw_trapezoidal(
        self,
        bottom_width: float,
        sideslope: float,
        channel_slope: float,
        manning_n: float,
        invert_elevation: float,
        index: int | None = None,
    ) -> None:
        """Set the tailwater values for the culvert crossing.

        Args:
            tw_invert_elevation (float): The tailwater invert elevation.
            tw_constant_elevation (float): The constant tailwater elevation.
            index (int): The index of the crossing.
        """
        if index is None or index >= len(self.crossings):
            index = len(self.crossings) - 1
        self.crossings[index].tw_type = 2
        self.crossings[index].tw_bottom_width = bottom_width
        self.crossings[index].tw_sideslope = sideslope
        self.crossings[index].tw_channel_slope = channel_slope
        self.crossings[index].tw_manning_n = manning_n
        self.crossings[index].tw_invert_elevation = invert_elevation

    def set_tw_triangular(
        self,
        sideslope: float,
        channel_slope: float,
        manning_n: float,
        invert_elevation: float,
        index: int | None = None,
    ) -> None:
        """Set the tailwater values for the culvert crossing.

        Args:
            tw_invert_elevation (float): The tailwater invert elevation.
            tw_constant_elevation (float): The constant tailwater elevation.
            index (int): The index of the crossing.
        """
        if index is None or index >= len(self.crossings):
            index = len(self.crossings) - 1
        self.crossings[index].tw_type = 3
        self.crossings[index].tw_sideslope = sideslope
        self.crossings[index].tw_channel_slope = channel_slope
        self.crossings[index].tw_manning_n = manning_n
        self.crossings[index].tw_invert_elevation = invert_elevation

    def set_tw_constant(
        self,
        tw_invert_elevation: float,
        tw_constant_elevation: float,
        index: int | None = None,
    ) -> None:
        """Set the tailwater values for the culvert crossing.

        Args:
            tw_invert_elevation (float): The tailwater invert elevation.
            tw_constant_elevation (float): The constant tailwater elevation.
            index (int): The index of the crossing.
        """
        if index is None or index >= len(self.crossings):
            index = len(self.crossings) - 1
        self.crossings[index].tw_type = 6
        self.crossings[index].tw_constant_elevation = tw_constant_elevation
        self.crossings[index].tw_invert_elevation = tw_invert_elevation

    def set_tw_rating_curve(
        self,
        invert_elevation: float,
        rating_curve: Sequence[Sequence[float]],
        index: int | None = None,
    ) -> None:
        """Set the rating curve for the culvert crossing.

        Args:
            invert_elevation (float): The invert elevation of the culvert.
            rating_curve (list of list): The rating curve for the culvert.
        """
        if index is None or index >= len(self.crossings):
            index = len(self.crossings) - 1
        self.crossings[index].tw_type = 5
        self.crossings[index].tw_invert_elevation = invert_elevation
        self.crossings[index].tw_rating_curve = [list(point) for point in rating_curve]

    def set_roadway_width(self, roadway_width: float, index: int | None = None) -> None:
        """Set the roadway width for the culvert crossing.

        Args:
            roadway_width (float): The width of the roadway.
            index (int): The index of the crossing.
        """
        if index is None or index >= len(self.crossings):
            index = len(self.crossings) - 1
        self.crossings[index].roadway_width = roadway_width

    def set_roadway_surface(self, roadway_surface: str, index: int | None = None) -> None:
        """Set the roadway surface for the culvert crossing.

        Args:
            roadway_surface (string): The surface of the roadway: 'paved' or 'gravel'.
            index (int): The index of the crossing.
        """
        if index is None or index >= len(self.crossings):
            index = len(self.crossings) - 1
        self.crossings[index].roadway_surface = roadway_surface

    def set_roadway_stations_and_elevations(
        self,
        stations: Sequence[float],
        elevations: Sequence[float],
        index: int | None = None,
    ) -> None:
        """Add the roadway stations for the culvert crossing.

        Args:
            stations (list of floats): The stations of the roadway.
            elevations (list of floats): The elevations of the roadway.
            index (int): The index of the crossing.
        """
        if index is None or index >= len(self.crossings):
            index = len(self.crossings) - 1
        self.crossings[index].roadway_shape = 2
        self.crossings[index].roadway_stations = list(stations)
        self.crossings[index].roadway_elevations = list(elevations)

    def set_constant_roadway(self, roadway_length: float, elevation: float, index: int | None = None) -> None:
        """Set the roadway stations to a constant elevation for the culvert crossing.
        Args:
            roadway_length (float): The length of the roadway.
            elevation (float): The elevation of the roadway.
            index (int): The index of the crossing.
        """
        if index is None or index >= len(self.crossings):
            index = len(self.crossings) - 1
        self.crossings[index].roadway_shape = 1
        stations = [0.0, roadway_length]
        elevations = [elevation, elevation]
        self.crossings[index].roadway_stations = stations
        self.crossings[index].roadway_elevations = elevations

    def set_culvert_barrel_name(
        self,
        name: str,
        index_crossing: int | None = None,
        index_culvert: int | None = None,
    ) -> None:
        """Set the name of the culvert barrel.

        Args:
            name (string): The name of the culvert barrel.
            index_crossing (int): The index of the crossing.
            index_culvert (int): The index of the barrel.
        """
        if index_crossing is None or index_crossing >= len(self.crossings):
            index_crossing = len(self.crossings) - 1
        if index_culvert is None or index_culvert >= len(self.crossings[index_crossing].culverts):
            index_culvert = len(self.crossings[index_crossing].culverts) - 1
        self.crossings[index_crossing].culverts[index_culvert].name = name

    def set_culvert_barrel_shape(
        self,
        shape: str,
        index_crossing: int | None = None,
        index_culvert: int | None = None,
    ) -> None:
        """Set the shape of the culvert barrel.

        Args:
            shape (string): The shape of the culvert barrel: 'circle' or 'box'.
            index_crossing (int): The index of the crossing.
            index_culvert (int): The index of the barrel.
        """
        if index_crossing is None or index_crossing >= len(self.crossings):
            index_crossing = len(self.crossings) - 1
        if index_culvert is None or index_culvert >= len(self.crossings[index_crossing].culverts):
            index_culvert = len(self.crossings[index_crossing].culverts) - 1
        self.crossings[index_crossing].culverts[index_culvert].shape = shape

    def set_culvert_barrel_span_and_rise(
        self,
        span: float,
        rise: float | None = None,
        index_crossing: int | None = None,
        index_culvert: int | None = None,
    ) -> None:
        """Set the shape of the culvert barrel.

        Args:
            span (float): The span of the culvert barrel.
            rise (float): The rise of the culvert barrel (only need to specify for box shapes)
            index_crossing (int): The index of the crossing.
            index_culvert (int): The index of the barrel.
        """
        if index_crossing is None or index_crossing >= len(self.crossings):
            index_crossing = len(self.crossings) - 1
        if index_culvert is None or index_culvert >= len(self.crossings[index_crossing].culverts):
            index_culvert = len(self.crossings[index_crossing].culverts) - 1
        self.crossings[index_crossing].culverts[index_culvert].span = span
        if rise is not None:
            self.crossings[index_crossing].culverts[index_culvert].rise = rise

    def set_culvert_barrel_material(
        self,
        material: str,
        index_crossing: int | None = None,
        index_culvert: int | None = None,
    ) -> None:
        """Set the material of the culvert barrel.

        Args:
            material (string): The material of the culvert barrel: 'concrete' or 'corrugated steel'.
            index_crossing (int): The index of the crossing.
            index_culvert (int): The index of the barrel.
        """
        if index_crossing is None or index_crossing >= len(self.crossings):
            index_crossing = len(self.crossings) - 1
        if index_culvert is None or index_culvert >= len(self.crossings[index_crossing].culverts):
            index_culvert = len(self.crossings[index_crossing].culverts) - 1
        self.crossings[index_crossing].culverts[index_culvert].material = material

    def set_culvert_barrel_site_data(
        self,
        inlet_invert_station: float,
        inlet_invert_elevation: float,
        outlet_invert_station: float,
        outlet_invert_elevation: float,
        index_crossing: int | None = None,
        index_culvert: int | None = None,
    ) -> None:
        """Set the inlet invert elevation of the culvert barrel.

        Args:
            inlet_invert_station (float): The inlet invert station.
            inlet_invert_elevation (float): The inlet invert elevation.
            outlet_invert_station (float): The outlet invert station.
            outlet_invert_elevation (float): The outlet invert elevation.
            index_crossing (int): The index of the crossing.
            index_culvert (int): The index of the barrel.
        """
        if index_crossing is None or index_crossing >= len(self.crossings):
            index_crossing = len(self.crossings) - 1
        if index_culvert is None or index_culvert >= len(self.crossings[index_crossing].culverts):
            index_culvert = len(self.crossings[index_crossing].culverts) - 1
        self.crossings[index_crossing].culverts[index_culvert].inlet_invert_station = inlet_invert_station
        self.crossings[index_crossing].culverts[index_culvert].inlet_invert_elevation = inlet_invert_elevation
        self.crossings[index_crossing].culverts[index_culvert].outlet_invert_station = outlet_invert_station
        self.crossings[index_crossing].culverts[index_culvert].outlet_invert_elevation = outlet_invert_elevation

    def set_culvert_barrel_number_of_barrels(
        self,
        number_of_barrels: int,
        index_crossing: int | None = None,
        index_culvert: int | None = None,
    ) -> None:
        """Set the number of barrels of the culvert barrel.

        Args:
            number_of_barrels (int): The number of barrels.
            index_crossing (int): The index of the crossing.
            index_culvert (int): The index of the barrel.
        """
        if index_crossing is None or index_crossing >= len(self.crossings):
            index_crossing = len(self.crossings) - 1
        if index_culvert is None or index_culvert >= len(self.crossings[index_crossing].culverts):
            index_culvert = len(self.crossings[index_crossing].culverts) - 1
        self.crossings[index_crossing].culverts[index_culvert].number_of_barrels = number_of_barrels

    def validate_crossings_data(self, overwrite: bool = True) -> tuple[bool, str]:
        """Validate the data.

        Returns:
            bool: True if the data is valid.
            string: The error message if the data is not valid.
        """
        messages = ""
        result = True

        for crossing_index, crossing in enumerate(self.crossings):
            crossing_str = f"Crossing: {crossing.name} with index: {crossing_index} "
            flow_result, flow_messages = crossing.flow.validate_crossings_data(crossing_str)
            if not flow_result:
                result = False
            messages += flow_messages
            if crossing.tw_type == 1:
                if crossing.tw_bottom_width <= 0.0:
                    messages += f"{crossing_str}Enter a tailwater bottom width.\n"
                    result = False
                if crossing.tw_channel_slope <= 0.0:
                    messages += f"{crossing_str}Enter a tailwater channel slope.\n"
                    result = False
                if crossing.tw_manning_n <= 0.0:
                    messages += f"{crossing_str}Enter a tailwater channel Manning's n value.\n"
                    result = False
                if crossing.tw_invert_elevation <= 0.0:
                    messages += f"{crossing_str}Enter a tailwater invert elevation.\n"
                    result = False
            elif crossing.tw_type == 5:
                if len(crossing.tw_rating_curve) == 0:
                    messages += f"{crossing_str}Enter a tailwater Rating curve.\n"
                    result = False
            elif crossing.tw_type == 6:
                if crossing.tw_constant_elevation < crossing.tw_invert_elevation:
                    messages += (
                        f"{crossing_str}Tailwater constant elevation must be greater than tailwater invert elevation.\n"
                    )
                    result = False
            if crossing.roadway_width <= 0:
                messages += f"{crossing_str}Roadway width must be greater than zero.\n"
                result = False
            if len(crossing.roadway_stations) < 2:
                messages += f"{crossing_str}Roadway stations & elevations must have at least two values.\n"
                result = False
            if len(crossing.roadway_stations) != len(crossing.roadway_elevations):
                messages += f"{crossing_str}Roadway stations and elevations must have the same number of values.\n"
                result = False
            if len(crossing.culverts) == 0:
                messages += f"{crossing_str}Crossing must have at least one culvert barrel.\n"
                result = False
            for barrel in crossing.culverts:
                culvert_barrel_str = f"{crossing_str}Culvert barrel: {barrel.name}\t"
                if barrel.span <= 0.0:
                    messages += f"{culvert_barrel_str}span of the culvert must be specified.\n"
                    result = False
                if barrel.shape == "box" and barrel.rise <= 0.0:
                    messages += f"{culvert_barrel_str}rise of the box culvert must be specified.\n"
                    result = False
                if barrel.number_of_barrels <= 0:
                    messages += f"{culvert_barrel_str}Number of barrels must be greater than zero.\n"
                    result = False

        hy8_exe = os.path.join(self.hy8_exe_path, self.hy8_basename_exe)
        if not os.path.exists(hy8_exe):
            messages += f"HY-8 executable does not exist: {hy8_exe}\n"
            result = False

        if self.hy8_file == "":
            messages += "HY-8 file must be specified.\n"
            result = False
        elif os.path.exists(self.hy8_file):
            if overwrite:
                try:
                    with open(self.hy8_file, "w"):
                        pass  # We have verified that it isn't locked
                except OSError:
                    messages += f"File '{self.hy8_file}' is locked."
                    return False, messages
            else:
                messages += f"HY-8 file already exists: {self.hy8_file}\n"
                result = False
        elif os.path.dirname(self.hy8_file) != "" and not os.path.exists(os.path.dirname(self.hy8_file)):
            os.makedirs(os.path.dirname(self.hy8_file))

        return result, messages

    def create_hy8_file(self, overwrite: bool = True) -> tuple[bool, str]:
        """Create the HY-8 file.

        Args:
            overwrite (bool): Overwrite the file if it already exists.

        Returns:
            bool: True if the file was created successfully.
            string: The error message if the file was not created successfully.
        """
        result, messages = self.validate_crossings_data(overwrite=overwrite)
        if not result:
            return result, messages

        if not overwrite and os.path.exists(self.hy8_file):
            return False, "HY-8 file already exists."

        units = 0
        if Hy8Runner.si_units:
            units = 1
        with open(self.hy8_file, "w") as hy8_file:
            hy8_file.write(f"HY8PROJECTFILE{Hy8Runner.version}\n")
            hy8_file.write(f"UNITS  {units}\n")
            hy8_file.write(f"EXITLOSSOPTION  {Hy8Runner.exit_loss_option}\n")
            hy8_file.write(f"PROJTITLE  {self.project_title}\n")
            hy8_file.write(f"PROJDESIGNER  {self.designer_name}\n")
            hy8_file.write(f"STARTPROJNOTES  {self.project_notes}\nENDPROJNOTES\n")
            hy8_file.write(f"PROJDATE  {datetime.datetime.now().timestamp()/3600}\n")
            hy8_file.write(f"NUMCROSSINGS  {len(self.crossings)}\n")

            for crossing in self.crossings:
                crossing.write_crossing_to_file(hy8_file)

            hy8_file.write("ENDPROJECTFILE\n")

        messages += f"HY-8 file created: {self.hy8_file}\n"
        return result, messages

    def _run_hy8_executable(self, commandline_arguments: Sequence[str]) -> None:
        """Run the HY-8 executable with command line arguments.

        Args:
            commandline_arguments (list of strings): The command line arguments to pass to the HY-8
        """
        hy8_exe: str = os.path.join(self.hy8_exe_path, self.hy8_basename_exe)
        command: list[str] = [hy8_exe]
        command.extend(commandline_arguments)
        command.append(self.hy8_file)
        completed_process = subprocess.run(command)
        if completed_process.returncode != 0:
            print(f"Command '{command}' failed with return code {completed_process.returncode}")

    def run_build_full_report(self) -> None:
        """Runs HY-8 and generates a full report in docx."""
        self._run_hy8_executable(["-BuildFullReport"])

    def run_open_save(self) -> None:
        """opens, runs, saves; this creates the rst, plt, rsql files. The rst file has HY-8 results.
        The plt file has the plot information. The rsql file has results beyond HY-8,
        which may be beneficial (freeboard depth, for example)."""
        self._run_hy8_executable(["-OpenRunSave"])

    def run_open_save_plots(self) -> None:
        """opens, runs, saves (same as last function), and creates bitmap plot images for each discharge."""
        self._run_hy8_executable(["-OpenRunSavePlots"])

    def run_build_flow_tw_table(
        self,
        flow_coef: float = 1.1,
        flow_const: float = 0.25,
        units: str = "EN",
        hw_inc: float = 0.25,
        tw_inc: float = 0.25,
    ) -> None:
        """Generates a table for the culvert where it tells you the headwater for a given flow and tailwater."""
        commandline_arguments: list[str] = [
            "-BuildFlowTwTable",
            "FLOWCOEF",
            str(flow_coef),
            "FLOWCONST",
            str(flow_const),
            "UNITS",
            units,
            "HWINC",
            str(hw_inc),
            "TWINC",
            str(tw_inc),
        ]
        self._run_hy8_executable(commandline_arguments)

    def run_build_hw_tw_table(self, units: str = "EN", hw_inc: float = 0.25, tw_inc: float = 0.25) -> None:
        """Generates a table for the culvert where it tells you the flow for a given headwater and tailwater."""
        commandline_arguments: list[str] = [
            "-BuildHwTwTable",
            "UNITS",
            units,
            "HWINC",
            str(hw_inc),
            "TWINC",
            str(tw_inc),
        ]
        self._run_hy8_executable(commandline_arguments)
