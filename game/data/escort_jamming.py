"""Graduated escort-jamming tiers (§77).

Escort jamming is a *role*, not one airframe. An aircraft's effect scales to how
real its EW kit is, so a dedicated jammer and a fighter with a bolt-on
self-protect pod both "represent" the mission but at very different utility:

- ``FULL`` -- a dedicated jammer carrying the ALQ-99 (``OFFENSIVE_JAMMER``):
  the EA-18G Growler and the EA-6B Prowler. Strong missile-spoof bubble over the
  whole package **plus** offensive ROE weapons-hold pulses on radar SAMs.
- ``ECM`` -- a fighter with genuine *built-in* ECM (F/A-18C ALQ-165, F-14 DECM):
  a moderate defensive bubble, no offensive suppression.
- ``SELF_PROTECT`` -- a fighter that bolts on a self-protect ECM pod (F-16C
  ALQ-184, F-4E ALQ-131, AV-8B ALQ-164, A-7E): a weak defensive bubble.
- ``LOOSE`` -- the opt-in "stretch" tier (``escort_jamming_loose`` setting, off
  by default): any other podded jet pressed into a token jamming escort. Weakest
  of all -- flavor, not a game-changer -- and never auto-planned unless the DM
  turns the setting on, so the default roster stays the curated set above and the
  retired "every fighter jams" ewrj behaviour (§2) never returns silently.

The tier is authored per airframe in its unit YAML (``escort_jammer_tier``),
alongside the ``Escort Jammer`` task priority that makes it plannable. This is a
curated whitelist by construction; only the LOOSE tier widens the net, and only
when the setting is enabled.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Optional


class EscortJammerTier(Enum):
    FULL = "full"
    ECM = "ecm"
    SELF_PROTECT = "self_protect"
    LOOSE = "loose"

    @classmethod
    def from_yaml(cls, value: Optional[str]) -> Optional["EscortJammerTier"]:
        """Parse the YAML string, tolerating absence (untagged -> None)."""
        if value is None:
            return None
        return cls(value)

    @property
    def is_loose(self) -> bool:
        return self is EscortJammerTier.LOOSE

    @property
    def does_offensive(self) -> bool:
        """Only the dedicated (FULL) tier suppresses radar SAMs with ROE holds."""
        return self is EscortJammerTier.FULL


@dataclass(frozen=True)
class TierEffect:
    """The plugin-facing strength knobs a tier emits.

    ``defensive_power`` scales the missile-spoof bubble's per-band probability
    (1.0 = the baseline Matador bands); ``offensive`` gates the SAM weapons-hold
    pulse. These are the *design* numbers -- the plugin multiplies its bands by
    ``defensive_power`` and only runs the offensive loop when ``offensive`` is set.
    """

    defensive_power: float
    offensive: bool


# The utility gradient: dedicated jammer -> built-in ECM -> pod -> token stretch.
_TIER_EFFECTS: dict[EscortJammerTier, TierEffect] = {
    EscortJammerTier.FULL: TierEffect(defensive_power=1.0, offensive=True),
    EscortJammerTier.ECM: TierEffect(defensive_power=0.6, offensive=False),
    EscortJammerTier.SELF_PROTECT: TierEffect(defensive_power=0.35, offensive=False),
    EscortJammerTier.LOOSE: TierEffect(defensive_power=0.18, offensive=False),
}


def effect_for(tier: EscortJammerTier) -> TierEffect:
    return _TIER_EFFECTS[tier]
