from dataclasses import dataclass, field
from typing import Any, Optional, Union

from .optiondescription import (
    EnabledWhen,
    OptionDescription,
    SETTING_DESCRIPTION_KEY,
    normalize_enabled_when,
)


@dataclass(frozen=True)
class BoundedIntOption(OptionDescription):
    min: int
    max: int


def bounded_int_option(
    text: str,
    page: str,
    section: str,
    default: int,
    min: int,
    max: int,
    detail: Optional[str] = None,
    tooltip: Optional[str] = None,
    causes_expensive_game_update: bool = False,
    enabled_when: Optional[Union[str, EnabledWhen]] = None,
    **kwargs: Any,
) -> int:
    return field(
        metadata={
            SETTING_DESCRIPTION_KEY: BoundedIntOption(
                page,
                section,
                text,
                detail,
                tooltip,
                causes_expensive_game_update,
                min=min,
                max=max,
                enabled_when=normalize_enabled_when(enabled_when),
            )
        },
        default=default,
        **kwargs,
    )
