from typing import Any, cast

from game.theater.frontline import FrontLine


def test_front_line_hash_survives_unpickle_ordering() -> None:
    """FrontLine.__hash__ must NOT depend on blue_cp/red_cp.

    Pickle hashes set/dict keys during load BEFORE __setstate__ restores an
    object's attributes. A state-dependent hash (hash((self.blue_cp,
    self.red_cp))) raises AttributeError on the half-constructed object and
    breaks save loading -- this regressed once in #53 and was the original
    reason upstream made the hash identity-based ("Fix save loading",
    605d8f057). The hash must also stay stable once state is attached, or a key
    inserted while half-constructed lands in the wrong bucket and is lost.
    """
    half_constructed = object.__new__(FrontLine)

    # Pickle inserts the key into the container while it is still empty.
    members = {half_constructed}
    # Hashing the empty object must not raise (blue_cp / red_cp are unset).
    assert hash(half_constructed)

    # __setstate__ then attaches the real attributes...
    half_constructed.blue_cp = cast(Any, object())
    half_constructed.red_cp = cast(Any, object())

    # ...and the key must still be findable, i.e. the hash did not change.
    assert half_constructed in members
