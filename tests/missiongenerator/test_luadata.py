"""An item carrying both scalars and a nested table must emit both.

Flown 2026-08-16: the deckdecor boat record kept its `recoverySpawns` table and
lost `group`/`unit`/`side`/`brc`/`clearNames`, so the plugin armed, looked up
`Group.getByName("")`, took its "boat gone" exit and never cleared the deck --
silently, because that exit does not log. The reactive-red group pool was
dropped the same way. The serializer, not the emitters, was at fault.
"""

from game.missiongenerator.luagenerator import LuaData


def test_scalars_survive_alongside_a_nested_table() -> None:
    root = LuaData("dcsRetribution")
    rec = root.add_item("boat")
    rec.add_key_value("group", "0077 | PORPOISE (Carrier)")
    rec.add_key_value("brc", "166.0")
    rec.add_data_array("clearNames", ["decor 01", "decor 02"])
    spawns = rec.add_item("recoverySpawns")
    spawn = spawns.add_item()
    spawn.add_key_value("type", "FA-18C_hornet")

    out = root.serialize()

    assert 'group = "0077 | PORPOISE (Carrier)"' in out
    assert 'brc = "166.0"' in out
    assert 'clearNames = {"decor 01", "decor 02"}' in out
    assert "recoverySpawns" in out
    assert 'type = "FA-18C_hornet"' in out


def test_scalar_only_and_nested_only_items_are_unchanged() -> None:
    # The two unmixed shapes are the common case; the fix must not disturb them.
    scalar_only = LuaData("plain")
    scalar_only.add_key_value("a", "1")
    assert scalar_only.serialize() == 'plain = {a = "1"}'

    nested_only = LuaData("outer")
    inner = nested_only.add_item("inner")
    inner.add_key_value("b", "2")
    out = nested_only.serialize()
    assert 'b = "2"' in out and "inner" in out


def test_reactive_red_pool_reaches_the_plugin() -> None:
    # The emitter shape from reactiveredluadata.py: the group pool is a scalar
    # array on the same item as the objectives table.
    root = LuaData("dcsRetribution")
    node = root.add_item("reactiveRed")
    node.add_data_array("groups", ["Reaction Alert 1", "Reaction Alert 2"])
    objectives = node.add_item("objectives")
    objective = objectives.add_item()
    objective.add_key_value("name", "QUAGGA")

    out = root.serialize()

    assert 'groups = {"Reaction Alert 1", "Reaction Alert 2"}' in out
    assert 'name = "QUAGGA"' in out
