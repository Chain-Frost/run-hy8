# HY-8 reference evidence

This directory records version-pinned evidence used to maintain `run-hy8`.
Reference evidence is not a runtime dependency.

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

The binary itself should be tracked with Git LFS if mirrored in this repository.
Do not commit a normal Git blob for the 4.37 MB HDF5 database. The hash file in
this directory is the maintained pin used to verify any local or mirrored copy.

A typical local verification on Windows is:

```powershell
Get-FileHash "C:\Program Files\HY-8 8.00\ShapeDB.dat" -Algorithm SHA256
```

The expected hash is the value in `ShapeDB.dat.sha256`.
