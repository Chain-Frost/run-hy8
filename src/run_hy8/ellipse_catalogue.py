"""Version-pinned HY-8 8.0.1.2 concrete elliptical size catalogue.

The entries are a checked-in runtime snapshot of:
/Elliptical/Concrete/Categories/Category 1/Sub Category 1

in reference_docs/ShapeDB.dat. The source database SHA-256 is
2479e9444feaff529313e18a1b26fc2de4f6b6c541db58477da6bebc602164a7.

HY-8 exposes ellipses as catalogue selections. This module deliberately does
not synthesize arbitrary ellipse sizes or rotate a horizontal catalogue entry
into a vertical one.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

INCH_TO_METRE = 0.0254
INCH_TO_FOOT = 1.0 / 12.0
SQUARE_FOOT_TO_SQUARE_METRE = 0.09290304

# HY-8 project files are written to six decimal places in feet. Half one file
# unit at that precision is about 0.0000001524 m; 2e-6 m comfortably covers a
# write/read round trip while remaining far below catalogue size spacing.
ELLIPSE_CATALOGUE_MATCH_TOLERANCE_M = 2e-6

ELLIPSE_CONCRETE_SOURCE_PATH = "/Elliptical/Concrete/Categories/Category 1/Sub Category 1"


@dataclass(frozen=True, slots=True)
class EllipticalCatalogueSize:
    """One concrete elliptical size observed in HY-8 8.0.1.2 ShapeDB.dat."""

    row_index_zero_based: int
    span_in: float
    rise_in: float
    area_ft2: float
    manning_n: float
    br_in: float
    tr_in: float
    cr_in: float
    b_in: float

    @property
    def span_m(self) -> float:
        """Return the catalogue span in metres."""
        return self.span_in * INCH_TO_METRE

    @property
    def rise_m(self) -> float:
        """Return the catalogue rise in metres."""
        return self.rise_in * INCH_TO_METRE

    @property
    def area_m2(self) -> float:
        """Return the catalogue full-section area in square metres."""
        return self.area_ft2 * SQUARE_FOOT_TO_SQUARE_METRE

    @property
    def geometry_prefix_ft(self) -> tuple[float, float, float, float]:
        """Return ShapeDB Br/Tr/Cr/B in HY-8 project-file length units."""
        return (
            self.br_in * INCH_TO_FOOT,
            self.tr_in * INCH_TO_FOOT,
            self.cr_in * INCH_TO_FOOT,
            self.b_in * INCH_TO_FOOT,
        )


CONCRETE_ELLIPSE_CATALOGUE: tuple[EllipticalCatalogueSize, ...] = (
    EllipticalCatalogueSize(
        row_index_zero_based=0,
        span_in=23,
        rise_in=14,
        area_ft2=1.8200000524520874,
        manning_n=0.012000000104308128,
        br_in=19.940000534057617,
        tr_in=19.940000534057617,
        cr_in=6.090000152587891,
        b_in=7,
    ),
    EllipticalCatalogueSize(
        row_index_zero_based=1,
        span_in=30,
        rise_in=19,
        area_ft2=3.2200000286102295,
        manning_n=0.012000000104308128,
        br_in=26.239999771118164,
        tr_in=26.239999771118164,
        cr_in=8.210000038146973,
        b_in=9.5,
    ),
    EllipticalCatalogueSize(
        row_index_zero_based=2,
        span_in=34,
        rise_in=22,
        area_ft2=4.099999904632568,
        manning_n=0.012000000104308128,
        br_in=29.25,
        tr_in=29.25,
        cr_in=9.25,
        b_in=11,
    ),
    EllipticalCatalogueSize(
        row_index_zero_based=3,
        span_in=38,
        rise_in=24,
        area_ft2=5.130000114440918,
        manning_n=0.012000000104308128,
        br_in=32.79999923706055,
        tr_in=32.79999923706055,
        cr_in=10.260000228881836,
        b_in=12,
    ),
    EllipticalCatalogueSize(
        row_index_zero_based=4,
        span_in=42,
        rise_in=27,
        area_ft2=6.369999885559082,
        manning_n=0.012000000104308128,
        br_in=36.20000076293945,
        tr_in=36.20000076293945,
        cr_in=11.449999809265137,
        b_in=13.5,
    ),
    EllipticalCatalogueSize(
        row_index_zero_based=5,
        span_in=45,
        rise_in=29,
        area_ft2=7.340000152587891,
        manning_n=0.012000000104308128,
        br_in=39.36000061035156,
        tr_in=39.36000061035156,
        cr_in=12.319999694824219,
        b_in=14.5,
    ),
    EllipticalCatalogueSize(
        row_index_zero_based=6,
        span_in=49,
        rise_in=32,
        area_ft2=8.8100004196167,
        manning_n=0.012000000104308128,
        br_in=42.65999984741211,
        tr_in=42.65999984741211,
        cr_in=13.550000190734863,
        b_in=16,
    ),
    EllipticalCatalogueSize(
        row_index_zero_based=7,
        span_in=53,
        rise_in=34,
        area_ft2=10.149999618530273,
        manning_n=0.012000000104308128,
        br_in=45.900001525878906,
        tr_in=45.900001525878906,
        cr_in=14.600000381469727,
        b_in=17,
    ),
    EllipticalCatalogueSize(
        row_index_zero_based=8,
        span_in=60,
        rise_in=38,
        area_ft2=12.850000381469727,
        manning_n=0.012000000104308128,
        br_in=51.599998474121094,
        tr_in=51.599998474121094,
        cr_in=16.43000030517578,
        b_in=19,
    ),
    EllipticalCatalogueSize(
        row_index_zero_based=9,
        span_in=68,
        rise_in=43,
        area_ft2=16.489999771118164,
        manning_n=0.012000000104308128,
        br_in=58.400001525878906,
        tr_in=58.400001525878906,
        cr_in=18.649999618530273,
        b_in=21.5,
    ),
    EllipticalCatalogueSize(
        row_index_zero_based=10,
        span_in=76,
        rise_in=48,
        area_ft2=20.549999237060547,
        manning_n=0.012000000104308128,
        br_in=65.08999633789062,
        tr_in=65.08999633789062,
        cr_in=20.670000076293945,
        b_in=24,
    ),
    EllipticalCatalogueSize(
        row_index_zero_based=11,
        span_in=83,
        rise_in=53,
        area_ft2=24.770000457763672,
        manning_n=0.012000000104308128,
        br_in=71.5199966430664,
        tr_in=71.5199966430664,
        cr_in=22.75,
        b_in=26.5,
    ),
    EllipticalCatalogueSize(
        row_index_zero_based=12,
        span_in=91,
        rise_in=58,
        area_ft2=29.690000534057617,
        manning_n=0.012000000104308128,
        br_in=77.94999694824219,
        tr_in=77.94999694824219,
        cr_in=24.84000015258789,
        b_in=29,
    ),
    EllipticalCatalogueSize(
        row_index_zero_based=13,
        span_in=98,
        rise_in=63,
        area_ft2=34.72999954223633,
        manning_n=0.012000000104308128,
        br_in=84.37999725341797,
        tr_in=84.37999725341797,
        cr_in=26.93000030517578,
        b_in=31.5,
    ),
    EllipticalCatalogueSize(
        row_index_zero_based=14,
        span_in=106,
        rise_in=68,
        area_ft2=40.529998779296875,
        manning_n=0.012000000104308128,
        br_in=90.80999755859375,
        tr_in=90.80999755859375,
        cr_in=29.020000457763672,
        b_in=34,
    ),
    EllipticalCatalogueSize(
        row_index_zero_based=15,
        span_in=113,
        rise_in=72,
        area_ft2=45.849998474121094,
        manning_n=0.012000000104308128,
        br_in=97.23999786376953,
        tr_in=97.23999786376953,
        cr_in=31.110000610351562,
        b_in=36,
    ),
    EllipticalCatalogueSize(
        row_index_zero_based=16,
        span_in=121,
        rise_in=77,
        area_ft2=52.470001220703125,
        manning_n=0.012000000104308128,
        br_in=103.66000366210938,
        tr_in=103.66000366210938,
        cr_in=33.189998626708984,
        b_in=38.5,
    ),
    EllipticalCatalogueSize(
        row_index_zero_based=17,
        span_in=128,
        rise_in=82,
        area_ft2=59.20000076293945,
        manning_n=0.012000000104308128,
        br_in=110,
        tr_in=110,
        cr_in=35.25,
        b_in=41,
    ),
    EllipticalCatalogueSize(
        row_index_zero_based=18,
        span_in=136,
        rise_in=87,
        area_ft2=66.61000061035156,
        manning_n=0.012000000104308128,
        br_in=116.2699966430664,
        tr_in=116.2699966430664,
        cr_in=37.45000076293945,
        b_in=43.5,
    ),
    EllipticalCatalogueSize(
        row_index_zero_based=19,
        span_in=143,
        rise_in=92,
        area_ft2=74,
        manning_n=0.012000000104308128,
        br_in=122.75,
        tr_in=122.75,
        cr_in=39.5,
        b_in=46,
    ),
    EllipticalCatalogueSize(
        row_index_zero_based=20,
        span_in=151,
        rise_in=97,
        area_ft2=82.4000015258789,
        manning_n=0.012000000104308128,
        br_in=129.1300048828125,
        tr_in=129.1300048828125,
        cr_in=41.619998931884766,
        b_in=48.5,
    ),
    EllipticalCatalogueSize(
        row_index_zero_based=21,
        span_in=166,
        rise_in=106,
        area_ft2=99.19999694824219,
        manning_n=0.012000000104308128,
        br_in=142,
        tr_in=142,
        cr_in=45.75,
        b_in=53,
    ),
    EllipticalCatalogueSize(
        row_index_zero_based=22,
        span_in=180,
        rise_in=116,
        area_ft2=118.5999984741211,
        manning_n=0.012000000104308128,
        br_in=154.75,
        tr_in=154.75,
        cr_in=50,
        b_in=58,
    ),
)


def find_concrete_ellipse_catalogue_size(
    span_m: float,
    rise_m: float,
    *,
    tolerance_m: float = ELLIPSE_CATALOGUE_MATCH_TOLERANCE_M,
) -> EllipticalCatalogueSize:
    """Return the exact supported HY-8 concrete ellipse catalogue selection.

    Span and rise are orientation-sensitive. A reversed pair is not accepted
    unless that reversed pair is independently present in the HY-8 catalogue.
    """
    if not math.isfinite(span_m) or not math.isfinite(rise_m):
        msg = "Elliptical span and rise must be finite."
        raise ValueError(msg)
    if tolerance_m < 0.0 or not math.isfinite(tolerance_m):
        msg = "Ellipse catalogue matching tolerance must be finite and non-negative."
        raise ValueError(msg)

    matches = [
        entry
        for entry in CONCRETE_ELLIPSE_CATALOGUE
        if abs(entry.span_m - span_m) <= tolerance_m and abs(entry.rise_m - rise_m) <= tolerance_m
    ]
    if len(matches) == 1:
        return matches[0]
    if len(matches) > 1:  # pragma: no cover - protected by catalogue uniqueness
        msg = f"Ambiguous HY-8 concrete ellipse catalogue match for span={span_m:.9g} m, rise={rise_m:.9g} m."
        raise ValueError(msg)

    nearest = min(
        CONCRETE_ELLIPSE_CATALOGUE,
        key=lambda entry: math.hypot(entry.span_m - span_m, entry.rise_m - rise_m),
    )
    msg = (
        "Unsupported HY-8 concrete elliptical size "
        f"span={span_m:.9g} m, rise={rise_m:.9g} m. "
        "HY-8 8.0.1.2 requires a catalogued ellipse size; no nearest-size "
        "substitution is performed. "
        f"Closest catalogue entry is {nearest.span_in:g} in x {nearest.rise_in:g} in "
        f"(row {nearest.row_index_zero_based})."
    )
    raise ValueError(msg)


__all__: list[str] = [
    "CONCRETE_ELLIPSE_CATALOGUE",
    "ELLIPSE_CATALOGUE_MATCH_TOLERANCE_M",
    "ELLIPSE_CONCRETE_SOURCE_PATH",
    "EllipticalCatalogueSize",
    "find_concrete_ellipse_catalogue_size",
]
