from dataclasses import dataclass, field
from typing import Optional, Tuple, Union

SETTING_DESCRIPTION_KEY = "DCS_LIBERATION_SETTING_DESCRIPTION_KEY"

#: A dependency: (master_field_name, value_that_enables_this_option). The settings
#: dialog greys this option out whenever ``settings.<master_field> != value``.
EnabledWhen = Tuple[str, bool]


def normalize_enabled_when(
    value: Optional[Union[str, EnabledWhen]],
) -> Optional[EnabledWhen]:
    """Accept ``"master"`` (shorthand for enabled when that field is truthy) or an
    explicit ``("master", enabled_value)`` tuple; return the normalized tuple or None.
    """
    if value is None:
        return None
    if isinstance(value, str):
        return (value, True)
    master, expected = value
    return (str(master), bool(expected))


@dataclass(frozen=True)
class OptionDescription:
    page: str
    section: str
    text: str
    detail: Optional[str]
    tooltip: Optional[str]
    causes_expensive_game_update: bool
    #: Optional dependency on another setting: the dialog greys this option's control
    #: and label out whenever the master field's value doesn't match. Keyword-only so
    #: the subclasses' positional fields (invert, min/max, choices, ...) are unaffected
    #: by adding it to the base -- existing positional constructor calls keep working.
    enabled_when: Optional[EnabledWhen] = field(default=None, kw_only=True)
