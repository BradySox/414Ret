"""Fuel-driven pre/post-vul tanker tasking.

Every flight launches normally. A flight whose planned fuel burn exceeds what it can
carry needs to take gas from a tanker, and *when* it should do so depends on where in
the sortie it runs short:

* **Pre-vul** -- it cannot complete the run in to the target and the vulnerability
  window (takeoff -> split) on internal fuel while keeping its landing reserve, so it
  tops off on the ingress leg before the vul.
* **Post-vul** -- it can fight through the vul on internal fuel but cannot make it home
  with reserve afterward, so it tanks on the egress leg.

This module holds only the (pure, unit-agnostic) decision; the flight plan supplies the
fuel numbers and inserts the matching refuel waypoint. All fuel quantities passed in
must share the same unit (pounds, matching ``FuelConsumption``).
"""

from __future__ import annotations

from enum import Enum, unique


@unique
class RefuelTasking(Enum):
    """Where, if anywhere, a flight should be sent to a tanker."""

    #: Internal fuel is sufficient for the whole sortie; no tanker needed.
    NONE = "none"
    #: Top off on the ingress leg, before the vulnerability window.
    PRE_VUL = "pre_vul"
    #: Tank on the egress leg, after the vulnerability window.
    POST_VUL = "post_vul"

    @property
    def needs_tanker(self) -> bool:
        return self is not RefuelTasking.NONE

    @property
    def refuels_pre_vul(self) -> bool:
        return self is RefuelTasking.PRE_VUL

    @property
    def refuels_post_vul(self) -> bool:
        return self is RefuelTasking.POST_VUL


def decide_refuel_tasking(
    usable_fuel: float,
    fuel_to_end_of_vul: float,
    fuel_vul_to_home: float,
    reserve: float,
) -> RefuelTasking:
    """Decide whether and where a flight should tank.

    Args:
        usable_fuel: Internal fuel available at the start of the sortie (after taxi),
            in pounds.
        fuel_to_end_of_vul: Fuel burned from takeoff through the end of the
            vulnerability window (split), in pounds.
        fuel_vul_to_home: Fuel burned from the split back to landing, in pounds.
        reserve: Landing fuel reserve to preserve, in pounds.

    Returns:
        ``NONE`` if internal fuel covers the whole sortie plus reserve, ``PRE_VUL`` if
        the flight cannot reach the end of the vul with reserve to spare, otherwise
        ``POST_VUL``.
    """
    total_required = fuel_to_end_of_vul + fuel_vul_to_home + reserve
    if usable_fuel >= total_required:
        return RefuelTasking.NONE
    # The flight is short. If it can't even fight through the vul while holding its
    # reserve it has to top off on the way in; otherwise it can wait until egress.
    if usable_fuel < fuel_to_end_of_vul + reserve:
        return RefuelTasking.PRE_VUL
    return RefuelTasking.POST_VUL
