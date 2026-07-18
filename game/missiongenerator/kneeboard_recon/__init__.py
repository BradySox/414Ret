"""Target recon kneeboard pages for player flights.

Gated by the ``generate_target_recon_kneeboard`` setting (default OFF,
pending an in-game pass of the 2026-07-18 alignment fix). The historical
"marker overlays do not reliably line up with the tiles" had two measured
causes, both fixed:

* the dominant one — the DCS-vs-real-world terrain georeference offset
  (~350 m median on Caucasus/GermanyCW, ~740 m Normandy; tens of page
  pixels at detail scale) was only corrected on airbase-anchored pages;
  target/corridor/overview pages now apply the robust regional offset of
  the nearest measured airports (``airport_imagery.offset_near``), and
* the secondary one — the whole-page bilinear QUAD warp's interior
  curvature residual (up to ~5 page px on a 300 km overview) is removed by
  a subdivided MESH warp on large extents (``tile_compositor``).
"""

from .pages import (
    AirbaseReconPage,
    AirfieldDeparturePage,
    DetailReconPage,
    FrontLineDetailPage,
    OverviewReconPage,
    generate_recon_pages,
)

__all__ = [
    "AirbaseReconPage",
    "AirfieldDeparturePage",
    "DetailReconPage",
    "FrontLineDetailPage",
    "OverviewReconPage",
    "generate_recon_pages",
]
