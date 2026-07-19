"""Per-flight planner controls for the native DTC cartridge (§74).

Lives in ``game.ato`` because it pickles with the :class:`Flight` (the Edit
Flight dialog writes it, the campaign save carries it, and the next
generation's ``DtcGenerator`` honors it). Deliberately a plain dataclass of
builtins so old saves unpickle trivially (``Flight.__setstate__`` defaults a
missing field to ``DtcOptions()``, which reproduces pre-feature behavior).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass
class DtcOptions:
    """What (if anything) this flight's cartridge should carry.

    ``enabled`` is a tri-state: ``None`` follows the campaign-wide
    ``dtc_data_cartridges`` setting, ``True``/``False`` override it for this
    flight alone. The section flags select cartridge contents; a section that
    is off is omitted entirely, leaving the jet's own defaults untouched.
    """

    enabled: Optional[bool] = None
    #: COMM1/COMM2 named presets mirroring the radio allocator's channels.
    comms: bool = True
    #: The flight's steerpoints + route sequence (ETAs, leg speeds).
    route: bool = True
    #: Recovery aids: TACAN/ICLS/ACLS pre-tune + FPAS home waypoint (Hornet).
    nav_aids: bool = True
    #: FLOT line(s) + ROE no-strike zones (SA FAOR / HSD GEO lines).
    flot_and_zones: bool = True
    #: Friendly CAP stations + tanker/AEW&C orbits (SA racetracks; Viper
    #: anchor steerpoints).
    friendly_orbits: bool = True
    #: Known enemy SAM threat rings (recon-fogged).
    threat_rings: bool = True

    def resolve_enabled(self, campaign_default: bool) -> bool:
        """The effective on/off for this flight."""
        if self.enabled is None:
            return campaign_default
        return self.enabled

    @property
    def any_content(self) -> bool:
        """Whether any section would make it into the cartridge."""
        return any(
            (
                self.comms,
                self.route,
                self.nav_aids,
                self.flot_and_zones,
                self.friendly_orbits,
                self.threat_rings,
            )
        )
