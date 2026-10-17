"""Version-pinned HY-8 8.0.1.2 elliptical size catalogues.

The entries are checked-in runtime snapshots of the two HY-8 ellipse tables in
reference_docs/ShapeDB.dat:

- /Elliptical/Concrete/Categories/Category 1/Sub Category 1
- /Elliptical/Steel or Aluminum/Categories/Category 1/Sub Category 1

The source database SHA-256 is
2479e9444feaff529313e18a1b26fc2de4f6b6c541db58477da6bebc602164a7.

HY-8 exposes ellipses as material-specific catalogue selections. This module
deliberately does not synthesize arbitrary ellipse sizes, rotate entries, or
substitute a nearby catalogue size.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from .type_helpers import CulvertMaterial

INCH_TO_METRE = 0.0254
INCH_TO_FOOT = 1.0 / 12.0
SQUARE_FOOT_TO_SQUARE_METRE = 0.09290304

# HY-8 project files are written to six decimal places in feet. Half one file
# unit at that precision is about 0.0000001524 m; 2e-6 m comfortably covers a
# write/read round trip while remaining far below catalogue size spacing.
ELLIPSE_CATALOGUE_MATCH_TOLERANCE_M = 2e-6

ELLIPSE_CONCRETE_SOURCE_PATH = "/Elliptical/Concrete/Categories/Category 1/Sub Category 1"
ELLIPSE_STEEL_OR_ALUMINUM_SOURCE_PATH = "/Elliptical/Steel or Aluminum/Categories/Category 1/Sub Category 1"


@dataclass(frozen=True, slots=True)
class EllipticalCatalogueSize:
    """One material-specific elliptical size observed in HY-8 8.0.1.2."""

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

STEEL_OR_ALUMINUM_ELLIPSE_CATALOGUE: tuple[EllipticalCatalogueSize, ...] = (
    EllipticalCatalogueSize(
        row_index_zero_based=0,
        span_in=232,
        rise_in=153,
        area_ft2=190.9199981689453,
        manning_n=0.03400000184774399,
        br_in=150,
        tr_in=150,
        cr_in=54,
        b_in=76.5,
    ),
    EllipticalCatalogueSize(
        row_index_zero_based=1,
        span_in=241,
        rise_in=156,
        area_ft2=201.85000610351562,
        manning_n=0.03400000184774399,
        br_in=157,
        tr_in=157,
        cr_in=54,
        b_in=78,
    ),
    EllipticalCatalogueSize(
        row_index_zero_based=2,
        span_in=242,
        rise_in=143,
        area_ft2=183.83999633789062,
        manning_n=0.03400000184774399,
        br_in=164,
        tr_in=164,
        cr_in=43,
        b_in=71.5,
    ),
    EllipticalCatalogueSize(
        row_index_zero_based=3,
        span_in=250,
        rise_in=146,
        area_ft2=193.8000030517578,
        manning_n=0.03400000184774399,
        br_in=171,
        tr_in=171,
        cr_in=43,
        b_in=73,
    ),
    EllipticalCatalogueSize(
        row_index_zero_based=4,
        span_in=252,
        rise_in=182,
        area_ft2=248.75999450683594,
        manning_n=0.032999999821186066,
        br_in=157,
        tr_in=157,
        cr_in=71,
        b_in=91,
    ),
    EllipticalCatalogueSize(
        row_index_zero_based=5,
        span_in=263,
        rise_in=157,
        area_ft2=219.9199981689453,
        manning_n=0.032999999821186066,
        br_in=178,
        tr_in=178,
        cr_in=49,
        b_in=78.5,
    ),
    EllipticalCatalogueSize(
        row_index_zero_based=6,
        span_in=270,
        rise_in=188,
        area_ft2=274.6099853515625,
        manning_n=0.032999999821186066,
        br_in=171,
        tr_in=171,
        cr_in=71,
        b_in=94,
    ),
    EllipticalCatalogueSize(
        row_index_zero_based=7,
        span_in=276,
        rise_in=169,
        area_ft2=249.11000061035156,
        manning_n=0.032999999821186066,
        br_in=185,
        tr_in=185,
        cr_in=54,
        b_in=84.5,
    ),
    EllipticalCatalogueSize(
        row_index_zero_based=8,
        span_in=279,
        rise_in=191,
        area_ft2=287.9100036621094,
        manning_n=0.032999999821186066,
        br_in=178,
        tr_in=178,
        cr_in=71,
        b_in=95.5,
    ),
    EllipticalCatalogueSize(
        row_index_zero_based=9,
        span_in=292,
        rise_in=203,
        area_ft2=320.5,
        manning_n=0.032999999821186066,
        br_in=185,
        tr_in=185,
        cr_in=76,
        b_in=101.5,
    ),
    EllipticalCatalogueSize(
        row_index_zero_based=10,
        span_in=294,
        rise_in=176,
        area_ft2=275.260009765625,
        manning_n=0.032999999821186066,
        br_in=198,
        tr_in=198,
        cr_in=54,
        b_in=88,
    ),
    EllipticalCatalogueSize(
        row_index_zero_based=11,
        span_in=302,
        rise_in=179,
        area_ft2=287.45001220703125,
        manning_n=0.032999999821186066,
        br_in=205,
        tr_in=205,
        cr_in=54,
        b_in=89.5,
    ),
    EllipticalCatalogueSize(
        row_index_zero_based=12,
        span_in=305,
        rise_in=201,
        area_ft2=329.9700012207031,
        manning_n=0.032999999821186066,
        br_in=198,
        tr_in=198,
        cr_in=71,
        b_in=100.5,
    ),
    EllipticalCatalogueSize(
        row_index_zero_based=13,
        span_in=313,
        rise_in=218,
        area_ft2=369,
        manning_n=0.032999999821186066,
        br_in=198,
        tr_in=198,
        cr_in=82,
        b_in=109,
    ),
    EllipticalCatalogueSize(
        row_index_zero_based=14,
        span_in=315,
        rise_in=190,
        area_ft2=318.8599853515625,
        manning_n=0.032999999821186066,
        br_in=212,
        tr_in=212,
        cr_in=59,
        b_in=95,
    ),
    EllipticalCatalogueSize(
        row_index_zero_based=15,
        span_in=324,
        rise_in=194,
        area_ft2=334.57000732421875,
        manning_n=0.032999999821186066,
        br_in=219,
        tr_in=219,
        cr_in=59,
        b_in=97,
    ),
    EllipticalCatalogueSize(
        row_index_zero_based=16,
        span_in=326,
        rise_in=229,
        area_ft2=403.8900146484375,
        manning_n=0.032999999821186066,
        br_in=205,
        tr_in=205,
        cr_in=87,
        b_in=114.5,
    ),
    EllipticalCatalogueSize(
        row_index_zero_based=17,
        span_in=335,
        rise_in=233,
        area_ft2=421.9200134277344,
        manning_n=0.032999999821186066,
        br_in=212,
        tr_in=212,
        cr_in=87,
        b_in=116.5,
    ),
    EllipticalCatalogueSize(
        row_index_zero_based=18,
        span_in=337,
        rise_in=205,
        area_ft2=368.5199890136719,
        manning_n=0.032999999821186066,
        br_in=226,
        tr_in=226,
        cr_in=65,
        b_in=102.5,
    ),
    EllipticalCatalogueSize(
        row_index_zero_based=19,
        span_in=346,
        rise_in=209,
        area_ft2=385.4200134277344,
        manning_n=0.032999999821186066,
        br_in=233,
        tr_in=233,
        cr_in=65,
        b_in=104.5,
    ),
    EllipticalCatalogueSize(
        row_index_zero_based=20,
        span_in=353,
        rise_in=239,
        area_ft2=455.04998779296875,
        manning_n=0.032999999821186066,
        br_in=226,
        tr_in=226,
        cr_in=87,
        b_in=119.5,
    ),
    EllipticalCatalogueSize(
        row_index_zero_based=21,
        span_in=361,
        rise_in=242,
        area_ft2=471.05999755859375,
        manning_n=0.032999999821186066,
        br_in=233,
        tr_in=233,
        cr_in=87,
        b_in=121,
    ),
    EllipticalCatalogueSize(
        row_index_zero_based=22,
        span_in=363,
        rise_in=215,
        area_ft2=415.2099914550781,
        manning_n=0.032999999821186066,
        br_in=247,
        tr_in=247,
        cr_in=65,
        b_in=107.5,
    ),
    EllipticalCatalogueSize(
        row_index_zero_based=23,
        span_in=374,
        rise_in=254,
        area_ft2=512.9099731445312,
        manning_n=0.032999999821186066,
        br_in=240,
        tr_in=240,
        cr_in=93,
        b_in=127,
    ),
    EllipticalCatalogueSize(
        row_index_zero_based=24,
        span_in=376,
        rise_in=227,
        area_ft2=454.8699951171875,
        manning_n=0.032999999821186066,
        br_in=253,
        tr_in=253,
        cr_in=71,
        b_in=113.5,
    ),
    EllipticalCatalogueSize(
        row_index_zero_based=25,
        span_in=385,
        rise_in=230,
        area_ft2=471.2799987792969,
        manning_n=0.032999999821186066,
        br_in=260,
        tr_in=260,
        cr_in=71,
        b_in=115,
    ),
    EllipticalCatalogueSize(
        row_index_zero_based=26,
        span_in=387,
        rise_in=266,
        area_ft2=556.1799926757812,
        manning_n=0.032999999821186066,
        br_in=247,
        tr_in=247,
        cr_in=98,
        b_in=133,
    ),
    EllipticalCatalogueSize(
        row_index_zero_based=27,
        span_in=396,
        rise_in=269,
        area_ft2=574.5800170898438,
        manning_n=0.032999999821186066,
        br_in=253,
        tr_in=253,
        cr_in=98,
        b_in=134.5,
    ),
    EllipticalCatalogueSize(
        row_index_zero_based=28,
        span_in=398,
        rise_in=241,
        area_ft2=511.2300109863281,
        manning_n=0.032999999821186066,
        br_in=267,
        tr_in=267,
        cr_in=76,
        b_in=120.5,
    ),
    EllipticalCatalogueSize(
        row_index_zero_based=29,
        span_in=409,
        rise_in=280,
        area_ft2=618.3200073242188,
        manning_n=0.032999999821186066,
        br_in=260,
        tr_in=260,
        cr_in=104,
        b_in=140,
    ),
    EllipticalCatalogueSize(
        row_index_zero_based=30,
        span_in=415,
        rise_in=248,
        area_ft2=547.97998046875,
        manning_n=0.032999999821186066,
        br_in=281,
        tr_in=281,
        cr_in=76,
        b_in=124,
    ),
    EllipticalCatalogueSize(
        row_index_zero_based=31,
        span_in=419,
        rise_in=256,
        area_ft2=572.780029296875,
        manning_n=0.032999999821186066,
        br_in=281,
        tr_in=281,
        cr_in=82,
        b_in=128,
    ),
    EllipticalCatalogueSize(
        row_index_zero_based=32,
        span_in=421,
        rise_in=292,
        area_ft2=664.5399780273438,
        manning_n=0.032999999821186066,
        br_in=267,
        tr_in=267,
        cr_in=109,
        b_in=146,
    ),
    EllipticalCatalogueSize(
        row_index_zero_based=33,
        span_in=429,
        rise_in=309,
        area_ft2=718.530029296875,
        manning_n=0.032999999821186066,
        br_in=267,
        tr_in=267,
        cr_in=120,
        b_in=154.5,
    ),
    EllipticalCatalogueSize(
        row_index_zero_based=34,
        span_in=432,
        rise_in=268,
        area_ft2=619.1900024414062,
        manning_n=0.032999999821186066,
        br_in=288,
        tr_in=288,
        cr_in=87,
        b_in=134,
    ),
    EllipticalCatalogueSize(
        row_index_zero_based=35,
        span_in=443,
        rise_in=307,
        area_ft2=735.280029296875,
        manning_n=0.032999999821186066,
        br_in=281,
        tr_in=281,
        cr_in=115,
        b_in=153.5,
    ),
    EllipticalCatalogueSize(
        row_index_zero_based=36,
        span_in=446,
        rise_in=266,
        area_ft2=631.5800170898438,
        manning_n=0.032999999821186066,
        br_in=302,
        tr_in=302,
        cr_in=82,
        b_in=133,
    ),
    EllipticalCatalogueSize(
        row_index_zero_based=37,
        span_in=456,
        rise_in=319,
        area_ft2=786.7899780273438,
        manning_n=0.032999999821186066,
        br_in=288,
        tr_in=288,
        cr_in=120,
        b_in=159.5,
    ),
    EllipticalCatalogueSize(
        row_index_zero_based=38,
        span_in=464,
        rise_in=335,
        area_ft2=842.7100219726562,
        manning_n=0.032999999821186066,
        br_in=288,
        tr_in=288,
        cr_in=131,
        b_in=167.5,
    ),
    EllipticalCatalogueSize(
        row_index_zero_based=39,
        span_in=480,
        rise_in=355,
        area_ft2=925.52001953125,
        manning_n=0.032999999821186066,
        br_in=295,
        tr_in=295,
        cr_in=142,
        b_in=177.5,
    ),
)

ELLIPSE_CATALOGUE_BY_MATERIAL: dict[CulvertMaterial, tuple[EllipticalCatalogueSize, ...]] = {
    CulvertMaterial.CONCRETE: CONCRETE_ELLIPSE_CATALOGUE,
    CulvertMaterial.STEEL_OR_ALUMINUM: STEEL_OR_ALUMINUM_ELLIPSE_CATALOGUE,
}

_ELLIPSE_MATERIAL_LABEL: dict[CulvertMaterial, str] = {
    CulvertMaterial.CONCRETE: "Concrete",
    CulvertMaterial.STEEL_OR_ALUMINUM: "Steel or Aluminum",
}


def ellipse_catalogue_for_material(
    material: CulvertMaterial,
) -> tuple[EllipticalCatalogueSize, ...]:
    """Return the HY-8 ellipse catalogue for a supported material."""
    try:
        return ELLIPSE_CATALOGUE_BY_MATERIAL[material]
    except KeyError as exc:
        msg = f"HY-8 8.0.1.2 has no supported ellipse catalogue for {material.name}."
        raise ValueError(msg) from exc


def find_ellipse_catalogue_size(
    span_m: float,
    rise_m: float,
    *,
    material: CulvertMaterial,
    tolerance_m: float = ELLIPSE_CATALOGUE_MATCH_TOLERANCE_M,
) -> EllipticalCatalogueSize:
    """Return the exact supported HY-8 ellipse catalogue selection.

    Span and rise are orientation-sensitive. A reversed pair is not accepted
    unless that reversed pair is independently present in the selected
    material's HY-8 catalogue.
    """
    if not math.isfinite(span_m) or not math.isfinite(rise_m):
        msg = "Elliptical span and rise must be finite."
        raise ValueError(msg)
    if tolerance_m < 0.0 or not math.isfinite(tolerance_m):
        msg = "Ellipse catalogue matching tolerance must be finite and non-negative."
        raise ValueError(msg)

    catalogue = ellipse_catalogue_for_material(material)
    material_label = _ELLIPSE_MATERIAL_LABEL[material]
    matches = [
        entry
        for entry in catalogue
        if abs(entry.span_m - span_m) <= tolerance_m and abs(entry.rise_m - rise_m) <= tolerance_m
    ]
    if len(matches) == 1:
        return matches[0]
    if len(matches) > 1:  # pragma: no cover - protected by catalogue uniqueness
        msg = f"Ambiguous HY-8 {material_label} ellipse catalogue match for span={span_m:.9g} m, rise={rise_m:.9g} m."
        raise ValueError(msg)

    nearest = min(
        catalogue,
        key=lambda entry: math.hypot(entry.span_m - span_m, entry.rise_m - rise_m),
    )
    msg = (
        f"Unsupported HY-8 {material_label} elliptical size "
        f"span={span_m:.9g} m, rise={rise_m:.9g} m. "
        "HY-8 8.0.1.2 requires a catalogued ellipse size for the selected "
        "material; no nearest-size substitution is performed. "
        f"Closest catalogue entry is {nearest.span_in:g} in x {nearest.rise_in:g} in "
        f"(row {nearest.row_index_zero_based})."
    )
    raise ValueError(msg)


def find_concrete_ellipse_catalogue_size(
    span_m: float,
    rise_m: float,
    *,
    tolerance_m: float = ELLIPSE_CATALOGUE_MATCH_TOLERANCE_M,
) -> EllipticalCatalogueSize:
    """Compatibility wrapper for the concrete HY-8 ellipse catalogue."""
    return find_ellipse_catalogue_size(
        span_m,
        rise_m,
        material=CulvertMaterial.CONCRETE,
        tolerance_m=tolerance_m,
    )


def find_steel_or_aluminum_ellipse_catalogue_size(
    span_m: float,
    rise_m: float,
    *,
    tolerance_m: float = ELLIPSE_CATALOGUE_MATCH_TOLERANCE_M,
) -> EllipticalCatalogueSize:
    """Return an exact HY-8 steel-or-aluminum ellipse catalogue selection."""
    return find_ellipse_catalogue_size(
        span_m,
        rise_m,
        material=CulvertMaterial.STEEL_OR_ALUMINUM,
        tolerance_m=tolerance_m,
    )


__all__: list[str] = [
    "CONCRETE_ELLIPSE_CATALOGUE",
    "ELLIPSE_CATALOGUE_BY_MATERIAL",
    "ELLIPSE_CATALOGUE_MATCH_TOLERANCE_M",
    "ELLIPSE_CONCRETE_SOURCE_PATH",
    "ELLIPSE_STEEL_OR_ALUMINUM_SOURCE_PATH",
    "STEEL_OR_ALUMINUM_ELLIPSE_CATALOGUE",
    "EllipticalCatalogueSize",
    "ellipse_catalogue_for_material",
    "find_concrete_ellipse_catalogue_size",
    "find_ellipse_catalogue_size",
    "find_steel_or_aluminum_ellipse_catalogue_size",
]
