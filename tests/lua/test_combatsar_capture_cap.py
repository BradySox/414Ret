"""Headless check of the combatsar capture-party SAFETY CAP.

The enemy snatch party is REAL infantry spawned onto DCS's single scripting/sim thread, so a
cranked ``capturePartySize`` / ``captureTeams`` (or a stale saved override) piles on dozens of
units per ejection and, over a few ejections, can bog a heavy mission into a hang (observed
2026-07-08: a saved 40-strong / 4-team value spawned 80 soldiers over two ejections on a full
Red Tide map -> sim lock-up, no crash dump). The plugin clamps the values at load; this runs
the REAL plugin script under Lua 5.1 with a cranked config and asserts the clamp fired with the
right numbers.

combatsar is otherwise MOOSE-heavy and not modelled by ``DcsPluginHarness``, but the cap runs
at file scope BEFORE any MOOSE/coalition wiring: with an empty ``CombatSAR`` data table the
config setup early-returns and the chunk returns before ``SET_GROUP``/``timer``/``world`` are
ever touched, so a tiny sandbox exercises the cap end to end.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import lupa.lua51 as lua51

PLUGIN = (
    Path(__file__).resolve().parents[2]
    / "resources/plugins/combatsar/combatsar-config.lua"
)


def _to_lua(rt: lua51.LuaRuntime, value: Any) -> Any:
    """Recursively convert Python dicts/lists/scalars into Lua tables."""
    if isinstance(value, dict):
        table = rt.table()
        for key, item in value.items():
            table[key] = _to_lua(rt, item)
        return table
    if isinstance(value, (list, tuple)):
        table = rt.table()
        for index, item in enumerate(value, start=1):
            table[index] = _to_lua(rt, item)
        return table
    return value


def _run_plugin(
    party_size: int | None, teams: int | None
) -> tuple[list[str], list[str]]:
    """Load the real plugin under a minimal DCS sandbox; return (warnings, infos)."""
    rt = lua51.LuaRuntime(unpack_returned_tuples=False)
    g = rt.globals()
    warnings: list[str] = []
    infos: list[str] = []

    g.env = rt.table()
    g.env["info"] = lambda msg: infos.append(str(msg))
    g.env["warning"] = lambda msg: warnings.append(str(msg))

    # The only globals the plugin touches before its early return (empty CombatSAR data).
    g.coalition = _to_lua(rt, {"side": {"BLUE": 2, "RED": 1}})
    g.country = _to_lua(rt, {"id": {"CJTF_RED": 82, "CJTF_BLUE": 80}})

    combatsar: dict[str, Any] = {}
    if party_size is not None:
        combatsar["capturePartySize"] = party_size
    if teams is not None:
        combatsar["captureTeams"] = teams
    g.dcsRetribution = _to_lua(
        rt,
        {
            # No pilotTemplate -> addConfig early-returns, #configs == 0, chunk returns
            # before any MOOSE wiring. The cap has already run by then.
            "CombatSAR": {},
            "plugins": {"combatsar": combatsar},
        },
    )

    rt.execute(PLUGIN.read_text(encoding="utf-8"))
    return warnings, infos


def test_cranked_capture_party_is_clamped() -> None:
    warnings, infos = _run_plugin(party_size=40, teams=4)
    clamp = [w for w in warnings if "clamp" in w.lower()]
    assert clamp, f"expected a clamp warning, got {warnings}"
    msg = clamp[0]
    # MAX_PARTY_SIZE = 12, MAX_TEAMS = 4; the message echoes the requested values.
    assert "12 infantry" in msg and "4 teams" in msg, msg
    assert "requested 40/4" in msg, msg
    # The chunk ran through to the no-rescue-helos early return (the cap sits before it).
    assert any("no rescue helos" in i for i in infos), infos


def test_default_capture_party_is_not_clamped() -> None:
    # Shipped defaults (5 / 3) sit inside the cap, so nothing is reined in.
    warnings, _ = _run_plugin(party_size=None, teams=None)
    assert not [w for w in warnings if "clamp" in w.lower()], warnings


def test_only_the_teams_over_cap_is_clamped() -> None:
    warnings, _ = _run_plugin(party_size=5, teams=9)
    clamp = [w for w in warnings if "clamp" in w.lower()]
    assert clamp, warnings
    # party 5 is within the cap; teams 9 -> 4.
    assert "5 infantry" in clamp[0] and "4 teams" in clamp[0], clamp[0]
    assert "requested 5/9" in clamp[0], clamp[0]
