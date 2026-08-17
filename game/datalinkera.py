"""Whether an airframe's datalink exists yet, for the DCS ``EPLRS`` task.

DCS reused the EPLRS name generically: the task on a group is what makes that
group take part in datalink at all -- Link 16 on a Hornet or Viper, SADL on an
A-10C, a ground unit's own net. Without it the terminal never comes up, which
reads in the cockpit as an empty SA page.

The switch used to be one boolean, and a fork shipping both a 1988 and a 2027
campaign cannot have that be right. On gave Desert Storm Hornets Link 16 a
decade early; off cost every modern campaign its datalink. Flown 2026-08-16:
**1 of 23** blue plane groups carried the task, against **16 of 18** in a
hand-built modern mission on the same install -- which is why datalink worked
there and not here.

pydcs's own ``eplrs`` flag cannot answer this. It means only "DCS lets you tick
the box" and is true for 87 airframes including the B-47 Stratojet, the Tu-16
and the OV-10A. So the era question needs its own per-airframe date, authored in
the unit files as ``datalink_introduced`` -- the same shape as the §24
``date_gated_properties`` era gate for payload options.

Rationale and the per-airframe sourcing live in
``docs/dev/design/414th-datalink-era-notes.md``.
"""

from __future__ import annotations

from typing import Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from game.settings import DatalinkPolicy


def datalink_available(
    policy: "DatalinkPolicy",
    introduced: Optional[int],
    campaign_year: int,
) -> bool:
    """Whether this airframe should get the EPLRS task in this campaign.

    ``introduced`` is the airframe's ``datalink_introduced`` year, or ``None``
    when the unit file does not declare one. Unknown reads as permissive: an
    un-authored airframe behaves exactly as it did before this gate existed, so
    adding dates is incremental and never silently removes a capability from an
    airframe nobody has researched.
    """
    from game.settings import DatalinkPolicy as Policy

    if policy is Policy.NEVER:
        return False
    if policy is Policy.ALWAYS:
        return True
    # ERA_CORRECT
    if introduced is None:
        return True
    return campaign_year >= introduced
