# HY-8 Runner

## Introduction
The HY-8 Runner is a program designed to create an HY-8 file from basic information and then run HY-8 to generate HY-8 results.
HY-8 is a widely used software for analyzing and designing culverts and channels.

This program aims to simplify the process of creating HY-8 files and running HY-8 simulations by automating the necessary steps.
By providing the required input information, users can easily generate HY-8 files and obtain accurate results without the need for manual data entry.

## Features
- Create HY-8 files: The program allows users to input basic information such as channel dimensions, flow rates, and culvert properties to generate HY-8 files.
- Run HY-8 simulations: Once the HY-8 file is created, the program can execute HY-8 simulations to calculate various hydraulic parameters and generate detailed results.
- Automate the process: The HY-8 Runner automates the process of creating HY-8 files and running simulations, saving time and effort for users.


## Getting Started
To get started with the HY-8 Runner, follow these steps:

Clone or download the project as a zip file:
1. Clone the repository: `git clone https://git.aquaveo.com/Aquaveo/hy8runner.git`
2. Install the required dependencies (from the hy8Runner directory, with path set to the python directory): `pip install hy8Runner`
3. import the hy8Runner module: `from hy8runner.hy8_runner import Hy8Runner`

or

1. Go to 'https://git.aquaveo.com/Aquaveo/hy8runner', click the code button, then select zip under 'download source code'. unzip project to a folder.
2. Install the required dependencies (from the hy8Runner directory, with path set to the python directory): `pip install hy8Runner`
3. import the hy8Runner module: `from hy8runner.hy8_runner import Hy8Runner`

Create an instance of the HY8Runner class. This class provides functions to create and edit culvert crossing information. Each instance of the
HY8Runner class represents a single HY-8 file. It can hold multiple culvert crossings that are part of the same HY-8 file. Each culvert crossing
can have multiple culvert barrels, as is the case in HY-8. Each culvert barrel can have multiple identical culvert barrels, as is the case in HY-8.
HY8Runner is designed to always have at least one culvert crossing. If you need to have multiple culvert crossings, you will need to create multiple
crossings or instances of the HY8Runner class.
The HY-8 executable path only needs to be set once and all HY8Runner instances will use the same path.

Each culvert Crossing needs to have the following information:
- min, max, incremental flow
- tailwater channel definition
- roadway definition
- at least one culvert barrel definition

**Creating or modifying a culvert crossing:**
When working with multiple culvert crossings, many of the functions available include an index parameter. If this index is omitted, the function will
modify the culvert crossing with the last index. The following functions are available to create and edit culvert crossings:

Path Management:
- set_hy8_exe_path: This function sets the path to the HY-8 executable on your system.
- set_hy8_file: This function sets the path to the HY-8 file that will be created.

Crossing Management:
- add_crossing: This function adds a new culvert crossing to the HY-8 file.
- delete_crossing: This function deletes a culvert crossing from the HY-8 file.
- add_culvert_barrel: This function adds a new culvert crossing to the HY-8 file.
- delete_culvert_barrel: This function deletes a culvert crossing from the HY-8 file.

Discharge Data:
- set_discharge_min_design_max_flow: This function sets the minimum, design, and max flow for a culvert crossing, same as HY-8's default flow.
- set_discharge_user_list_flow: This function sets the list of user-defined flows for a culvert crossing, same as HY-8's user-defined flow.
- set_discharge_min_max_inc_flow: This function sets the list of user-defined flows using a min, max, and incremental flows for a culvert crossing.

tailwater Data:
- set_culvert_crossing_tw_constant: This function sets the tailwater information for a culvert crossing.

Roadway Data:
- set_roadway_width: This function sets the roadway width for a culvert crossing.
- set_roadway_surface: This function sets the roadway surface for a culvert crossing.
- set_roadway_stations_and_elevations: This function sets the roadway stations and elevations for a culvert crossing.
- set_constant_roadway: This function sets the roadway as constant for a culvert crossing.

Barrel Data:
- set_culvert_barrel_name: This function sets the name for a culvert barrel.
- set_culvert_barrel_shape: This function sets the shape for a culvert barrel.
- set_culvert_barrel_material: This function sets the material for a culvert barrel.
- set_culvert_barrel_span_and_rise: This function sets the span and rise for a culvert barrel.

Site Data:
- set_culvert_barrel_site_data: This function sets the site data for a culvert barrel.
- set_culvert_barrel_number_of_barrels: This function sets the number of barrels for a culvert crossing.

**Validating Data**
Once you have a culvert crossing defined, you can verify the data by calling the following function:
- validate_crossings_data: This function will validate the data for all culvert crossings and return an array of errors messages.

**Writing HY-8 File**
When you have a culvert crossing defined and validated, you can write a HY-8 file to disk, using the following function:
- writeHy8File: This function will write the HY-8 file to disk.

**Generating HY-8 Results**
You can then use the following functions to run the HY-8 file:
- run_build_full_report: This function will run the HY-8 file and generate a full report in docx format.
- run_open_save: opens, runs, saves; this creates the rst, plt, rsql files. The rst file has HY-8 results. The plt file has the plot information. The rsql file has results beyond HY-8, which may be beneficial (freeboard depth, for example).
- run_open_save_plot: opens, runs, saves (same as last function), and creates bitmap plot images for each discharge.
- run_build_flow_tw_table: Generates a table for the culvert where it tells you the headwater for a given flow and tailwater.
- run_build_hw_tw_table: Generates a table for the culvert where it tells you the flow for a given headwater and tailwater.

**Further Development Options**
- Set notes for project and or crossing
- Set the tailwater based on geometry (square, trapezoidal, triangular, or user-defined)
- Set lattitude and longitude for crossing, district, state, county, address, city, zip
- Specify UUID for crossings
- Implement spacing and roadway station for front view plotting

## Dependencies
The HY-8 Runner relies on the following dependencies:

- Node.js: The program is built using Node.js, a JavaScript runtime environment.
- HY-8: HY-8 software must be installed on your system to run the generated HY-8 files and obtain results.


## Contact
For any inquiries or further information, please contact [EJones@aquaveo.com](mailto:EJones@aquaveo).
