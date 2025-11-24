# run-hy8
run hy8 and parse outputs via python

Utilities for assembling HY-8 project files and running the HY-8 executable from Python. The focus is on a
pythonic, extensible object model that can be imported into other scripts, with Windows/Python 3.13 as the only
supported runtime.

## Highlights

- Strongly typed dataclasses that describe flows, tailwater, roadway geometry, and culvert barrels.
- Separation between domain objects (`run_hy8.models`), on-disk serialization (`run_hy8.writer`), and process
  orchestration (`run_hy8.executor`).
- Friendly validation helpers that raise actionable errors before the HY-8 binary is invoked. At the moment this
  library intentionally supports a *subset* of HY-8 features (constant tailwater elevation, paved/gravel/user
  roadway surfaces, circle/box culverts). When a configuration requires more advanced HY-8 options we surface a
  clear error that instructs the caller to finish the edit in the HY-8 GUI.
- Small CLI scaffold (`python -m run_hy8`) that can emit a demo file or build projects from 
  JSON configs, and a `validate-only` mode to lint configs without writing any files.

## Project Structure

The `run-hy8` project is organized into the following modules:

-   **`run_hy8.models`**: Contains the core data classes that represent the HY-8 project structure, including `Hy8Project`, `CulvertCrossing`, `CulvertBarrel`, `FlowDefinition`, `TailwaterDefinition`, and `RoadwayProfile`.
-   **`run_hy8.reader`**: Handles the parsing of existing HY-8 project files (`.hy8`) into the object model.
-   **`run_hy8.writer`**: Serializes the object model back into HY-8 project files.
-   **`run_hy8.executor`**: Provides a wrapper around the HY-8 command-line executable for running simulations.
-   **`run_hy8.hydraulics`**: Contains helper functions for running hydraulic scenarios and parsing the results.
-   **`run_hy8.results`**: Parses the HY-8 output files (`.rst` and `.rsql`) into a more usable format.
-   **`run_hy8.cli`**: Implements the command-line interface for the `run-hy8` package.
-   **`run_hy8.config`**: Handles the loading of project configurations from JSON files.
-   **`run_hy8.classes_references`**: Contains core data classes and references for `run-hy8`.
-   **`run_hy8.type_helpers`**: Contains enums and enum helpers shared between HY-8 domain models.
-   **`run_hy8.units`**: Contains unit conversion helpers shared across the `run-hy8` domain.

## Quick Start

```powershell
py -3.13 -m venv .venv
.venv\Scripts\Activate.ps1
pip install -e .
```

```python
from pathlib import Path
from run_hy8 import (
    Hy8Project,
    CulvertCrossing,
    CulvertBarrel,
    FlowDefinition,
    Hy8FileWriter,
)

project = Hy8Project(title="Sample project", designer="River Engineer")
crossing = CulvertCrossing(name="Crossing 1")
crossing.flow = FlowDefinition(minimum=10.0, design=25.0, maximum=50.0)
crossing.tailwater.constant_elevation = 99.1
crossing.tailwater.invert_elevation = 99.0
crossing.culverts.append(CulvertBarrel(name="Barrel 1", span=1.2, rise=1.2))
project.crossings.append(crossing)

writer = Hy8FileWriter(project)
hy8_file = writer.write(Path("output/sample.hy8"))
print(f"Wrote {hy8_file}")
```

Once an `.hy8` file exists you can run HY-8 with `run_hy8.executor.Hy8Executable`. Each high-level action returns
a `CompletedProcess` so scripting layers can inspect stdout/stderr or retry with different parameters.

## Reading existing HY-8 projects

Existing HY-8 files can be parsed back into the same object model via `run_hy8.reader.load_project_from_hy8`. The
[`scripts/gen-hy8-example.py`](scripts/gen-hy8-example.py) helper demonstrates the flow in a standalone script; inline
usage looks like:

```python
from pathlib import Path
from run_hy8 import Hy8FileWriter, load_project_from_hy8

source_path = Path("tests/example_crossings.hy8")
project = load_project_from_hy8(source_path)
project.title = "Round-tripped project"

round_tripped = Hy8FileWriter(project).write(Path("output/round_trip.hy8"))
print(f"Serialized {round_tripped}")
```

This is the same pipeline used in `tests/test_reader.py` to guarantee that we can faithfully read and re-write reference
projects supplied by HY-8.

## Parsing HY-8 outputs

When HY-8 finishes a run it emits `.rst` (culvert summary table) and `.rsql` (flow profile) files next to the project.
`run_hy8.results` contains parsers for both formats plus a `Hy8Results` helper that merges them into easier-to-query
rows:

```python
from pathlib import Path
from run_hy8 import Hy8Results, parse_rst, parse_rsql

crossing = "Crossing 1"
rst_data = parse_rst(Path("output/sample.rst"))
rsql_profiles = parse_rsql(Path("output/sample.rsql"))

series = rst_data.get(crossing, {})
profiles = rsql_profiles.get(crossing, [])
results = Hy8Results(series, profiles)
best_design = results.nearest(target=50.0)
print(f"Design headwater: {best_design.headwater_elevation}")
```

These utilities power `scripts/batch_hy8_compare.py` and let you automate regression checks without opening the HY-8 GUI.

## HY-8 executable location

The repository stores its default HY-8 path inside [`HY8_PATH.txt`](HY8_PATH.txt). Update that file if HY-8 is installed
somewhere else—the helpers automatically pick up the new value. `Hy8Executable()` falls back to the path recorded in the
file (or the `HY8_EXE` / `HY8_EXECUTABLE` environment variables) so scripts can simply do `Hy8Executable()` without
passing a path every time. Call `Hy8Executable.configure_default_path(Path(...))` to override the default for the
current process, or `Hy8Executable.persist_default_path(Path(...))` to update both the in-memory default and the
`HY8_PATH.txt` file. All command-line tooling also respects these settings; pass `--run-exe` to override on a
per-invocation basis if needed.

## Configuration via JSON

For quick scripting, describe your project in JSON and let the CLI write the `.hy8` file. The same schema is used
by the checked-in `sample_project.json`:

```json
{
  "project": {
    "title": "Culvert Replacement",
    "designer": "River Engineer",
    "units": "EN"
  },
  "crossings": [
    {
      "name": "Crossing A",
      "flow": {
        "minimum": 10,
        "design": 25,
        "maximum": 40
      },
      "tailwater": {
        "constant_elevation": 100.5,
        "invert_elevation": 99.0
      },
      "roadway": {
        "width": 40,
        "surface": "paved",
        "stations": [-20, 0, 20],
        "elevations": [102, 101.5, 102]
      },
      "culverts": [
        {
          "name": "Barrel 1",
          "shape": "circle",
          "material": "concrete",
          "span": 4.0,
          "rise": 4.0
        }
      ]
    }
  ]
}
```

```powershell
python -m run_hy8 build --config project.json --output output/sample.hy8 --overwrite
```

If you pass `--run-exe path\to\HY864.exe` the CLI will immediately call `-OpenRunSave` after writing the project.

To lint a configuration without touching the filesystem:

```powershell
python -m run_hy8 build --config sample_project.json --output ignored.hy8 --validate-only
```

## Tests

Targeted unit tests live under `tests`. Run them with:

```powershell
python -m pytest tests
```

## Packaging & automation

The repository includes Windows batch helpers so packaging can happen without remembering long commands.

1. `build_package.bat` installs/updates the [`build`](https://pypi.org/project/build/) backend and then runs `python -m build`, placing the wheel and source distribution under `dist\`.
2. `install_package.bat` installs the most recently built artifact (wheel if present, otherwise the source distribution) via `pip install --force-reinstall`.
3. `run_tests.bat` runs `python -m pytest`. Pass any additional pytest arguments after the script name (for example `run_tests.bat -k culvert`).

Before running tests locally, install the development extras once per virtual environment:

```powershell
pip install -e .[dev]
```

## Contributing

Contributions are welcome! If you would like to contribute to the project, please follow the guidelines in [`docs/agents.md`](docs/agents.md). It is recommended to first open an issue to discuss any planned changes.

Before submitting a pull request, please ensure your changes are `pyright`-clean and that all tests pass. To get started with the development environment:

```powershell
pip install -e .[dev]
```

## Development Notes

Coding agents and contributors should follow the conventions in [`docs/agents.md`](docs/agents.md), including the
project-wide expectation for explicit type hints and `pyright`-clean changes.

## Current Limitations

- Constant tailwater elevation only: other HY-8 tailwater definitions are flagged so the user can finish in the GUI.
- Roadway crest protection: if the constant tailwater elevation reaches the roadway elevation we abort with a clear error.
- The JSON loader currently supports HY-8 fundamentals (flow ranges, roadway geometry, culvert barrels). More exotic
  features (rating curves, irregular channels, etc.) are intentionally deferred until the new structure solidifies.

Once these constraints are proven in downstream workflows we can extend the parser/CLI and add regression tests around
validation and serialization behaviors.

## Legacy hy8runner

A separate `hy8runner` implementation lives under `tests/hy8runner` so we can use it for regression comparisons.
It is not published or installed; the supported entry points are the automated regression test
(`tests/test_legacy_regression.py`) and the comparison workflow in `scripts/sample_crossing_compare.py`, both of which
import it via `from .hy8runner.hy8_runner import Hy8Runner`.
