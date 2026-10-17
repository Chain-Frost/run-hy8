"""Extract every ShapeDB HDF5 node and derive browsable catalogue tables.

Requires h5py and numpy for this development utility only.
"""

from __future__ import annotations

import argparse
import base64
import csv
import hashlib
import json
import math
from pathlib import Path
from typing import Any

import h5py
import numpy as np


def json_value(value: Any) -> Any:
    if isinstance(value, np.ndarray):
        return json_value(value.tolist())
    if isinstance(value, np.generic):
        return json_value(value.item())
    if isinstance(value, bytes):
        return value.decode("utf-8")
    if isinstance(value, (list, tuple)):
        return [json_value(item) for item in value]
    if isinstance(value, float) and not math.isfinite(value):
        return {"nonfinite_float": str(value)}
    return value


def array_record(value: Any) -> dict[str, Any]:
    array = np.asarray(value)
    if array.dtype.kind not in "Sfi":
        msg = f"Unsupported dtype for lossless extraction: {array.dtype}"
        raise ValueError(msg)
    raw = array.tobytes(order="C")
    return {
        "dtype": array.dtype.str,
        "shape": list(array.shape),
        "values": json_value(array),
        "raw_c_order_base64": base64.b64encode(raw).decode("ascii"),
        "raw_sha256": hashlib.sha256(raw).hexdigest(),
    }


def extract(source: Path, output: Path) -> None:
    source_bytes = source.read_bytes()
    nodes: dict[str, Any] = {}
    tables: list[dict[str, Any]] = []
    parameter_rows: list[dict[str, Any]] = []
    size_rows: list[dict[str, Any]] = []
    with h5py.File(source, "r") as database:

        def visit(name: str, obj: Any) -> None:
            record: dict[str, Any] = {
                "kind": "dataset" if isinstance(obj, h5py.Dataset) else "group",
                "attributes": {key: array_record(value) for key, value in obj.attrs.items()},
            }
            if isinstance(obj, h5py.Dataset):
                record.update(array_record(obj[()]))
            else:
                record["children_in_h5py_iteration_order"] = list(obj.keys())
            nodes["/" + name if name else "/"] = record

        visit("", database)
        database.visititems(visit)
        for path, record in nodes.items():
            if record["kind"] != "group" or not path.endswith("/Parameters"):
                continue
            group = database[path]
            if "Parameter Names" not in group:
                continue
            names = [name for name in json_value(group["Parameter Names"][()]) if name]
            parameters: dict[str, Any] = {}
            for name in names:
                parameter = group[name]
                data = parameter["Data"]
                if data.ndim != 1:
                    msg = f"Expected one catalogue row axis: {data.name}, {data.shape}"
                    raise ValueError(msg)
                parameters[name] = {
                    "data_path": data.name,
                    "english_units": json_value(parameter["English Units"][()]) if "English Units" in parameter else [],
                    "metric_units": json_value(parameter["Metric Units"][()]) if "Metric Units" in parameter else [],
                    "values": json_value(data[()]),
                }
            lengths = {len(parameter["values"]) for parameter in parameters.values()}
            if len(lengths) != 1:
                msg = f"Catalogue parameter lengths differ at {path}: {lengths}"
                raise ValueError(msg)
            count = lengths.pop()
            parent = group.parent
            units = json_value(parent["Units"][()]) if "Units" in parent else []
            table = {
                "path": parent.name,
                "row_count": count,
                "units": units,
                "parameter_names_in_native_order": names,
                "parameters": parameters,
                "geometry_path": parent["Geometry/Data"].name if "Geometry/Data" in parent else None,
            }
            tables.append(table)
            for index in range(count):
                size: dict[str, Any] = {"table_path": parent.name, "row_index_zero_based": index}
                for name, parameter in parameters.items():
                    size[name] = parameter["values"][index]
                    parameter_rows.append(
                        {
                            "table_path": parent.name,
                            "row_index_zero_based": index,
                            "parameter": name,
                            "native_value": parameter["values"][index],
                            "native_units_system": "|".join(units),
                            "english_units": "|".join(parameter["english_units"]),
                            "metric_units": "|".join(parameter["metric_units"]),
                            "data_path": parameter["data_path"],
                        }
                    )
                size_rows.append(size)
        # Independently check the encoded bytes against every original dataset.
        for path, record in nodes.items():
            if record["kind"] == "dataset":
                restored = np.frombuffer(base64.b64decode(record["raw_c_order_base64"]), dtype=record["dtype"])
                restored = restored.reshape(record["shape"])
                original = np.asarray(database[path][()])
                if restored.dtype != original.dtype or restored.tobytes() != original.tobytes():
                    msg = f"Dataset round-trip verification failed: {path}"
                    raise ValueError(msg)
    payload = {
        "schema_version": 1,
        "source": {
            "filename": source.name,
            "size_bytes": len(source_bytes),
            "sha256": hashlib.sha256(source_bytes).hexdigest(),
        },
        "extractor": {
            "script": "scripts/extract_shape_catalogue.py",
            "h5py_version": h5py.__version__,
            "numpy_version": np.__version__,
        },
        "notes": [
            "All datasets and groups are included; raw dataset bytes preserve native dtype and C-order axes.",
            "Native string-array order and empty slots are preserved in nodes.",
            "CSV tables include only explicit Parameters catalogues; other shapes remain fully present in nodes.",
            "Metric Units labels do not indicate stored metric values: each catalogue's Units defines its native system.",
            "Row indices are extraction identifiers, not established GUI or project-card identifiers.",
            "Geometry axis semantics, coordinate units and GUI BARRELGEOMETRY mapping require separate evidence.",
        ],
        "counts": {
            "datasets": sum(node["kind"] == "dataset" for node in nodes.values()),
            "groups_including_root": sum(node["kind"] == "group" for node in nodes.values()),
            "catalogue_tables": len(tables),
            "catalogue_rows": len(size_rows),
        },
        "catalogue_tables": tables,
        "nodes": nodes,
    }
    output.mkdir(parents=True, exist_ok=True)
    (output / "shape_catalogue.json").write_text(
        json.dumps(payload, indent=2, allow_nan=False) + "\n", encoding="utf-8"
    )
    for filename, rows in (("catalogue_sizes.csv", size_rows), ("catalogue_parameters.csv", parameter_rows)):
        fields = list(dict.fromkeys(key for row in rows for key in row))
        with (output / filename).open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=fields)
            writer.writeheader()
            writer.writerows(rows)
    print(json.dumps(payload["counts"]))
    print(f"Source SHA-256: {payload['source']['sha256']}")
    print("All dataset raw-byte round trips verified.")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=Path("reference_docs/ShapeDB.dat"))
    parser.add_argument("--output", type=Path, default=Path("reference_docs/catalogue"))
    args = parser.parse_args()
    extract(args.source, args.output)


if __name__ == "__main__":
    main()
