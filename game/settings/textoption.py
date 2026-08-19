from dataclasses import dataclass, field
from typing import Any, Optional, Union

from .optiondescription import (
    EnabledWhen,
    OptionDescription,
    SETTING_DESCRIPTION_KEY,
    normalize_enabled_when,
)


@dataclass(frozen=True)
class TextOption(OptionDescription):
    """A free-text setting, rendered as a single-line edit box.

    For values that cannot be offered as a list: a filesystem path, or an identifier
    (an ICAO code, say) drawn from a set too large or too external to enumerate.
    ``placeholder`` is shown greyed out while the box is empty, which is how a
    "leave blank and it will be worked out" default announces itself.
    """

    placeholder: Optional[str] = None


def text_option(
    text: str,
    page: str,
    section: str,
    default: str = "",
    placeholder: Optional[str] = None,
    detail: Optional[str] = None,
    tooltip: Optional[str] = None,
    causes_expensive_game_update: bool = False,
    enabled_when: Optional[Union[str, EnabledWhen]] = None,
    advanced: bool = False,
    **kwargs: Any,
) -> str:
    return field(
        metadata={
            SETTING_DESCRIPTION_KEY: TextOption(
                page,
                section,
                text,
                detail,
                tooltip,
                causes_expensive_game_update,
                placeholder,
                enabled_when=normalize_enabled_when(enabled_when),
                advanced=advanced,
            )
        },
        default=default,
        **kwargs,
    )
