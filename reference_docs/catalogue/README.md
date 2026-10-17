# Complete HY-8 ShapeDB catalogue extraction

Extracted on 7 October 2026 from the retained HY-8 8.0.1.2 database.

## Files

- `shape_catalogue.json`: every dataset and group, including geometry arrays,
  inlet coefficients, dimension defaults, names, units, attributes and empty
  string slots. Also contains a derived index of explicit size tables.
- `catalogue_sizes.csv`: one row per explicit catalogue size; parameter columns
  retain native values. Missing columns mean the parameter is absent from that
  table, not zero.
- `catalogue_parameters.csv`: one row per size and parameter, with native units
  system, English/metric unit labels and exact HDF5 data path.
- `manifest.json`: source identity and hashes of the three generated artifacts.

The JSON is the complete extraction. CSV files are browsing aids and cover only
explicit `Categories/.../Parameters` tables. Shapes such as Circular and
Concrete Box that do not contain these tables are still fully extracted in the
JSON. No catalogue was invented for them.

## Scope and verification

- Source size: 4,370,624 bytes.
- Source SHA-256:
  `2479e9444feaff529313e18a1b26fc2de4f6b6c541db58477da6bebc602164a7`.
- 1,344 datasets and 884 groups including the root.
- 33 explicit catalogue tables, containing 1,077 size rows.
- Every dataset's encoded raw bytes were reconstructed and compared byte for
  byte with the original HDF5 dataset. Fixed-width strings and float32 values
  retain their exact stored representation in `raw_c_order_base64`.
- Re-extraction from the installed database was compared with the saved files.

Native names-array ordering is retained, including blank slots. JSON object key
order and HDF5 group iteration order do not establish GUI enumeration values.
CSV row indices are zero-based source-array indices, not proven project-card
identifiers. Missing unit labels are left empty rather than inferred.

The database's `File Version` is stored as `-1`; the HY-8 executable version is
external provenance, not inferred from that dataset.

## Elliptical catalogue findings

| Material | Size rows | Native units system | Geometry array shape |
| --- | --- | --- | --- |
| Concrete | 23 | English | `[19, 3, 23]` |
| Steel or Aluminum | 40 | English | `[19, 3, 40]` |

Both tables are at
`/Elliptical/<material>/Categories/Category 1/Sub Category 1`.
Their parameter order is `Span`, `Rise`, `Area`, `Mannings n`, `Br`, `Tr`,
`Cr`, `B`, followed by two blank slots in the raw names dataset.
Span/rise and the named geometry parameters carry English `in` labels;
area carries `ft^2`. `Mannings n` has no unit-label datasets.
Metric labels describe display units; the stored catalogue values remain
English values.

Concrete row index 8 is **60 in span x 38 in rise**, corresponding to
1.524 m x 0.9652 m. This confirms that the earlier horizontal test dimensions
are present in the catalogue. The reversed 38 x 60 pair is not separately
listed in this concrete table. Neither this absence nor the raw geometry
arrays establishes whether/how the GUI supports rotating that selection.

The geometry arrays are preserved without assigning coordinate-column meanings
or coordinate units. Their last-axis lengths match the catalogue row counts;
the GUI `BARRELDATA`/`BARRELGEOMETRY` mapping still requires evidence from
GUI-selected and saved catalogue entries. This extraction makes no production
support or hydraulic-validity claim.

## Reproduce

From the repository root, using Python with `h5py` and `numpy` installed:

```powershell
python scripts/extract_shape_catalogue.py
```

These libraries are development extraction dependencies; they were not added
to the runtime package. The extractor fails on unexpected native dtypes,
non-vector parameter tables or inconsistent parameter row counts.

To extract another copy for comparison:

```powershell
python scripts/extract_shape_catalogue.py --source 'C:\Program Files\HY-8 8.00\ShapeDB.dat' --output '<comparison-directory>'
```

For an individual dataset, decode `raw_c_order_base64` with Python's `base64`,
then use `numpy.frombuffer(..., dtype=record['dtype']).reshape(record['shape'])`.
Decoded `values` are provided for browsing; raw bytes are authoritative for
exact native representation.
