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

## Current Limitations

- Constant tailwater elevation only: other HY-8 tailwater definitions are flagged so the user can finish in the GUI.
- Roadway crest protection: if the constant tailwater elevation reaches the roadway elevation we abort with a clear error.
- The JSON loader currently supports HY-8 fundamentals (flow ranges, roadway geometry, culvert barrels). More exotic
  features (rating curves, irregular channels, etc.) are intentionally deferred until the new structure solidifies.

Once these constraints are proven in downstream workflows we can extend the parser/CLI and add regression tests around
validation and serialization behaviors.

## Legacy hy8runner

A separate `hy8runner` implementation lives under `tests/hy8runner` so we can use it for regression comparisons.
It is not published or installed; the only supported way to exercise it is through `tests/test_legacy_regression.py`,
which imports it via `from .hy8runner.hy8_runner import Hy8Runner`.
