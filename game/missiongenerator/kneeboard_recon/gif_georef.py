# game/missiongenerator/kneeboard_recon/gif_georef.py
"""World coverage of the shipped theater rasters (``resources/<theater>.gif``).

The offline recon basemap crops these rasters and draws symbology over the
result, so a wrong world-to-pixel mapping puts the markers on the wrong ground
while the page still looks correct.

``Terrain.bounds`` is NOT that mapping and must never be used as one. Measured
2026-08-22: it leaves 24 of Syria's 224 airfields outside itself (the whole
Jordanian corner and the Negev — King Abdullah II, Muwaffaq Salti, Nevatim,
Hatzerim), 23 of Normandy's 89, 4 of Persian Gulf's 29 and 2 of Nevada's 17.
pydcs also declares Syria, Normandy and PersianGulf with ``top < bottom``,
inverting its own Rectangle contract, so a north-south scale taken from it
comes out negative.

The rects here come from the two per-theater reference airports the pre-2021
Qt map used to georeference these same images, re-derived against each GIF's
current pixel size. ``tests/test_gif_georef.py`` re-derives them from those
airports so the provenance stays checkable.

A rect is only valid for the image it was measured on, so the pixel size is
part of the record: a replaced GIF fails the lookup instead of silently
inheriting numbers measured against a different render.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional, Tuple

from dcs.terrain.terrain import Terrain

from .extent import MapExtent


@dataclass(frozen=True)
class WorldRect:
    """An axis-aligned DCS-world rectangle in metres (x = north, y = east)."""

    min_x: float
    max_x: float
    min_y: float
    max_y: float

    def contains(self, other: "WorldRect") -> bool:
        return (
            self.min_x <= other.min_x
            and other.max_x <= self.max_x
            and self.min_y <= other.min_y
            and other.max_y <= self.max_y
        )

    def intersects(self, other: "WorldRect") -> bool:
        return (
            self.min_x < other.max_x
            and other.min_x < self.max_x
            and self.min_y < other.max_y
            and other.min_y < self.max_y
        )


@dataclass(frozen=True)
class GifCoverage:
    """The world rectangle one shipped theater GIF actually shows."""

    image_size: Tuple[int, int]
    rect: WorldRect
    # Ground inside ``rect`` that the raster does not draw. Cropping over one
    # of these returns imagery that is confidently wrong rather than absent,
    # which is worse than no imagery at all — so it refuses instead.
    unrendered: Tuple[WorldRect, ...] = field(default_factory=tuple)

    def can_render(self, extent: MapExtent) -> bool:
        """True when this raster can place every metre of ``extent``."""
        want = WorldRect(extent.min_x, extent.max_x, extent.min_y, extent.max_y)
        if not self.rect.contains(want):
            return False
        return not any(hole.intersects(want) for hole in self.unrendered)

    def slide_to_cover(
        self, extent: MapExtent, must_contain: MapExtent
    ) -> Optional[MapExtent]:
        """``extent`` translated so this raster covers it, or None.

        Translation only — never a resize — so the page keeps its scale and
        aspect and the projection stays uniform. All that moves is where the
        area of interest sits on the page.

        The caller's extent has usually been grown by ``aspect_correct`` to
        match the page shape, and that padding is symmetric about the centre.
        When it pushes one edge off the raster there is normally slack on the
        opposite edge, and spending it costs nothing the reader can see.
        ``must_contain`` is the area the page actually has to show (the
        pre-padding extent); a slide that would push any of it off the page is
        refused rather than silently cropping the packages.

        Returns None when the raster is smaller than the extent on either axis,
        when the slide would lose ``must_contain``, or when the slid extent
        lands on ground the raster never drew.
        """
        if (
            extent.span_x_m > self.rect.max_x - self.rect.min_x
            or extent.span_y_m > self.rect.max_y - self.rect.min_y
        ):
            return None
        dx = max(0.0, self.rect.min_x - extent.min_x) - max(
            0.0, extent.max_x - self.rect.max_x
        )
        dy = max(0.0, self.rect.min_y - extent.min_y) - max(
            0.0, extent.max_y - self.rect.max_y
        )
        slid = MapExtent(
            min_x=extent.min_x + dx,
            max_x=extent.max_x + dx,
            min_y=extent.min_y + dy,
            max_y=extent.max_y + dy,
            terrain=extent.terrain,
        )
        keep = WorldRect(
            must_contain.min_x,
            must_contain.max_x,
            must_contain.min_y,
            must_contain.max_y,
        )
        if not WorldRect(slid.min_x, slid.max_x, slid.min_y, slid.max_y).contains(keep):
            return None
        return slid if self.can_render(slid) else None


# Cyprus is inside syria.gif's frame but the raster draws flat sea there:
# all 25 of the island's airfields — Akrotiri, Larnaca, Paphos, Ercan,
# Gecitkale, Kingsfield, Lakatamia, Pinarbashi and the HC/HMed helipads —
# project onto sea pixels, in an island-shaped arrangement that confirms the
# georeference is right and the imagery is missing. Bounds are the island's
# real extent (34.53-35.72 N, 32.20-34.65 E) in Syria world metres.
_SYRIA_CYPRUS = WorldRect(min_x=-50_339, max_x=94_409, min_y=-341_764, max_y=-110_757)

# Keyed by ``Terrain.name``. A theater absent here has no usable raster
# georeference and takes the landmap renderer instead.
#
# Sinai and MarianaIslands ship a GIF (sinai.gif, marianasislands.gif) but no
# reference points were ever authored for them, and their terrain names
# ("SinaiMap", "MarianaIslands") do not match those filenames, so the loader
# has never reached them. Left out rather than guessed.
COVERAGE: dict[str, GifCoverage] = {
    # m/px: 282.0 east, 336.7 north
    "Caucasus": GifCoverage(
        image_size=(2464, 1400),
        rect=WorldRect(min_x=-421_477, max_x=49_973, min_y=248_768, max_y=943_699),
    ),
    # m/px: 537.3 east, 578.9 north
    "Nevada": GifCoverage(
        image_size=(1192, 1008),
        rect=WorldRect(min_x=-574_257, max_x=9_270, min_y=-425_188, max_y=215_292),
    ),
    # m/px: 130.5 east, 135.5 north. The raster predates the Normandy 2.0
    # expansion, so London and Paris are off its frame; 28 of the map's 89
    # airfields are outside this rect and pages there fall back to the landmap.
    "Normandy": GifCoverage(
        image_size=(2158, 2500),
        rect=WorldRect(min_x=-153_308, max_x=185_357, min_y=-152_357, max_y=129_293),
    ),
    # m/px: 292.3 east, 294.7 north
    "PersianGulf": GifCoverage(
        image_size=(1870, 3552),
        rect=WorldRect(min_x=-368_288, max_x=678_331, min_y=-352_849, max_y=193_711),
    ),
    # m/px: 439.6 east, 451.7 north. The raster predates the Syria expansion
    # into Jordan and Israel, so the Negev and the Jordanian fields are off
    # its frame, and it never drew Cyprus at all.
    "Syria": GifCoverage(
        image_size=(2059, 1370),
        rect=WorldRect(min_x=-320_121, max_x=298_772, min_y=-340_596, max_y=564_498),
        unrendered=(_SYRIA_CYPRUS,),
    ),
}


def coverage_for(
    terrain: Terrain, image_size: Tuple[int, int]
) -> Optional[GifCoverage]:
    """The measured coverage of ``terrain``'s raster, or None.

    Returns None for a theater with no measured georeference, and for one
    whose shipped image is no longer the size the rect was measured against —
    a resized or replaced raster invalidates the numbers, and guessing a new
    mapping from them would reintroduce exactly the silent misplacement this
    module exists to stop.
    """
    coverage = COVERAGE.get(terrain.name)
    if coverage is None or coverage.image_size != image_size:
        return None
    return coverage
