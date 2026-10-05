# HY-8 GUI comparison project

Open `roadway_gui_review.hy8` in HY-8, run the analysis, then use **Save As** to
save a separate file named `roadway_gui_review_saved.hy8` alongside it. Keep
the generated input file so the saved file can be compared with it. No input
edits are required. A crossing summary table screenshot for `Original-3Q-Free`
and `Original-3Q-Submerged` would also provide displayed result evidence.

This is an adapter-generated project based on the user's GUI-created
`tests/floodway.hy8`. It has ten crossings, with SI display units. All retain
the original ten 0.9 m circular concrete barrels, invert elevations 11/10 m,
30 m horizontal length, and 1 m roadway top width.

| Crossing pair | Roadway | Surface | Discharges (m³/s) |
| --- | --- | --- | --- |
| `Original-3Q` | Original six points | Paved | 8, 30, 100 |
| `Irregular-6Q` | Original six points | Paved | 1, 2, 4, 8, 30, 100 |
| `Irregular-C1.6` | Original six points | User-defined, C = 1.6 SI | 1, 2, 4, 8, 30, 100 |
| `Irregular-Gravel` | Original six points | Gravel | 1, 2, 4, 8, 30, 100 |
| `Constant-6Q` | Original endpoints, level at 19 m | Paved | 1, 2, 4, 8, 30, 100 |

Each pair contains `-Free` (tailwater 12 m) and `-Submerged` (tailwater 19.2 m).
The irregular crest is 19 m. The original irregular stations/elevations are
preserved, rather than simplifying the roadway.

Eight individual six-flow cases successfully ran using HY-8 8.0.1.2
`-OpenRunSave`, with identical parsed reports after reader/writer round-trip.
The two three-flow cases crash that automation command. They are deliberately
included to compare GUI behavior with the failing command-line path.

At 100 m³/s the paved irregular free-flow six-discharge case reports headwater
20.71 m, culvert flow 51.95 m³/s and roadway flow 48.05 m³/s, matching the user's
original GUI screenshot at displayed precision.

Recreate the generated input in a new destination:

```powershell
python scripts/make_roadway_gui_review.py --output validation_artifacts/roadway_gui_review.hy8
```

The generator refuses to overwrite an existing file. The initial generated
project is not a GUI-authored fixture. The separately saved copy will provide
GUI round-trip evidence once it has actually been saved and compared.

The existing generated input predates the irregular flow-padding workaround
and retains the two three-flow cases for comparison. Regenerating with the
updated writer adds exactly three helpers to those cases, retaining the three
requests while avoiding the command-line crash. The existing review input is
deliberately preserved.
