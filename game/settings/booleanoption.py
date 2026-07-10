from dataclasses import dataclass, field
from typing import Any, Optional, Union

from .optiondescription import (
    EnabledWhen,
    OptionDescription,
    SETTING_DESCRIPTION_KEY,
    normalize_enabled_when,
)


@dataclass(frozen=True)
class BooleanOption(OptionDescription):
    invert: bool


def boolean_option(
    text: str,
    page: str,
    section: str,
    default: bool,
    invert: bool = False,
    detail: Optional[str] = None,
    tooltip: Optional[str] = None,
    causes_expensive_game_update: bool = False,
    enabled_when: Optional[Union[str, EnabledWhen]] = None,
    **kwargs: Any,
) -> bool:
    return field(
        metadata={
            SETTING_DESCRIPTION_KEY: BooleanOption(
                page,
                section,
                text,
                detail,
                tooltip,
                causes_expensive_game_update,
                invert,
                enabled_when=normalize_enabled_when(enabled_when),
            )
        },
        default=default,
        **kwargs,
    )
