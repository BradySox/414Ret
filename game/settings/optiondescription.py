from dataclasses import dataclass, field
from typing import Any, Optional, Tuple, Union

SETTING_DESCRIPTION_KEY = "DCS_LIBERATION_SETTING_DESCRIPTION_KEY"

#: A dependency: (master_field_name, value_that_enables_this_option). The settings
#: dialog greys this option out whenever ``settings.<master_field> != value``. The
#: value is usually a bool, but an enum member works too -- a knob that only means
#: something for one choice of a dropdown (ATMOS-X live weather under the cloud-preset
#: pack) is the same dependency as one gated on a checkbox.
EnabledWhen = Tuple[str, Any]


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
    # Deliberately not coerced: a bool stays a bool (the old shorthand), an enum
    # member stays itself, so the dialog can compare against either.
    return (str(master), expected)


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
    #: Marks an expert / tuning knob. The settings dialog hides advanced options
    #: behind a per-section "Show N advanced options" disclosure so a section reads
    #: as the handful of choices that actually shape a campaign, with the numbers
    #: that fine-tune them one click away. Search always reaches them regardless.
    #: Keyword-only for the same reason as ``enabled_when``.
    advanced: bool = field(default=False, kw_only=True)
