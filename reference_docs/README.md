# HY-8 reference evidence

This directory records version-pinned evidence used to maintain `run-hy8`.
Reference evidence is not a runtime dependency and is not included in the
published `run-hy8` wheel.

## `ShapeDB.dat`

The HY-8 8.0.1.2 installer distributed by FHWA contains `ShapeDB.dat`:

- installer archive: `HY88.00.2Setup.zip`
- setup executable: `HY88.00.2Setup.exe`
- embedded MSI: `HY88.00.2Setup.msi`
- database size: `4,370,624` bytes
- SHA-256: `2479e9444feaff529313e18a1b26fc2de4f6b6c541db58477da6bebc602164a7`

The same byte-identical database is retained through Git LFS in
`Chain-Frost/ryan-culverts/reference_docs/ShapeDB.dat`. It was independently
re-extracted from the official HY-8 package during the issue #5 ellipse audit
and matched the recorded hash.

The binary is mirrored in this repository through Git LFS at
`reference_docs/ShapeDB.dat`. The LFS object was uploaded from a fresh
extraction of the official HY-8 8.0.1.2 installer after verifying both its size
and SHA-256. The accompanying `ShapeDB.dat.sha256` file is the maintained pin
for independent verification.

Keep this file under Git LFS. Do not replace it with a normal Git blob or commit
an LFS pointer without uploading the corresponding LFS object.

A typical local verification on Windows is:

```powershell
Get-FileHash "C:\Program Files\HY-8 8.00\ShapeDB.dat" -Algorithm SHA256
```

The expected hash is the value in `ShapeDB.dat.sha256`.


## Elliptical catalogue evidence

The reproducible extraction under `reference_docs/catalogue/` is generated
from the pinned database above by `scripts/extract_shape_catalogue.py`.
For HY-8 8.0.1.2 it records:

- `Shape Names[2] = "Elliptical"`, corresponding to project-file
  `CULVERTSHAPE 3`;
- elliptical material index 1 = `Steel or Aluminum`;
- elliptical material index 2 = `Concrete`;
- 23 concrete ellipse catalogue sizes;
- 40 Steel-or-Aluminum ellipse catalogue sizes;
- per-size `Span`, `Rise`, `Area`, `Mannings n`, `Br`, `Tr`, `Cr`,
  and `B` values plus raw geometry datasets.

`reference_docs/example-ellipse.hy8` is a GUI-created HY-8 8.0.1.2
Steel-or-Aluminum ellipse reference. It is retained as independent
project-file evidence. Its selected 241 in x 156 in size is present in the
Steel-or-Aluminum ShapeDB catalogue.

The runtime tables in `src/run_hy8/ellipse_catalogue.py` are version-pinned
snapshots of all 23 Concrete and 40 Steel-or-Aluminum ellipse rows. The runtime
package does not depend on the HDF5 reference database.
