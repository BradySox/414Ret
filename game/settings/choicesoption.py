from dataclasses import dataclass, field
from typing import Any, Generic, Iterable, Mapping, Optional, TypeVar, Union

from .optiondescription import (
    EnabledWhen,
    OptionDescription,
    SETTING_DESCRIPTION_KEY,
    normalize_enabled_when,
)

ValueT = TypeVar("ValueT")


@dataclass(frozen=True)
class ChoicesOption(OptionDescription, Generic[ValueT]):
    choices: dict[str, ValueT]

    def text_for_value(self, value: ValueT) -> str:
        for text, _value in self.choices.items():
            if value == _value:
                return text
        raise ValueError(f"{self} does not contain {value}")


def choices_option(
    text: str,
    page: str,
    section: str,
    default: ValueT,
    choices: Union[Iterable[str], Mapping[str, ValueT]],
    detail: Optional[str] = None,
    tooltip: Optional[str] = None,
    enabled_when: Optional[Union[str, EnabledWhen]] = None,
    **kwargs: Any,
) -> ValueT:
    if not isinstance(choices, Mapping):
        choices = {c: c for c in choices}
    return field(
        metadata={
            SETTING_DESCRIPTION_KEY: ChoicesOption(
                page,
                section,
                text,
                detail,
                tooltip,
                causes_expensive_game_update=False,
                choices=dict(choices),
                enabled_when=normalize_enabled_when(enabled_when),
            )
        },
        default=default,
        **kwargs,
    )
