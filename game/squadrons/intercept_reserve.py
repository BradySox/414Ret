from __future__ import annotations

import random
from typing import Optional

#: Probability that a single QRA scramble launches one interceptor rather than a
#: pair. A distributed-QRA posture (the 414th's choice) prefers many bases each
#: putting up a small alert response over one base scrambling a large formation,
#: so most scrambles are a single ship and a minority are 2-ships.
QRA_SINGLE_SHIP_PROBABILITY = 0.75


def clamp_intercept_reserve(value: int, max_size: int) -> int:
    """Constrain a QRA reserve to ``0 <= reserve <= max_size``.

    Applied when a reserve enters a ``Squadron`` from an external source (a
    squadron definition / campaign YAML) where the value is not bounded by the
    UI spinner.
    """
    return max(0, min(value, max_size))


def qra_resource_count(
    intercept_reserve: int,
    owned_aircraft: int,
    available_pilots: Optional[int] = None,
) -> int:
    """Airframes actually fielded on QRA: the reserve capped by what can fly it.

    ``intercept_reserve`` is a fixed setting, but a squadron cannot field more QRA
    jets than it has airframes (``owned_aircraft``, which falls with attrition) or
    untasked pilots to fly them. ``available_pilots`` is the untasked pilot count;
    pass ``None`` when pilot limits are disabled (pilots are then unconstrained).
    """
    count = max(0, min(intercept_reserve, owned_aircraft))
    if available_pilots is not None:
        count = min(count, max(0, available_pilots))
    return count


def max_intercept_reserve(
    untasked_aircraft: int, intercept_reserve: int, max_size: int
) -> int:
    """Highest QRA reserve settable given aircraft already tasked this turn.

    Aircraft tasked to flights cannot be pulled onto QRA, so the reserve can only
    rise to the unplanned airframes plus what is already reserved:
    ``untasked_aircraft + intercept_reserve`` equals ``owned - tasked`` by the turn
    invariant (``tasked + untasked + reserve == owned``). This sum is stable under
    ``untasked_after_reserve_change`` (which trades untasked for reserve), so it is
    a fixed ceiling while the reserve spinner is edited. Also bounded by
    ``max_size``.
    """
    return min(max_size, untasked_aircraft + intercept_reserve)


def untasked_after_reserve_change(
    old_reserve: int, new_reserve: int, untasked_aircraft: int, owned_aircraft: int
) -> int:
    """Plannable-aircraft count after a mid-turn QRA reserve edit.

    ``untasked_aircraft`` is only recomputed from ``owned - reserve`` at
    ``return_all_pilots_and_aircraft`` (turn init). Editing the reserve spinner
    between turns must reflect in the plannable pool immediately, but a full
    reset would return airframes already tasked to flights this turn. Adjust by
    the reserve delta instead: freeing reserve (``old > new``) releases jets into
    the pool; raising it benches only jets that are still untasked.

    Bounded on both ends: floored at 0 (already-tasked flights are never
    retroactively un-planned) and capped at ``owned_aircraft - new_reserve`` (the
    airframes that actually exist beyond the new reserve). The cap matters after
    attrition leaves ``owned < reserve``: ``return_all_pilots_and_aircraft`` floors
    that to untasked 0, discarding the negative, so the delta alone would inflate
    the pool above the jets on hand.
    """
    adjusted = untasked_aircraft + (old_reserve - new_reserve)
    return max(0, min(adjusted, owned_aircraft - new_reserve))


def qra_player_manned_count(
    player_manned: int, intercept_reserve: int, owned_aircraft: int
) -> int:
    """Airframes of the QRA reserve a human pilot mans (the alert flight size).

    ``player_manned`` is the per-squadron setting for how many of the reserve are
    flown by the player on hot-alert instead of the AI dispatcher. It can never
    exceed the reserve itself, nor the airframes the squadron actually owns. Kept
    independent of the live untasked-pilot pool so the count is stable between
    planning (where the alert flight is fragged) and mission generation (where the
    AI dispatcher count is debited) -- both call this with the same inputs.
    """
    return max(0, min(player_manned, intercept_reserve, owned_aircraft))


def qra_player_client_slots(player_manned: int, ai_wingman: bool) -> int:
    """How many of the alert flight's airframes are human (client) slots.

    The alert flight is always ``player_manned`` airframes (that's what's carved
    from the reserve and debited from the AI dispatcher -- unaffected by this).
    This only decides *crewing*: with ``ai_wingman`` off every slot is a client
    (multi-human co-op alert); with it on only the lead is a client and the rest
    fly as AI wingmen (a human-lead section in single-player). A single-ship alert
    (``player_manned`` 1) has no wingman either way.
    """
    if ai_wingman and player_manned >= 1:
        return 1
    return max(0, player_manned)


def ai_qra_resource_count(
    intercept_reserve: int,
    owned_aircraft: int,
    available_pilots: Optional[int],
    player_manned: int,
) -> int:
    """QRA airframes the AI dispatcher fields after the player mans their share.

    The player-manned airframes (``qra_player_manned_count``) are carved out of the
    reserve *and* the owned pool before the usual ``qra_resource_count`` clamp, so
    the AI never spawns a jet the player is already sitting in (no double-spawn) and
    a partially-attrited squadron splits its survivors correctly between the two.
    The available-pilot cap is left as-is: the alert flight claims its pilots during
    planning, so by mission-generation time ``available_pilots`` already excludes
    them -- subtracting again here would double-count.
    """
    manned = qra_player_manned_count(player_manned, intercept_reserve, owned_aircraft)
    return qra_resource_count(
        intercept_reserve - manned, owned_aircraft - manned, available_pilots
    )


def qra_scramble_grouping(rng: Optional[random.Random] = None) -> int:
    """How many interceptors a base launches per QRA scramble: 1 or 2.

    Returns 1 with probability ``QRA_SINGLE_SHIP_PROBABILITY`` (default 0.75),
    otherwise 2. MOOSE's ``AI_A2A_DISPATCHER`` grouping is set per squadron, so
    this is rolled once per fielded QRA squadron (per turn) rather than per
    individual scramble; across the theater's alert bases the per-launch mix
    approaches the configured single/pair split.

    ``rng`` is injectable for deterministic tests; defaults to the module random.
    """
    roll = (rng or random).random()
    return 1 if roll < QRA_SINGLE_SHIP_PROBABILITY else 2


def seeded_intercept_reserve(
    capable_of_barcap: bool,
    current_reserve: int,
    default_reserve: int,
    max_size: int,
) -> int:
    """Return the QRA reserve a squadron should start a new campaign with.

    The per-side ``ownfor_default_qra_reserve`` / ``opfor_default_qra_reserve`` settings seed BARCAP-capable squadrons
    that do not already carry an explicit reserve. A squadron that cannot fly
    BARCAP, or one already carrying an explicit non-zero reserve (e.g. from a
    squadron definition), is left unchanged. The result never exceeds
    ``max_size``.
    """
    if not capable_of_barcap:
        return current_reserve
    if current_reserve != 0:
        return current_reserve
    return min(default_reserve, max_size)


def repropagated_intercept_reserve(
    capable_of_barcap: bool,
    current_reserve: int,
    old_default: int,
    new_default: int,
    max_size: int,
) -> int:
    """QRA reserve after a coalition default changes old -> new on a live campaign.

    Symmetric with ``seeded_intercept_reserve`` but for a default edited
    mid-campaign rather than at new-game seeding. A BARCAP-capable squadron whose
    reserve still equals the *clamped* old default is moved to the clamped new
    default; squadrons that cannot fly BARCAP, or that the user has set to any
    other value, are left unchanged. The result never exceeds ``max_size``.
    """
    if not capable_of_barcap:
        return current_reserve
    if current_reserve != clamp_intercept_reserve(old_default, max_size):
        return current_reserve
    return clamp_intercept_reserve(new_default, max_size)
