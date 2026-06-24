"""Target recon kneeboard pages for player flights.

Gated by the ``generate_target_recon_kneeboard`` setting (default OFF: the
marker overlays do not reliably line up with the underlying satellite tiles).
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
